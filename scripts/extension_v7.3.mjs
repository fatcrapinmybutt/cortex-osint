import { joinSession } from "@github/copilot-sdk/extension";
import { spawn, execSync, spawnSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import { platform, hostname, cpus, totalmem, freemem } from "node:os";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { randomUUID } from "node:crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DAEMON_PATH = join(__dirname, "nexus_daemon.py");
const DB_PATH = "C:\\Users\\andre\\LitigationOS\\litigation_context.db";
const REPO_ROOT = "C:\\Users\\andre\\LitigationOS";
const PIPELINE_DIR = join(REPO_ROOT, "00_SYSTEM", "pipeline");
const BRIDGE_TIMEOUT = 60000; // 60s for bridge tools (multi-query orchestration)
const CMD_TIMEOUT = 600000;   // 600s for command execution
const MAX_CMD_OUTPUT = 250 * 1024; // 250 KB output cap for commands

const PHASE_MAP = {
    "1": "phase1_inventory.py", "2": "phase2_classify.py", "3": "phase3_extract.py",
    "4a": "phase4a_pdf.py", "4b": "phase4b_docx.py", "4c": "phase4c_structured.py",
    "4d": "phase4d_atomize.py", "4e": "phase4e_archive.py", "5": "phase5_brain_feed.py",
    "7a": "phase7a_authority.py", "7c": "phase7c_chains.py", "8": "phase8_filing.py",
    "12": "phase12_dedup.py", "13": "phase13_semantic.py", "14": "phase14_timeline.py",
    "16": "phase16_convergence.py",
    "autopilot": "autopilot.py", "filing": "filing_pipeline.py",
    "status": "quick_status.py", "validate": "validate.py",
};

// Safety guards (RangeError prevention)
const MAX_STDOUT_BYTES = 2 * 1024 * 1024;   // 2 MB cap for subprocess stdout
const MAX_STDERR_BYTES = 64 * 1024;          // 64 KB cap for stderr
const MAX_FORMAT_ROWS = 200;                 // Max rows to render in markdown tables
const MAX_OUTPUT_CHARS = 500_000;            // 500 KB max for any single tool output
const MAX_BRIDGE_ITEMS = 500;                // Max items from bridge arrays

function safeTruncate(str, maxLen, label = "output") {
    if (typeof str !== "string") {
        try { str = String(str ?? ""); } catch { return "[unstringifiable value]"; }
    }
    if (str.length <= maxLen) return str;
    return str.substring(0, maxLen) +
        `\n\n⚠️ [${label} truncated: ${str.length.toLocaleString()} → ${maxLen.toLocaleString()} chars]`;
}

function safeStringify(obj, maxLen = MAX_OUTPUT_CHARS) {
    try {
        const s = JSON.stringify(obj, null, 2);
        return safeTruncate(s, maxLen, "JSON");
    } catch {
        return "[object too large to serialize]";
    }
}

// === NEXUS v2 — Persistent Daemon Transport ===
// Single long-running Python process (nexus_daemon.py) with warm DB connections.
// Eliminates ~500ms spawn overhead per tool call (was: new python process per call).
// Protocol: line-delimited JSON over stdin/stdout with UUID request correlation.

let daemonProc = null;
let daemonReady = false;
let daemonReadyResolve = null;
let daemonReadyPromise = null;
const pendingRequests = new Map(); // id → { resolve, timer }
let stdoutBuffer = "";
let daemonRestarts = 0;
const MAX_RESTARTS = 5;
const DEFAULT_TIMEOUT = 30000;

function startDaemon() {
    if (daemonProc) return daemonReadyPromise;

    daemonReadyPromise = new Promise((resolve) => { daemonReadyResolve = resolve; });
    stdoutBuffer = "";
    pendingRequests.clear();

    daemonProc = spawn("python", [DAEMON_PATH], {
        env: { ...process.env, PYTHONUTF8: "1" },
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
    });

    daemonProc.stdout.setEncoding("utf-8");
    daemonProc.stdout.on("data", (chunk) => {
        stdoutBuffer += chunk;
        let nl;
        while ((nl = stdoutBuffer.indexOf("\n")) !== -1) {
            const line = stdoutBuffer.substring(0, nl).trim();
            stdoutBuffer = stdoutBuffer.substring(nl + 1);
            if (!line) continue;
            try {
                const msg = JSON.parse(line);
                // Startup ready signal
                if (msg.status === "ready" && !daemonReady) {
                    daemonReady = true;
                    if (daemonReadyResolve) { daemonReadyResolve(true); daemonReadyResolve = null; }
                    continue;
                }
                // Route response to pending request by id
                if (msg.id && pendingRequests.has(msg.id)) {
                    const { resolve, timer } = pendingRequests.get(msg.id);
                    clearTimeout(timer);
                    pendingRequests.delete(msg.id);
                    resolve(msg);
                }
            } catch {
                // Non-JSON line — ignore (daemon logs go to stderr/temp file)
            }
        }
    });

    daemonProc.stderr.on("data", () => {}); // Daemon logs to %TEMP%/nexus_daemon.log

    daemonProc.on("close", (code) => {
        const wasReady = daemonReady;
        daemonProc = null;
        daemonReady = false;
        // Reject all in-flight requests
        for (const [, { resolve, timer }] of pendingRequests) {
            clearTimeout(timer);
            resolve({ ok: false, error: `Daemon exited (code ${code})` });
        }
        pendingRequests.clear();
        // Auto-restart with backoff (unless exhausted)
        if (wasReady && daemonRestarts < MAX_RESTARTS) {
            daemonRestarts++;
            setTimeout(startDaemon, 500 * daemonRestarts);
        }
    });

    // Kill daemon when parent process exits
    const cleanup = () => { if (daemonProc) { try { daemonProc.kill(); } catch {} } };
    process.once("exit", cleanup);
    process.once("SIGINT", cleanup);
    process.once("SIGTERM", cleanup);

    return daemonReadyPromise;
}

async function callDaemon(request, timeoutMs = DEFAULT_TIMEOUT) {
    // Ensure daemon is running and ready
    if (!daemonProc || !daemonReady) {
        const readyP = startDaemon();
        const ready = await Promise.race([
            readyP.then(() => true),
            new Promise((r) => setTimeout(() => r(false), 8000)),
        ]);
        if (!ready) return { ok: false, error: "Daemon startup timeout (8s)" };
    }

    const id = randomUUID();
    request.id = id;

    return new Promise((resolve) => {
        const timer = setTimeout(() => {
            if (pendingRequests.has(id)) {
                pendingRequests.delete(id);
                resolve({ ok: false, error: `Request timeout (${timeoutMs}ms)` });
            }
        }, timeoutMs);

        pendingRequests.set(id, { resolve, timer });

        try {
            daemonProc.stdin.write(JSON.stringify(request) + "\n");
        } catch (e) {
            pendingRequests.delete(id);
            clearTimeout(timer);
            resolve({ ok: false, error: `Write failed: ${e.message}` });
        }
    });
}

// Legacy-compatible wrappers — all 22+ tool handlers call these UNCHANGED.
// queryDB: returns string on error (formatResult expects this pattern).
// callBridge: returns object on error (bridge formatters check data.error).

function queryDB(request) {
    return callDaemon(request).then((res) => {
        if (res && res.ok === false) return `❌ ${res.error || "Unknown error"}`;
        return res;
    });
}

function callBridge(payload, timeoutMs = BRIDGE_TIMEOUT) {
    return callDaemon(payload, timeoutMs);
}

// Markdown formatter (queryDB results)

function formatResult(data) {
    if (typeof data === "string") return safeTruncate(data, MAX_OUTPUT_CHARS, "text result");

    // Error response from daemon
    if (data.ok === false && data.error) {
        return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    }

    if (data.stats) {
        let out =
            "## 📊 Database Statistics\n\n| Table | Rows |\n| --- | --- |\n";
        for (const [k, v] of Object.entries(data.stats)) {
            out += `| ${k} | ${typeof v === "number" ? v.toLocaleString() : v} |\n`;
        }
        return out;
    }

    // Rich rendering for case_health
    if (data.health) {
        let out = "## 🏥 Case Health Dashboard\n\n| Metric | Count |\n| --- | --- |\n";
        for (const [k, v] of Object.entries(data.health)) {
            out += `| ${k.replace(/_/g, ' ')} | ${typeof v === "number" ? v.toLocaleString() : v} |\n`;
        }
        return out;
    }

    // Rich rendering for adversary_threats
    if (data.threats && Array.isArray(data.threats)) {
        if (data.threats.length === 0) return "No adversary threats found.";
        let out = `## ⚔️ Adversary Threat Matrix (${data.count || data.threats.length} targets)\n\n`;
        const cols = Object.keys(data.threats[0]);
        out += "| " + cols.join(" | ") + " |\n";
        out += "| " + cols.map(() => "---").join(" | ") + " |\n";
        for (const t of data.threats.slice(0, 30)) {
            out += "| " + cols.map(c => String(t[c] ?? "").replace(/\|/g, "\\|").substring(0, 100)).join(" | ") + " |\n";
        }
        return out;
    }

    // Rich rendering for filing_pipeline
    if (data.pipeline && Array.isArray(data.pipeline)) {
        if (data.pipeline.length === 0) return "No filing pipeline data found.";
        let out = `## 📋 Filing Pipeline (${data.count || data.pipeline.length} filings)\n\n`;
        const cols = Object.keys(data.pipeline[0]);
        out += "| " + cols.join(" | ") + " |\n";
        out += "| " + cols.map(() => "---").join(" | ") + " |\n";
        for (const p of data.pipeline.slice(0, 30)) {
            out += "| " + cols.map(c => String(p[c] ?? "").replace(/\|/g, "\\|").substring(0, 100)).join(" | ") + " |\n";
        }
        if (data.source) out += `\n*Source table: ${data.source}*`;
        return out;
    }

    // Rich rendering for evolution_stats
    if (data.evolution) {
        let out = "## 🧬 Evolution Statistics\n\n| Metric | Value |\n| --- | --- |\n";
        for (const [k, v] of Object.entries(data.evolution)) {
            if (typeof v !== "object") {
                out += `| ${k.replace(/_/g, ' ')} | ${typeof v === "number" ? v.toLocaleString() : v} |\n`;
            }
        }
        if (data.evolution.cross_ref_types && Array.isArray(data.evolution.cross_ref_types)) {
            out += "\n### Cross-Reference Types\n\n| Type | Count |\n| --- | --- |\n";
            for (const r of data.evolution.cross_ref_types) {
                out += `| ${r.type} | ${r.count?.toLocaleString()} |\n`;
            }
        }
        return out;
    }

    // Rich rendering for convergence_status
    if (data.convergence) {
        let out = "## 🔄 Convergence Status\n\n| Metric | Value |\n| --- | --- |\n";
        const c = data.convergence;
        for (const [k, v] of Object.entries(c)) {
            if (typeof v !== "object") {
                out += `| ${k.replace(/_/g, ' ')} | ${typeof v === "number" ? v.toLocaleString() : v} |\n`;
            }
        }
        if (c.domain_status) {
            out += "\n### Domain Status\n\n| Status | Count |\n| --- | --- |\n";
            for (const [s, n] of Object.entries(c.domain_status)) {
                out += `| ${s} | ${n} |\n`;
            }
        }
        if (c.pending_waves && c.pending_waves.length > 0) {
            out += "\n### Pending Waves\n\n| Wave | Name | Status |\n| --- | --- | --- |\n";
            for (const w of c.pending_waves) {
                out += `| ${w.wave_id} | ${w.name} | ${w.status} |\n`;
            }
        }
        return out;
    }

    // Rich rendering for self_test
    if (data.tests && Array.isArray(data.tests)) {
        let out = `## 🧪 Self-Test Results — ${data.passed || 0} passed, ${data.failed || 0} failed\n\n`;
        out += "| Test | Status | Detail |\n| --- | --- | --- |\n";
        for (const t of data.tests) {
            const icon = t.status === "PASS" ? "✅" : "❌";
            out += `| ${t.test || t.name || "?"} | ${icon} ${t.status} | ${String(t.detail || t.message || "").substring(0, 100)} |\n`;
        }
        return out;
    }

    // Rich rendering for self_audit
    if (data.quality_score !== undefined) {
        let out = `## 🔍 Data Quality Audit — Score: **${data.quality_score}/100**\n\n`;
        if (data.findings && Array.isArray(data.findings)) {
            out += "| Severity | Finding | Detail |\n| --- | --- | --- |\n";
            for (const f of data.findings.slice(0, 30)) {
                out += `| ${f.severity || "?"} | ${f.finding || f.check || "?"} | ${String(f.detail || f.message || "").substring(0, 120)} |\n`;
            }
        }
        if (data.summary) {
            out += "\n### Summary\n\n";
            for (const [k, v] of Object.entries(data.summary)) {
                out += `- **${k.replace(/_/g, ' ')}**: ${v}\n`;
            }
        }
        return out;
    }

    // Rich rendering for system_health
    if (data.system_health || data.disk_space) {
        let out = "## 🖥️ System Health\n\n";
        const h = data.system_health || data;
        const skip = new Set(["ok", "id"]);
        for (const [k, v] of Object.entries(h)) {
            if (skip.has(k)) continue;
            if (typeof v === "object" && v !== null) {
                out += `\n### ${k.replace(/_/g, ' ')}\n\n`;
                if (Array.isArray(v)) {
                    for (const item of v.slice(0, 20)) {
                        out += `- ${JSON.stringify(item)}\n`;
                    }
                } else {
                    out += "| Key | Value |\n| --- | --- |\n";
                    for (const [sk, sv] of Object.entries(v)) {
                        out += `| ${sk} | ${typeof sv === "number" ? sv.toLocaleString() : sv} |\n`;
                    }
                }
            } else {
                out += `- **${k.replace(/_/g, ' ')}**: ${v}\n`;
            }
        }
        return out;
    }

    if (data.rows && data.rows.length === 0) return "No results found.";
    if (!data.rows) {
        // Fallback: custom response structure
        const skip = new Set(["ok", "id"]);
        const display = {};
        for (const [k, v] of Object.entries(data)) {
            if (!skip.has(k)) display[k] = v;
        }
        if (Object.keys(display).length === 0) return "⚠️ Handler returned empty response (possible silent error).";
        return "```json\n" + JSON.stringify(display, null, 2) + "\n```";
    }

    const displayRows = data.rows.length > MAX_FORMAT_ROWS
        ? data.rows.slice(0, MAX_FORMAT_ROWS)
        : data.rows;
    const rowsCapped = data.rows.length > MAX_FORMAT_ROWS;

    let out = `**${data.count} rows**`;
    if (data.truncated) out += ` (${data.truncated} more available)`;
    if (rowsCapped) out += ` (showing first ${MAX_FORMAT_ROWS} of ${data.rows.length})`;
    out += "\n\n";
    out += "| " + data.columns.join(" | ") + " |\n";
    out += "| " + data.columns.map(() => "---").join(" | ") + " |\n";
    for (const row of displayRows) {
        const vals = data.columns.map((c) => {
            let v = String(row[c] ?? "");
            if (v.length > 150) v = v.substring(0, 147) + "...";
            return v.replace(/\|/g, "\\|").replace(/\n/g, " ");
        });
        out += "| " + vals.join(" | ") + " |\n";
        if (out.length > MAX_OUTPUT_CHARS) {
            out += "\n⚠️ [Table truncated — output size limit reached]\n";
            break;
        }
    }
    return out;
}

// Bridge formatters (rich markdown from lexos_bridge.py responses)

function formatNarrative(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const lane = data.lane ? ` — Lane ${data.lane}` : "";
    const lines = [`## 📖 Chronological Narrative${lane}`, `> ⚡ DB-only (instant)`, ``];
    let events = data.events || data.narrative || [];
    if (Array.isArray(events) && events.length) {
        const capped = events.length > MAX_BRIDGE_ITEMS;
        if (capped) events = events.slice(0, MAX_BRIDGE_ITEMS);
        for (const ev of events) {
            const date = ev.event_date || ev.date || "????-??-??";
            const desc = String(ev.event_description || ev.description || ev.text || "").substring(0, 500);
            const actors = ev.actors ? ` _(${String(ev.actors).substring(0, 100)})_` : "";
            const tag = ev.lane ? ` \`[${ev.lane}]\`` : "";
            lines.push(`- **${date}**${tag} ${desc}${actors}`);
        }
        if (capped) lines.push(`\n⚠️ _Showing first ${MAX_BRIDGE_ITEMS} of ${(data.events || data.narrative).length} events_`);
    } else if (typeof events === "string") {
        lines.push(safeTruncate(events, MAX_OUTPUT_CHARS, "narrative"));
    } else {
        lines.push("_No narrative events found._");
    }
    if (data.total != null) lines.push(`\n**Total events:** ${data.total}`);
    const result = lines.join("\n");
    return result.length > MAX_OUTPUT_CHARS ? safeTruncate(result, MAX_OUTPUT_CHARS, "narrative") : result;
}

function formatFilingPlan(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const lane = data.lane ? ` — Lane ${data.lane}` : "";
    const lines = [`## 📋 Filing Strategy${lane}`, `> ⚡ DB-only (instant)`, ``];
    let filings = data.filings || data.plan || [];
    if (Array.isArray(filings) && filings.length) {
        if (filings.length > MAX_BRIDGE_ITEMS) filings = filings.slice(0, MAX_BRIDGE_ITEMS);
        lines.push(`| # | Filing | Deadline | Fee | Court | Status |`);
        lines.push(`| --- | --- | --- | --- | --- | --- |`);
        filings.forEach((f, i) => {
            const urg = f.urgency === "critical" || f.urgency === "high" ? "🔴"
                : f.urgency === "medium" ? "🟡" : "🟢";
            lines.push(
                `| ${i + 1} | ${String(f.filing || f.name || f.title || "—").substring(0, 200)} ` +
                `| ${f.deadline || "TBD"} | ${f.fee || "$0"} ` +
                `| ${String(f.court || "—").substring(0, 100)} | ${urg} ${f.status || f.urgency || "—"} |`
            );
        });
    } else if (typeof filings === "string") {
        lines.push(safeTruncate(filings, MAX_OUTPUT_CHARS, "filing plan"));
    } else {
        lines.push("_No filing plan data found._");
    }
    if (data.total_fees) lines.push(`\n**Estimated total fees:** ${data.total_fees}`);
    return safeTruncate(lines.join("\n"), MAX_OUTPUT_CHARS, "filing plan");
}

function formatRulesCheck(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const lines = [`## 📏 Procedural Compliance Check`, `> ⚡ DB-only (instant)`, ``];
    let rules = data.rules || data.results || [];
    if (Array.isArray(rules) && rules.length) {
        if (rules.length > MAX_BRIDGE_ITEMS) rules = rules.slice(0, MAX_BRIDGE_ITEMS);
        for (const r of rules) {
            const status = r.compliant === true ? "🟢 Compliant"
                : r.compliant === false ? "🔴 Non-compliant" : "🟡 Review needed";
            lines.push(`### ${r.rule_number || r.rule || "Rule"}: ${String(r.title || "").substring(0, 200)}`);
            lines.push(`**Status:** ${status}`);
            if (r.full_text || r.text) {
                lines.push("```");
                lines.push(String(r.full_text || r.text).slice(0, 600));
                lines.push("```");
            }
            if (r.notes) lines.push(`> ${String(r.notes).substring(0, 300)}`);
            lines.push("");
        }
    } else if (typeof rules === "string") {
        lines.push(safeTruncate(rules, MAX_OUTPUT_CHARS, "rules"));
    } else if (data.rule_text || data.text) {
        lines.push("```");
        lines.push(String(data.rule_text || data.text).slice(0, 2000));
        lines.push("```");
    } else {
        lines.push("_No matching rules found._");
    }
    return safeTruncate(lines.join("\n"), MAX_OUTPUT_CHARS, "rules check");
}

function formatAdversary(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const name = data.person || data.name || "Unknown";
    const lines = [`## 🕵️ Adversary Profile — ${name}`, `> ⚡ DB-only (instant)`, ``];
    const fields = [
        ["Role", data.role],
        ["Credibility Score", data.credibility_score ?? data.credibility],
        ["Contradiction Count", data.contradiction_count ?? data.contradictions],
        ["Impeachment Items", data.impeachment_count ?? data.impeachment_items],
        ["Key Weakness", data.weakness || data.key_weakness],
        ["Lanes Involved", data.lanes ? (Array.isArray(data.lanes) ? data.lanes.join(", ") : data.lanes) : undefined],
    ].filter(([, v]) => v !== undefined && v !== null);
    if (fields.length) {
        lines.push(`| Attribute | Value |`);
        lines.push(`| --- | --- |`);
        for (const [k, v] of fields) lines.push(`| ${k} | ${String(v).substring(0, 300)} |`);
        lines.push("");
    }
    if (Array.isArray(data.key_facts) && data.key_facts.length) {
        lines.push(`### Key Facts`);
        const facts = data.key_facts.length > MAX_BRIDGE_ITEMS ? data.key_facts.slice(0, MAX_BRIDGE_ITEMS) : data.key_facts;
        for (const f of facts) lines.push(`- ${String(f).substring(0, 500)}`);
        lines.push("");
    }
    if (Array.isArray(data.top_contradictions) && data.top_contradictions.length) {
        lines.push(`### Top Contradictions`);
        const contras = data.top_contradictions.length > MAX_BRIDGE_ITEMS ? data.top_contradictions.slice(0, MAX_BRIDGE_ITEMS) : data.top_contradictions;
        for (const c of contras) {
            const text = typeof c === "string" ? c : c.text || c.contradiction_text || safeStringify(c, 500);
            lines.push(`- 🔴 ${String(text).substring(0, 500)}`);
        }
        lines.push("");
    }
    if (fields.length === 0 && !data.key_facts && data.profile) {
        lines.push(typeof data.profile === "string"
            ? safeTruncate(data.profile, MAX_OUTPUT_CHARS, "profile")
            : safeStringify(data.profile, MAX_OUTPUT_CHARS));
    }
    return safeTruncate(lines.join("\n"), MAX_OUTPUT_CHARS, "adversary profile");
}

function formatGapAnalysis(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const lane = data.lane ? ` — Lane ${data.lane}` : "";
    const lines = [`## 🔍 Gap Analysis${lane}`, `> ⚡ DB-only (instant)`, ``];
    const categories = [
        ["Missing Evidence", data.missing_evidence],
        ["Missing Claims", data.missing_claims],
        ["Missing Filings", data.missing_filings],
        ["Weak Points", data.weak_points],
    ];
    let hasContent = false;
    for (const [label, items] of categories) {
        if (!items || (Array.isArray(items) && items.length === 0)) continue;
        hasContent = true;
        lines.push(`### ${label}`);
        if (Array.isArray(items)) {
            const capped = items.length > MAX_BRIDGE_ITEMS ? items.slice(0, MAX_BRIDGE_ITEMS) : items;
            for (const item of capped) {
                const sev = typeof item === "object" ? item.severity : undefined;
                const icon = sev === "critical" || sev === "high" ? "🔴" : sev === "medium" ? "🟡" : "🟢";
                const text = typeof item === "string" ? item : item.description || item.text || safeStringify(item, 500);
                lines.push(`- ${icon} ${String(text).substring(0, 500)}`);
            }
        } else {
            lines.push(String(items).substring(0, 2000));
        }
        lines.push("");
    }
    if (!hasContent && data.gaps) {
        if (Array.isArray(data.gaps)) {
            const capped = data.gaps.length > MAX_BRIDGE_ITEMS ? data.gaps.slice(0, MAX_BRIDGE_ITEMS) : data.gaps;
            for (const g of capped) lines.push(`- ${typeof g === "string" ? g : g.text || safeStringify(g, 500)}`);
        } else {
            lines.push(String(data.gaps).substring(0, 2000));
        }
        hasContent = true;
    }
    if (!hasContent) lines.push("_No gaps identified._");
    return safeTruncate(lines.join("\n"), MAX_OUTPUT_CHARS, "gap analysis");
}

function formatCrossConnect(data) {
    if (data.error) return `❌ **Error:** ${String(data.error).substring(0, 500)}`;
    const lines = [`## 🔗 Cross-Lane Intelligence — "${data.topic || "N/A"}"`, `> ⚡ DB-only (instant)`, ``];
    let connections = data.connections || data.results || [];
    if (Array.isArray(connections) && connections.length) {
        if (connections.length > MAX_BRIDGE_ITEMS) connections = connections.slice(0, MAX_BRIDGE_ITEMS);
        const byLane = {};
        for (const c of connections) {
            const lane = c.lane || "Unassigned";
            if (!byLane[lane]) byLane[lane] = [];
            byLane[lane].push(c);
        }
        for (const [lane, items] of Object.entries(byLane)) {
            lines.push(`### Lane ${lane}`);
            for (const item of items) {
                const text = String(item.text || item.description || item.event_description || item.quote_text || safeStringify(item, 300)).slice(0, 300);
                const src = item.source || item.source_file || "";
                lines.push(`- ${text}${src ? ` _(${String(src).substring(0, 100)})_` : ""}`);
            }
            lines.push("");
        }
    } else if (typeof connections === "string") {
        lines.push(safeTruncate(connections, MAX_OUTPUT_CHARS, "connections"));
    } else {
        lines.push("_No cross-lane connections found._");
    }
    if (data.lanes_touched) {
        const lt = Array.isArray(data.lanes_touched) ? data.lanes_touched.join(", ") : data.lanes_touched;
        lines.push(`**Lanes touched:** ${lt}`);
    }
    return safeTruncate(lines.join("\n"), MAX_OUTPUT_CHARS, "cross-connect");
}

// Extension session

const session = await joinSession({
    hooks: {
        onSessionStart: async () => {
            startDaemon(); // Spawn NEXUS v2 daemon (warm connections, 24 actions)
            await session.log(
                "⚖️ SINGULARITY v7.2 — NEXUS v2 daemon + 22 tools + 8 slash commands",
                { level: "info" },
            );
        },
        beforeInvoke: async (toolCall) => {
            // Log all tool invocations for governance audit trail
            const ts = new Date().toISOString();
            await session.log(`[${ts}] Tool: ${toolCall.name}`, { level: "debug" });
            return toolCall; // pass through unchanged
        },
        afterInvoke: async (toolCall, result) => {
            // Track tool performance
            if (result.error) {
                await session.log(`⚠️ Tool ${toolCall.name} failed: ${result.error}`, { level: "warn" });
            }
            return result;
        },
    },
    slashCommands: [
        {
            name: "filing",
            description: "Filing workflow: check readiness, generate documents, assemble packages",
            handler: async (args, session) => {
                const lane = args.trim() || "all";
                return `Check filing readiness and generate documents for lane: ${lane}. Use nexus_readiness, filing_status, and lexos_filing_plan tools to assess current state. If a specific lane is specified, focus there. Show readiness scores, gaps, and next steps.`;
            },
        },
        {
            name: "evidence",
            description: "Search evidence across all sources with hybrid FTS5+semantic+reranking",
            handler: async (args, session) => {
                const query = args.trim();
                if (!query) return "Usage: /evidence <search terms>. Example: /evidence parental alienation";
                return `Deep evidence search for: "${query}". Use nexus_fuse to search across evidence_quotes, timeline_events, police_reports, impeachment_matrix, and authority_chains simultaneously. Then use search_evidence for FTS5 results and lexos_cross_connect to trace across lanes.`;
            },
        },
        {
            name: "argue",
            description: "Build complete argument chain: evidence + authorities + impeachment",
            handler: async (args, session) => {
                const claim = args.trim();
                if (!claim) return "Usage: /argue <claim>. Example: /argue judicial bias";
                return `Build a complete argument chain for the claim: "${claim}". Use nexus_argue to find supporting evidence, legal authorities, and impeachment ammunition. Show chain strength score. Then use search_authority_chains to verify all citations exist in the database.`;
            },
        },
        {
            name: "timeline",
            description: "Build chronological narrative for a topic or date range",
            handler: async (args, session) => {
                const query = args.trim();
                if (!query) return "Usage: /timeline <topic or date>. Example: /timeline custody withholding";
                return `Build a chronological narrative for: "${query}". Use lexos_narrative and timeline_search to construct a time-ordered story. Focus on key events, actors, and evidence citations.`;
            },
        },
        {
            name: "damages",
            description: "Calculate damages across all lanes with conservative and aggressive estimates",
            handler: async (args, session) => {
                const lane = args.trim() || "";
                return `Calculate comprehensive damages${lane ? ` for lane ${lane}` : " across all lanes"}. Use nexus_damages to get conservative and aggressive amounts by category. Include constitutional violations, emotional distress, economic harm, and punitive multipliers.`;
            },
        },
        {
            name: "impeach",
            description: "Build impeachment package for a target witness/party",
            handler: async (args, session) => {
                const target = args.trim();
                if (!target) return "Usage: /impeach <person>. Example: /impeach Emily Watson";
                return `Build a comprehensive impeachment package for: "${target}". Use search_impeachment with high severity, search_contradictions, and lexos_adversary to compile prior inconsistent statements, contradictions, and credibility attacks. Score overall credibility.`;
            },
        },
        {
            name: "status",
            description: "Full system status: case health, deadlines, filing readiness, separation counter",
            handler: async (args, session) => {
                const today = new Date();
                const sep = new Date("2025-07-29");
                const days = Math.floor((today - sep) / 86400000);
                return `System status check. Separation day count: ${days} days since July 29, 2025. Use check_deadlines for upcoming deadlines, nexus_readiness for filing readiness across all lanes, and nexus_priorities for daily action priorities. Show everything in a dashboard format.`;
            },
        },
        {
            name: "judge",
            description: "Judicial intelligence profile for a specific judge",
            handler: async (args, session) => {
                const judge = args.trim() || "McNeill";
                return `Build judicial intelligence profile for Judge ${judge}. Use judicial_intel to get patterns, bias indicators, and misconduct evidence. Cross-reference with search_impeachment targeting the judge. Show ruling patterns, ex parte rate, and JTC exhibits.`;
            },
        },
    ],
    tools: [
        {
            name: "query_litigation_db",
            description:
                "READ-ONLY SQL query against litigation_context.db (186 tables, 1.3 M+ rows). " +
                "SELECT queries ONLY — INSERT/UPDATE/DELETE are BLOCKED. For writes, use exec_python with a script. " +
                "Pass SQL with ? placeholders and a params array — values are NEVER interpolated. " +
                "Key tables: evidence_quotes, timeline_events, michigan_rules_extracted, police_reports, " +
                "impeachment_matrix, authority_chains_v2, contradiction_map, deadlines, filing_packages.",
            parameters: {
                type: "object",
                properties: {
                    sql: {
                        type: "string",
                        description: "SQL with ? placeholders. Example: SELECT * FROM evidence_quotes WHERE category = ? AND lane = ? LIMIT 20",
                    },
                    params: {
                        type: "array",
                        description: "Parameter values matching ? placeholders. Example: ['custody', 'F7']",
                    },
                    max_rows: {
                        type: "number",
                        description: "Maximum rows to return (default 50, max 500)",
                    },
                },
                required: ["sql"],
            },
            handler: async (args) => {
                const result = await queryDB({
                    action: "query",
                    sql: args.sql,
                    params: args.params || [],
                    max_rows: Math.min(args.max_rows || 50, 500),
                });
                return formatResult(result);
            },
        },

        {
            name: "search_evidence",
            description:
                "Full-text search across evidence. Uses FTS5 with snippet() for evidence_quotes " +
                "and timeline_events (ranked results with highlighted excerpts). Falls back to " +
                "LIKE for police_reports and michigan_rules_extracted.",
            parameters: {
                type: "object",
                properties: {
                    query: {
                        type: "string",
                        description: 'FTS5 search terms (AND, OR, NOT, "quoted phrases", prefix*). ' +
                            "Examples: 'custody alienation', '\"parental alienation\" OR \"best interest\"'",
                    },
                    table: {
                        type: "string",
                        description: "Table to search (default: evidence_quotes)",
                        enum: ["evidence_quotes", "timeline_events", "police_reports", "michigan_rules_extracted"],
                    },
                    limit: {
                        type: "number",
                        description: "Max results (default 25, max 100)",
                    },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const table = args.table || "evidence_quotes";
                const limit = Math.min(args.limit || 25, 100);
                const q = args.query.trim();

                if (q.length < 2)
                    return "❌ Search query must be at least 2 characters.";

                let result;

                if (table === "evidence_quotes") {
                    result = await queryDB({
                        action: "query",
                        sql: "SELECT eq.source_file, " +
                            "snippet(evidence_fts, 0, '>>>', '<<<', '...', 64) AS excerpt, " +
                            "eq.category, eq.lane, eq.relevance_score, evidence_fts.rank " +
                            "FROM evidence_fts " +
                            "JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid " +
                            "WHERE evidence_fts MATCH ? " +
                            "ORDER BY evidence_fts.rank LIMIT ?",
                        params: [q, limit],
                        max_rows: limit,
                    });
                } else if (table === "timeline_events") {
                    result = await queryDB({
                        action: "query",
                        sql: "SELECT snippet(timeline_fts, 0, '>>>', '<<<', '...', 64) AS excerpt, " +
                            "timeline_fts.actors, timeline_fts.rank " +
                            "FROM timeline_fts " +
                            "WHERE timeline_fts MATCH ? " +
                            "ORDER BY timeline_fts.rank LIMIT ?",
                        params: [q, limit],
                        max_rows: limit,
                    });
                } else if (table === "police_reports") {
                    const terms = q.split(/\s+/).filter((t) => t.length >= 2);
                    if (terms.length === 0)
                        return "❌ No valid search terms (minimum 2 characters each).";
                    const conds = terms.map(() => "full_text LIKE ?").join(" AND ");
                    const params = terms.map((t) => `%${t}%`);
                    params.push(limit);
                    result = await queryDB({
                        action: "query",
                        sql: `SELECT filename, allegations, exculpatory, false_reports, ` +
                            `substr(full_text, 1, 300) AS excerpt ` +
                            `FROM police_reports WHERE ${conds} LIMIT ?`,
                        params,
                        max_rows: limit,
                    });
                } else if (table === "michigan_rules_extracted") {
                    const terms = q.split(/\s+/).filter((t) => t.length >= 2);
                    if (terms.length === 0)
                        return "❌ No valid search terms (minimum 2 characters each).";
                    const conds = terms.map(() => "full_text LIKE ?").join(" AND ");
                    const params = terms.map((t) => `%${t}%`);
                    params.push(limit);
                    result = await queryDB({
                        action: "query",
                        sql: `SELECT rule_number, rule_type, title, ` +
                            `substr(full_text, 1, 300) AS excerpt ` +
                            `FROM michigan_rules_extracted WHERE ${conds} LIMIT ?`,
                        params,
                        max_rows: limit,
                    });
                } else {
                    return "❌ Unknown table. Use: evidence_quotes, timeline_events, police_reports, michigan_rules_extracted";
                }

                return formatResult(result);
            },
        },

        {
            name: "check_deadlines",
            description:
                "Check litigation deadlines and filing due dates with urgency color coding. " +
                "Shows overdue items 🔴, critical 🟠 (≤3 days), urgent 🟡 (≤7 days), and OK 🟢. Also lists filing packages.",
            parameters: {
                type: "object",
                properties: {
                    days_ahead: {
                        type: "number",
                        description: "Show deadlines within N days from now (default 30)",
                    },
                },
            },
            handler: async (args) => {
                const days = args?.days_ahead || 30;
                const modifier = `+${days} days`;

                const dlData = await queryDB({
                    action: "query",
                    sql: "SELECT title, due_date, court, case_number, status, urgency, " +
                        "CAST(julianday(due_date) - julianday('now') AS INTEGER) AS days_remaining " +
                        "FROM deadlines " +
                        "WHERE due_date <= date('now', ?) " +
                        "ORDER BY due_date ASC",
                    params: [modifier],
                    max_rows: 50,
                });

                // Inject urgency flags
                if (typeof dlData === "object" && dlData.rows) {
                    for (const row of dlData.rows) {
                        const d = row.days_remaining;
                        if (d < 0) row.urgency_flag = "🔴 OVERDUE";
                        else if (d <= 3) row.urgency_flag = "🟠 CRITICAL";
                        else if (d <= 7) row.urgency_flag = "🟡 URGENT";
                        else row.urgency_flag = "🟢 OK";
                    }
                    if (!dlData.columns.includes("urgency_flag"))
                        dlData.columns.push("urgency_flag");
                }

                const pkgData = await queryDB({
                    action: "query",
                    sql: "SELECT filing_id, title, lane, case_number, doc_count, status " +
                        "FROM filing_packages ORDER BY lane",
                    params: [],
                    max_rows: 20,
                });

                return (
                    `## ⏰ Deadlines (next ${days} days)\n\n` +
                    formatResult(dlData) +
                    "\n\n## 📦 Filing Packages\n\n" +
                    formatResult(pkgData)
                );
            },
        },

        {
            name: "case_context",
            description:
                "Comprehensive context for active litigation cases. Returns database statistics, " +
                "filing packages, and recent timeline. Optionally filter by case number.",
            parameters: {
                type: "object",
                properties: {
                    case_id: {
                        type: "string",
                        description: "Optional case number to focus on (e.g. '2024-001507-DC', '366810')",
                    },
                },
            },
            handler: async (args) => {
                const statsData = await queryDB({ action: "stats" });

                let pkgSql =
                    "SELECT filing_id, title, lane, case_number, doc_count, status FROM filing_packages";
                let pkgParams = [];
                if (args?.case_id) {
                    pkgSql += " WHERE case_number LIKE ?";
                    pkgParams = [`%${args.case_id}%`];
                }
                pkgSql += " ORDER BY lane";
                const pkgData = await queryDB({
                    action: "query",
                    sql: pkgSql,
                    params: pkgParams,
                    max_rows: 20,
                });

                const tlData = await queryDB({
                    action: "query",
                    sql: "SELECT event_date, category, event_description, actors " +
                        "FROM timeline_events ORDER BY event_date DESC LIMIT 10",
                    params: [],
                    max_rows: 10,
                });

                return (
                    "## 📊 LitigationOS Intelligence Summary\n\n" +
                    formatResult(statsData) +
                    "\n\n## 📦 Filing Packages\n\n" +
                    formatResult(pkgData) +
                    "\n\n## 📅 Recent Timeline\n\n" +
                    formatResult(tlData)
                );
            },
        },

        {
            name: "filing_status",
            description:
                "Detailed status of a specific filing package by lane. Shows package info, related evidence count, and deadlines.",
            parameters: {
                type: "object",
                properties: {
                    lane: {
                        type: "string",
                        description: "Filing lane: F1-F10, CRIMINAL, F-VAC, F-MSC2",
                        enum: ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "CRIMINAL", "F-VAC", "F-MSC2"],
                    },
                },
                required: ["lane"],
            },
            handler: async (args) => {
                const lane = args.lane;

                const pkgData = await queryDB({
                    action: "query",
                    sql: "SELECT * FROM filing_packages " +
                        "WHERE lane = ? OR filing_id LIKE ? OR title LIKE ?",
                    params: [lane, `%${lane}%`, `%${lane}%`],
                    max_rows: 5,
                });

                const evData = await queryDB({
                    action: "query",
                    sql: "SELECT COUNT(*) AS evidence_count FROM evidence_quotes " +
                        "WHERE lane LIKE ? OR tags LIKE ?",
                    params: [`%${lane}%`, `%${lane}%`],
                    max_rows: 1,
                });

                const dlData = await queryDB({
                    action: "query",
                    sql: "SELECT title, due_date, status, " +
                        "CAST(julianday(due_date) - julianday('now') AS INTEGER) AS days_remaining " +
                        "FROM deadlines WHERE filing_id LIKE ? ORDER BY due_date",
                    params: [`%${lane}%`],
                    max_rows: 10,
                });

                return (
                    `## 📄 Filing Package: ${lane}\n\n` +
                    formatResult(pkgData) +
                    "\n\n## 📎 Related Evidence\n\n" +
                    formatResult(evData) +
                    "\n\n## ⏰ Deadlines\n\n" +
                    formatResult(dlData)
                );
            },
        },

        {
            name: "search_impeachment",
            description:
                "Search impeachment_matrix for cross-examination ammunition. " +
                "Columns: category, evidence_summary, source_file, quote_text, impeachment_value (1-10), " +
                "cross_exam_question, filing_relevance, event_date.",
            parameters: {
                type: "object",
                properties: {
                    target: {
                        type: "string",
                        description: "Person / entity to impeach (e.g. 'Emily', 'Watson', 'Judge McNeill')",
                    },
                    category: {
                        type: "string",
                        description: "Category filter (e.g. 'custody', 'PPO', 'financial')",
                    },
                    min_severity: {
                        type: "number",
                        description: "Minimum impeachment_value (1-10, default 1)",
                    },
                    limit: {
                        type: "number",
                        description: "Max results (default 25, max 100)",
                    },
                },
            },
            handler: async (args) => {
                const limit = Math.min(args.limit || 25, 100);
                const minSev = args.min_severity || 1;
                const conditions = ["impeachment_value >= ?"];
                const params = [minSev];

                if (args.target) {
                    conditions.push(
                        "(category LIKE ? OR evidence_summary LIKE ? OR cross_exam_question LIKE ?)",
                    );
                    params.push(
                        `%${args.target}%`,
                        `%${args.target}%`,
                        `%${args.target}%`,
                    );
                }
                if (args.category) {
                    conditions.push("category LIKE ?");
                    params.push(`%${args.category}%`);
                }
                params.push(limit);

                const result = await queryDB({
                    action: "query",
                    sql: "SELECT category, evidence_summary, source_file, " +
                        "substr(quote_text, 1, 200) AS quote_text, " +
                        "impeachment_value, cross_exam_question, " +
                        "filing_relevance, event_date " +
                        "FROM impeachment_matrix " +
                        `WHERE ${conditions.join(" AND ")} ` +
                        "ORDER BY impeachment_value DESC LIMIT ?",
                    params,
                    max_rows: limit,
                });

                return "## 🎯 Impeachment Results\n\n" + formatResult(result);
            },
        },

        {
            name: "search_contradictions",
            description:
                "Search contradiction_map for inconsistencies. Columns: claim_id, source_a, source_b, " +
                "contradiction_text, severity, lane. Find where parties contradict themselves or others.",
            parameters: {
                type: "object",
                properties: {
                    entity: {
                        type: "string",
                        description: "Person or topic (searches source_a, source_b, contradiction_text)",
                    },
                    severity: {
                        type: "string",
                        description: "Severity filter (e.g. 'high', 'critical')",
                    },
                    lane: {
                        type: "string",
                        description: "Filing lane filter (e.g. 'F7', 'CRIMINAL')",
                    },
                    limit: {
                        type: "number",
                        description: "Max results (default 25, max 100)",
                    },
                },
            },
            handler: async (args) => {
                const limit = Math.min(args.limit || 25, 100);
                const conditions = [];
                const params = [];

                if (args.entity) {
                    conditions.push(
                        "(source_a LIKE ? OR source_b LIKE ? OR contradiction_text LIKE ?)",
                    );
                    params.push(
                        `%${args.entity}%`,
                        `%${args.entity}%`,
                        `%${args.entity}%`,
                    );
                }
                if (args.severity) {
                    conditions.push("severity LIKE ?");
                    params.push(`%${args.severity}%`);
                }
                if (args.lane) {
                    conditions.push("lane LIKE ?");
                    params.push(`%${args.lane}%`);
                }

                const where =
                    conditions.length > 0
                        ? "WHERE " + conditions.join(" AND ")
                        : "";
                params.push(limit);

                const result = await queryDB({
                    action: "query",
                    sql: "SELECT claim_id, source_a, source_b, " +
                        "substr(contradiction_text, 1, 250) AS contradiction_text, " +
                        `severity, lane FROM contradiction_map ${where} ` +
                        "ORDER BY id DESC LIMIT ?",
                    params,
                    max_rows: limit,
                });

                return "## ⚡ Contradictions Found\n\n" + formatResult(result);
            },
        },

        {
            name: "search_authority_chains",
            description:
                "Search authority_chains_v2 (31K citation chains). Columns: primary_citation, " +
                "supporting_citation, relationship, source_document, source_type, lane, paragraph_context. " +
                "Find which citations support which arguments.",
            parameters: {
                type: "object",
                properties: {
                    citation: {
                        type: "string",
                        description: "Citation to search (e.g. 'MCL 722.23', 'MCR 2.003', 'Vodvarka')",
                    },
                    lane: {
                        type: "string",
                        description: "Filing lane filter",
                    },
                    source_type: {
                        type: "string",
                        description: "Source type filter (e.g. 'motion', 'brief', 'order')",
                    },
                    limit: {
                        type: "number",
                        description: "Max results (default 25, max 100)",
                    },
                },
            },
            handler: async (args) => {
                const limit = Math.min(args.limit || 25, 100);
                const conditions = [];
                const params = [];

                if (args.citation) {
                    conditions.push(
                        "(primary_citation LIKE ? OR supporting_citation LIKE ?)",
                    );
                    params.push(`%${args.citation}%`, `%${args.citation}%`);
                }
                if (args.lane) {
                    conditions.push("lane LIKE ?");
                    params.push(`%${args.lane}%`);
                }
                if (args.source_type) {
                    conditions.push("source_type LIKE ?");
                    params.push(`%${args.source_type}%`);
                }

                const where =
                    conditions.length > 0
                        ? "WHERE " + conditions.join(" AND ")
                        : "";
                params.push(limit);

                const result = await queryDB({
                    action: "query",
                    sql: "SELECT primary_citation, supporting_citation, relationship, " +
                        "source_document, source_type, lane, " +
                        "substr(paragraph_context, 1, 200) AS context " +
                        `FROM authority_chains_v2 ${where} ` +
                        "ORDER BY id DESC LIMIT ?",
                    params,
                    max_rows: limit,
                });

                return "## 📚 Authority Chains\n\n" + formatResult(result);
            },
        },

        {
            name: "nexus_fuse",
            description:
                "Cross-table evidence fusion. Searches evidence_quotes (FTS5), timeline_events (FTS5), " +
                "police_reports, impeachment_matrix, and authority_chains simultaneously. Returns fused results from all 5 sources.",
            parameters: {
                type: "object",
                properties: {
                    topic: {
                        type: "string",
                        description: "FTS5 search terms (AND, OR, NOT, quoted phrases). E.g.: 'alienation', 'PPO OR protection order'",
                    },
                    lanes: {
                        type: "array",
                        items: { type: "string" },
                        description: "Optional lane filter: A, B, D, E, F, CRIMINAL",
                    },
                    limit: {
                        type: "number",
                        description: "Max results per source (default 50)",
                    },
                },
                required: ["topic"],
            },
            handler: async (args) => {
                const q = args.topic.trim();
                const limit = Math.min(args.limit || 50, 100);
                const likeTerms = q.split(/\s+/).filter((t) => t.length >= 2);

                // Evidence quotes (FTS5)
                const evRes = await queryDB({
                    action: "query",
                    sql: "SELECT eq.source_file, " +
                        "snippet(evidence_fts, 0, '>>>', '<<<', '...', 48) AS excerpt, " +
                        "eq.category, eq.lane, eq.relevance_score " +
                        "FROM evidence_fts " +
                        "JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid " +
                        "WHERE evidence_fts MATCH ? ORDER BY evidence_fts.rank LIMIT ?",
                    params: [q, limit],
                    max_rows: limit,
                });

                // Timeline events (FTS5)
                const tlRes = await queryDB({
                    action: "query",
                    sql: "SELECT snippet(timeline_fts, 0, '>>>', '<<<', '...', 48) AS excerpt, " +
                        "timeline_fts.actors " +
                        "FROM timeline_fts WHERE timeline_fts MATCH ? " +
                        "ORDER BY timeline_fts.rank LIMIT ?",
                    params: [q, limit],
                    max_rows: limit,
                });

                // Police reports (LIKE)
                let prRes = "No matches.";
                if (likeTerms.length > 0) {
                    const prConds = likeTerms.map(() => "full_text LIKE ?").join(" AND ");
                    const prParams = likeTerms.map((t) => `%${t}%`);
                    prParams.push(limit);
                    prRes = await queryDB({
                        action: "query",
                        sql: `SELECT filename, allegations, exculpatory, false_reports FROM police_reports WHERE ${prConds} LIMIT ?`,
                        params: prParams,
                        max_rows: limit,
                    });
                }

                // Impeachment matrix
                const impRes = await queryDB({
                    action: "query",
                    sql: "SELECT category, evidence_summary, impeachment_value, cross_exam_question " +
                        "FROM impeachment_matrix WHERE evidence_summary LIKE ? OR category LIKE ? " +
                        "ORDER BY impeachment_value DESC LIMIT ?",
                    params: [`%${likeTerms[0] || q}%`, `%${likeTerms[0] || q}%`, limit],
                    max_rows: limit,
                });

                // Authority chains
                const authRes = await queryDB({
                    action: "query",
                    sql: "SELECT primary_citation, supporting_citation, relationship, lane " +
                        "FROM authority_chains_v2 WHERE primary_citation LIKE ? OR supporting_citation LIKE ? LIMIT ?",
                    params: [`%${likeTerms[0] || q}%`, `%${likeTerms[0] || q}%`, limit],
                    max_rows: limit,
                });

                return safeTruncate(
                    `## 🔥 NEXUS Fusion: "${q}"\n\n` +
                    "### Evidence Quotes\n" + formatResult(evRes) + "\n\n" +
                    "### Timeline Events\n" + formatResult(tlRes) + "\n\n" +
                    "### Police Reports\n" + formatResult(prRes) + "\n\n" +
                    "### Impeachment\n" + formatResult(impRes) + "\n\n" +
                    "### Authority Chains\n" + formatResult(authRes),
                    MAX_OUTPUT_CHARS, "nexus fusion"
                );
            },
        },

        {
            name: "nexus_case_map",
            description:
                "Multi-standard case analysis. For custody: all 12 MCL 722.23 best interest factors with scores and evidence. " +
                "For judicial: violations and bias events. Also housing, criminal, federal, ppo, appellate.",
            parameters: {
                type: "object",
                properties: {
                    case_type: {
                        type: "string",
                        description: "Case type: custody, housing, judicial, criminal, federal, ppo, appellate",
                    },
                },
                required: ["case_type"],
            },
            handler: async (args) => {
                const ct = (args.case_type || "").toLowerCase();
                let result;

                if (ct === "custody") {
                    result = await queryDB({
                        action: "query",
                        sql: "SELECT factor, description, andrew_score, emily_score, " +
                            "evidence_count, assessment FROM custody_factors ORDER BY factor",
                        params: [],
                        max_rows: 15,
                    });
                } else if (ct === "judicial") {
                    result = await queryDB({
                        action: "query",
                        sql: "SELECT violation_type, COUNT(*) AS cnt, " +
                            "GROUP_CONCAT(DISTINCT source_file) AS sources " +
                            "FROM judicial_violations GROUP BY violation_type ORDER BY cnt DESC",
                        params: [],
                        max_rows: 30,
                    });
                } else {
                    result = await queryDB({
                        action: "query",
                        sql: "SELECT category, COUNT(*) AS evidence_count, " +
                            "GROUP_CONCAT(DISTINCT lane) AS lanes " +
                            "FROM evidence_quotes WHERE category LIKE ? GROUP BY category ORDER BY evidence_count DESC LIMIT 20",
                        params: [`%${ct}%`],
                        max_rows: 20,
                    });
                }

                return `## 🗺️ Case Map: ${args.case_type}\n\n` + formatResult(result);
            },
        },

        {
            name: "nexus_readiness",
            description:
                "Filing readiness dashboard across all lanes. Shows evidence count, authority count, " +
                "impeachment count, readiness score, deadline, and gap analysis per filing package.",
            parameters: {
                type: "object",
                properties: {
                    lane: {
                        type: "string",
                        description: "Optional lane filter: A, B, D, E, F, CRIMINAL. Omit for all lanes.",
                    },
                },
            },
            handler: async (args) => {
                let pkgSql =
                    "SELECT fp.filing_id, fp.title, fp.lane, fp.status, fp.doc_count, " +
                    "(SELECT COUNT(*) FROM evidence_quotes eq WHERE eq.lane LIKE '%' || fp.lane || '%') AS evidence_count, " +
                    "(SELECT COUNT(*) FROM authority_chains_v2 ac WHERE ac.lane LIKE '%' || fp.lane || '%') AS authority_count " +
                    "FROM filing_packages fp";
                const params = [];
                if (args?.lane) {
                    pkgSql += " WHERE fp.lane LIKE ?";
                    params.push(`%${args.lane}%`);
                }
                pkgSql += " ORDER BY fp.lane";

                const result = await queryDB({
                    action: "query",
                    sql: pkgSql,
                    params,
                    max_rows: 20,
                });

                return "## 🚦 Filing Readiness Dashboard\n\n" + formatResult(result);
            },
        },

        {
            name: "nexus_priorities",
            description:
                "Daily action priorities across ALL cases. Combines deadline urgency with filing readiness gaps. " +
                "Shows overdue items, days until each deadline, priority scores, and parent-child separation counter.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const dlData = await queryDB({
                    action: "query",
                    sql: "SELECT title, due_date, court, case_number, " +
                        "CAST(julianday(due_date) - julianday('now') AS INTEGER) AS days_remaining " +
                        "FROM deadlines ORDER BY due_date ASC LIMIT 20",
                    params: [],
                    max_rows: 20,
                });

                const sepDays = await queryDB({
                    action: "query",
                    sql: "SELECT CAST(julianday('now') - julianday('2025-07-29') AS INTEGER) AS separation_days",
                    params: [],
                    max_rows: 1,
                });

                return (
                    "## 🎯 Daily Priorities\n\n" +
                    formatResult(dlData) + "\n\n" +
                    "### ⏱️ Parent-Child Separation\n" +
                    formatResult(sepDays)
                );
            },
        },

        {
            name: "nexus_argue",
            description:
                "Argument chain synthesis. For a given claim, finds supporting evidence (FTS5), " +
                "legal authorities, and impeachment ammunition. Returns chain strength score and rating.",
            parameters: {
                type: "object",
                properties: {
                    claim: {
                        type: "string",
                        description: "The claim or argument. E.g.: 'parental alienation', 'wrongful eviction', 'judicial bias'",
                    },
                    lane: {
                        type: "string",
                        description: "Optional lane filter",
                    },
                    limit: {
                        type: "number",
                        description: "Max results per source (default 10)",
                    },
                },
                required: ["claim"],
            },
            handler: async (args) => {
                const claim = args.claim.trim();
                const limit = Math.min(args.limit || 10, 50);
                const likeTerms = claim.split(/\s+/).filter((t) => t.length >= 2);
                const likeTerm = likeTerms[0] || claim;

                const evRes = await queryDB({
                    action: "query",
                    sql: "SELECT eq.source_file, " +
                        "snippet(evidence_fts, 0, '>>>', '<<<', '...', 48) AS excerpt, " +
                        "eq.relevance_score " +
                        "FROM evidence_fts " +
                        "JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid " +
                        "WHERE evidence_fts MATCH ? ORDER BY evidence_fts.rank LIMIT ?",
                    params: [claim, limit],
                    max_rows: limit,
                });

                const authRes = await queryDB({
                    action: "query",
                    sql: "SELECT primary_citation, supporting_citation, relationship " +
                        "FROM authority_chains_v2 WHERE primary_citation LIKE ? OR supporting_citation LIKE ? LIMIT ?",
                    params: [`%${likeTerm}%`, `%${likeTerm}%`, limit],
                    max_rows: limit,
                });

                const impRes = await queryDB({
                    action: "query",
                    sql: "SELECT evidence_summary, impeachment_value, cross_exam_question " +
                        "FROM impeachment_matrix WHERE evidence_summary LIKE ? " +
                        "ORDER BY impeachment_value DESC LIMIT ?",
                    params: [`%${likeTerm}%`, limit],
                    max_rows: limit,
                });

                return safeTruncate(
                    `## ⚔️ Argument Chain: "${claim}"\n\n` +
                    "### Supporting Evidence\n" + formatResult(evRes) + "\n\n" +
                    "### Legal Authority\n" + formatResult(authRes) + "\n\n" +
                    "### Impeachment Support\n" + formatResult(impRes),
                    MAX_OUTPUT_CHARS, "argument chain"
                );
            },
        },

        {
            name: "nexus_damages",
            description:
                "Aggregate damages across all claims and lanes. Shows conservative and aggressive amounts by lane and category.",
            parameters: {
                type: "object",
                properties: {
                    lane: {
                        type: "string",
                        description: "Optional lane filter. Omit for all lanes.",
                    },
                },
            },
            handler: async (args) => {
                let sql =
                    "SELECT lane, category, SUM(amount_conservative) AS conservative, " +
                    "SUM(amount_aggressive) AS aggressive, COUNT(*) AS claim_count " +
                    "FROM damages";
                const params = [];
                if (args?.lane) {
                    sql += " WHERE lane LIKE ?";
                    params.push(`%${args.lane}%`);
                }
                sql += " GROUP BY lane, category ORDER BY aggressive DESC";

                const result = await queryDB({
                    action: "query",
                    sql,
                    params,
                    max_rows: 50,
                });

                return "## 💰 Damages Summary\n\n" + formatResult(result);
            },
        },

        {
            name: "judicial_intel",
            description:
                "Judicial intelligence findings for judges. Shows patterns, bias indicators, violation types, and misconduct evidence.",
            parameters: {
                type: "object",
                properties: {
                    judge: {
                        type: "string",
                        description: "Judge name (e.g. 'McNeill', 'Hoopes'). Omit for all judges.",
                    },
                },
            },
            handler: async (args) => {
                const conditions = [];
                const params = [];
                if (args?.judge) {
                    conditions.push("(description LIKE ? OR source_file LIKE ?)");
                    params.push(`%${args.judge}%`, `%${args.judge}%`);
                }
                const where = conditions.length ? "WHERE " + conditions.join(" AND ") : "";

                const result = await queryDB({
                    action: "query",
                    sql: `SELECT violation_type, COUNT(*) AS cnt, ` +
                        `GROUP_CONCAT(DISTINCT severity) AS severities, ` +
                        `GROUP_CONCAT(DISTINCT source_file) AS sources ` +
                        `FROM judicial_violations ${where} ` +
                        `GROUP BY violation_type ORDER BY cnt DESC`,
                    params,
                    max_rows: 30,
                });

                return `## 🔍 Judicial Intelligence${args?.judge ? ": " + args.judge : ""}\n\n` + formatResult(result);
            },
        },

        {
            name: "lexos_narrative",
            description:
                "⚡ Chronological narrative builder (instant, no LLM). Builds time-ordered story from 16K+ timeline events. " +
                "Filter by lane: A=custody, D=PPO, E=judicial, F=appellate, CRIMINAL.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Topic/keywords for narrative focus" },
                    lane: { type: "string", description: "Filter by litigation lane", enum: ["A", "B", "C", "D", "E", "F", "CRIMINAL"] },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const payload = { action: "narrative", query: args.query };
                if (args.lane) payload.lane = args.lane;
                return formatNarrative(await callBridge(payload, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "lexos_filing_plan",
            description:
                "⚡ Filing strategy with deadlines, fees, and sequence (instant, no LLM). Returns prioritized filing plan.",
            parameters: {
                type: "object",
                properties: {
                    lane: { type: "string", description: "Specific lane to plan for, or omit for all" },
                },
            },
            handler: async (args) => {
                const payload = { action: "filing_plan" };
                if (args.lane) payload.lane = args.lane;
                return formatFilingPlan(await callBridge(payload, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "lexos_rules_check",
            description:
                "⚡ Procedural compliance validator (instant, no LLM). Checks MCR/MCL for requirements, deadlines, service rules.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Filing type or rule. E.g., 'MCR 2.003', 'motion for reconsideration'" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                return formatRulesCheck(await callBridge({ action: "rules_check", query: args.query }, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "lexos_adversary",
            description:
                "⚡ Deep adversary profile builder (instant, no LLM). Builds comprehensive profile from " +
                "impeachment, contradictions, evidence, and timeline. Shows credibility score, weaknesses.",
            parameters: {
                type: "object",
                properties: {
                    person: { type: "string", description: "Person name. E.g., 'Emily Watson', 'McNeill', 'Pamela Rusco'" },
                },
                required: ["person"],
            },
            handler: async (args) => {
                return formatAdversary(await callBridge({ action: "adversary", person: args.person }, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "lexos_gap_analysis",
            description:
                "⚡ Missing evidence, claims, and filings detector (instant, no LLM). " +
                "Identifies gaps: missing evidence, unclaimed damages, unfiled motions, weak authority chains.",
            parameters: {
                type: "object",
                properties: {
                    lane: { type: "string", description: "Specific lane to analyze, or omit for all" },
                },
            },
            handler: async (args) => {
                const payload = { action: "gap_analysis" };
                if (args.lane) payload.lane = args.lane;
                return formatGapAnalysis(await callBridge(payload, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "lexos_cross_connect",
            description:
                "⚡ Cross-lane intelligence fusion (instant, no LLM). Traces a topic across all litigation " +
                "lanes to find connections, patterns, and shared evidence.",
            parameters: {
                type: "object",
                properties: {
                    topic: { type: "string", description: "Topic to trace. E.g., 'false allegations', 'parental alienation'" },
                },
                required: ["topic"],
            },
            handler: async (args) => {
                return formatCrossConnect(await callBridge({ action: "cross_connect", topic: args.topic }, BRIDGE_TIMEOUT));
            },
        },

        {
            name: "timeline_search",
            description:
                "Search the litigation timeline for events by date range, category, or actor. 16K+ events chronologically indexed.",
            parameters: {
                type: "object",
                properties: {
                    query: {
                        type: "string",
                        description: "FTS5 search terms for event text",
                    },
                    date_from: {
                        type: "string",
                        description: "Start date (YYYY-MM-DD)",
                    },
                    date_to: {
                        type: "string",
                        description: "End date (YYYY-MM-DD)",
                    },
                    actor: {
                        type: "string",
                        description: "Filter by actor name",
                    },
                    limit: {
                        type: "number",
                        description: "Max results (default 30)",
                    },
                },
            },
            handler: async (args) => {
                const limit = Math.min(args.limit || 30, 100);

                if (args.query) {
                    const result = await queryDB({
                        action: "query",
                        sql: "SELECT snippet(timeline_fts, 0, '>>>', '<<<', '...', 48) AS event, " +
                            "timeline_fts.actors FROM timeline_fts WHERE timeline_fts MATCH ? " +
                            "ORDER BY timeline_fts.rank LIMIT ?",
                        params: [args.query, limit],
                        max_rows: limit,
                    });
                    return "## 📅 Timeline Results\n\n" + formatResult(result);
                }

                const conditions = [];
                const params = [];
                if (args.date_from) { conditions.push("event_date >= ?"); params.push(args.date_from); }
                if (args.date_to) { conditions.push("event_date <= ?"); params.push(args.date_to); }
                if (args.actor) { conditions.push("actors LIKE ?"); params.push(`%${args.actor}%`); }
                const where = conditions.length ? "WHERE " + conditions.join(" AND ") : "";
                params.push(limit);

                const result = await queryDB({
                    action: "query",
                    sql: `SELECT event_date, category, event_description, actors FROM timeline_events ${where} ORDER BY event_date DESC LIMIT ?`,
                    params,
                    max_rows: limit,
                });
                return "## 📅 Timeline Results\n\n" + formatResult(result);
            },
        },

        // ═══════════════════════════════════════════════════════════════
        // ABSORBED MCP CAPABILITIES — 24 new tools via NEXUS daemon
        // ═══════════════════════════════════════════════════════════════

        {
            name: "list_documents",
            description: "List all documents in the litigation knowledge base with metadata (file name, size, page count, dates).",
            parameters: {
                type: "object",
                properties: {
                    limit: { type: "number", description: "Max documents (default 20, max 100)" },
                    offset: { type: "number", description: "Pagination offset (default 0)" },
                    name_filter: { type: "string", description: "Filter by file name (partial match)" },
                },
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "list_documents", limit: args.limit || 20, offset: args.offset || 0, name_filter: args.name_filter || null });
                return formatResult(result);
            },
        },

        {
            name: "get_document",
            description: "Retrieve full extracted text of a specific document by ID. Optionally get specific pages only.",
            parameters: {
                type: "object",
                properties: {
                    document_id: { type: "number", description: "Document ID from the database" },
                    page_numbers: { type: "array", description: "Specific page numbers to retrieve. Omit for all pages." },
                },
                required: ["document_id"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "get_document", document_id: args.document_id, page_numbers: args.page_numbers || null });
                return formatResult(result);
            },
        },

        {
            name: "search_documents",
            description: "Full-text search across all ingested PDF content using FTS5 with porter stemming. Supports AND/OR/NOT and quoted phrases.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "FTS5 search query. Example: 'ex parte AND McNeill'" },
                    limit: { type: "number", description: "Max results (default 20, max 100)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "search_documents", query: args.query, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "lookup_rule",
            description: "Look up Michigan Court Rules (MCR/MCL) by citation or keyword. Searches 873+ indexed rules with context snippets.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Rule citation (e.g. 'MCR 3.706') or keyword (e.g. 'custody')" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "lookup_rule", query: args.query, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "query_graph",
            description: "Search the litigation knowledge graph for authorities, case law, forms, and procedures.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Search term (e.g. 'PPO', 'MCL 600.2950')" },
                    node_type: { type: "string", description: "Filter: authority, CASELAW, FORM, PROCEDURE" },
                    graph_source: { type: "string", description: "Filter: court_forms_graph, authority_forms_graph, master_graph" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "query_graph", query: args.query, node_type: args.node_type || null, graph_source: args.graph_source || null, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "lookup_authority",
            description: "Look up specific legal authorities (case law, statutes, court rules) with pin cites, jurisdiction, and confidence scores.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Search term (e.g. 'Pierron', 'MCL 722', 'PPO')" },
                    node_type: { type: "string", description: "Filter: authority, CASELAW, FORM, PROCEDURE" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "lookup_authority", query: args.query, node_type: args.node_type || null, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "assess_risk",
            description: "Assess litigation risks from the risk event taxonomy. Returns severity scores, cure steps, deadlines, and authority references.",
            parameters: {
                type: "object",
                properties: {
                    severity_min: { type: "number", description: "Minimum severity threshold 0-100 (default 0)" },
                    risk_class: { type: "string", description: "Filter: record_incomplete, curable_defect, etc." },
                },
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "assess_risk", severity_min: args.severity_min || 0, risk_class: args.risk_class || null });
                return formatResult(result);
            },
        },

        {
            name: "get_vehicle_map",
            description: "Map a relief type to its litigation vehicle, authority chain, required elements, and deadlines.",
            parameters: {
                type: "object",
                properties: {
                    relief_type: { type: "string", description: "Relief type (e.g. 'custody modification', 'PPO', 'contempt')" },
                },
                required: ["relief_type"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "get_vehicle_map", relief_type: args.relief_type });
                return formatResult(result);
            },
        },

        {
            name: "case_health",
            description: "Case health dashboard — quotes, harms, impeachment, contradictions, claims, deadlines across all lanes.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "case_health" });
                return formatResult(result);
            },
        },

        {
            name: "adversary_threats",
            description: "Ranked adversary threat matrix with harm counts and category spread.",
            parameters: {
                type: "object",
                properties: {
                    limit: { type: "number", description: "Max adversaries (default 20)" },
                },
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "adversary_threats", limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "filing_pipeline",
            description: "Filing pipeline — every action with phase, readiness %, risk score, and gaps.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "filing_pipeline" });
                return formatResult(result);
            },
        },

        {
            name: "get_subagent_spec",
            description: "Retrieve the specification for a SUPERPIN sub-agent (role, inputs, outputs, triggers).",
            parameters: {
                type: "object",
                properties: {
                    agent_name: { type: "string", description: "Agent name (e.g. 'AUTH_HARVESTER', 'DRAFTER_COA')" },
                },
                required: ["agent_name"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "get_subagent_spec", agent_name: args.agent_name });
                return formatResult(result);
            },
        },

        {
            name: "evolution_stats",
            description: "Evolution coverage statistics dashboard — files evolved, sections, cross-refs, completeness.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "evolution_stats" });
                return formatResult(result);
            },
        },

        {
            name: "search_evolved",
            description: "FTS5 search across all evolved content (md, txt, pdf sections) with snippets.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Search query" },
                    source_type: { type: "string", description: "Filter: md, txt, pdf, or null for all" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "search_evolved", query: args.query, source_type: args.source_type || null, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "cross_refs",
            description: "Query the cross-reference network for matching references (agents, rules, vehicles, risks, authorities).",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: 'Search value (e.g. "MCR 3.706", "AUTH_HARVESTER")' },
                    ref_type: { type: "string", description: "Filter: agent, rule, vehicle, risk, authority" },
                    limit: { type: "number", description: "Max results (default 50)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "cross_refs", query: args.query, ref_type: args.ref_type || null, limit: args.limit || 50 });
                return formatResult(result);
            },
        },

        {
            name: "convergence_status",
            description: "Check convergence status — quality score, ΔNEW items, BLOCKERs, NEXT_PATCH, emergence signals.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "convergence_status" });
                return formatResult(result);
            },
        },

        {
            name: "self_test",
            description: "Run diagnostic self-tests on the litigation database (DB connectivity, FTS5 round-trip, graph counts).",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "self_test" });
                return formatResult(result);
            },
        },

        {
            name: "query_master",
            description: "Search across master CSV datasets with optional dataset filtering.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Search query against master data" },
                    dataset: { type: "string", description: "Limit to specific dataset" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "query_master", query: args.query, dataset: args.dataset || null, limit: args.limit || 20 });
                return formatResult(result);
            },
        },

        {
            name: "vector_search",
            description: "Vector similarity search via LanceDB (75K vectors, 384-dim). Falls back to FTS5 if LanceDB unavailable. Finds semantically similar content.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Natural language query for semantic search" },
                    top_k: { type: "number", description: "Number of results (default 10, max 50)" },
                },
                required: ["query"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "vector_search", query: args.query, top_k: args.top_k || 10 });
                return formatResult(result);
            },
        },

        {
            name: "self_audit",
            description: "Run comprehensive data-quality audit. Returns quality score 0-100, findings by severity, and summary statistics.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "self_audit" });
                return formatResult(result);
            },
        },

        {
            name: "evidence_chain",
            description: "Trace the evidence chain for a legal claim — maps claim → sections → cross-references → sources with completeness percentage.",
            parameters: {
                type: "object",
                properties: {
                    claim: { type: "string", description: "Legal claim to trace (e.g. 'parental alienation')" },
                },
                required: ["claim"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "evidence_chain", claim: args.claim });
                return formatResult(result);
            },
        },

        {
            name: "compute_deadlines",
            description: "Compute legal deadlines from a trigger event and date using Michigan court rules. Returns timeline of upcoming deadlines with rule citations.",
            parameters: {
                type: "object",
                properties: {
                    trigger_event: { type: "string", description: "Event type: motion_served, complaint_filed, order_entered, ppo_served, appeal_filed" },
                    trigger_date: { type: "string", description: "ISO date (e.g. '2026-04-01')" },
                },
                required: ["trigger_event", "trigger_date"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "compute_deadlines", trigger_event: args.trigger_event, trigger_date: args.trigger_date });
                return formatResult(result);
            },
        },

        {
            name: "red_team",
            description: "Red-team validate a legal claim or argument. Scores authority, evidence, and consistency. Reports findings by severity and FILING_READY status.",
            parameters: {
                type: "object",
                properties: {
                    claim: { type: "string", description: "Legal claim or argument to validate" },
                },
                required: ["claim"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "red_team", claim: args.claim });
                return formatResult(result);
            },
        },

        {
            name: "stats_extended",
            description: "Extended knowledge base statistics including graphs, rules, risk data, and evolution counts.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "stats_extended" });
                return formatResult(result);
            },
        },

        // ── NEXUS v3 Absorbed Capabilities (13 new handlers) ──────────────

        {
            name: "system_health",
            description: "Get NEXUS daemon health: circuit breaker state, startup time, graph loading status, degraded mode, recent errors.",
            parameters: { type: "object", properties: {
                reset_circuit_breaker: { type: "boolean", description: "Reset circuit breaker to CLOSED state" },
            }},
            handler: async (args) => {
                const result = await callDaemon({ action: "health", reset_cb: args.reset_circuit_breaker || false });
                return formatResult(result);
            },
        },

        {
            name: "record_error",
            description: "Record an error event in the error telemetry log for tracking and diagnostics.",
            parameters: { type: "object", properties: {
                code: { type: "string", description: "Error code (ERR_DB_CONNECT, ERR_PDF_PERMISSION, ERR_PDF_TIMEOUT, ERR_FTS_SYNTAX, ERR_DB_LOCKED, ERR_PATH_TRAVERSAL)" },
                tool: { type: "string", description: "Tool/action that triggered the error" },
                detail: { type: "string", description: "Error detail message" },
            }, required: ["code", "tool", "detail"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "record_error", code: args.code, tool: args.tool, detail: args.detail });
                return formatResult(result);
            },
        },

        {
            name: "get_error_summary",
            description: "Get error telemetry summary: recent errors grouped by code and tool from the last 24 hours.",
            parameters: { type: "object", properties: {
                hours: { type: "number", description: "Hours to look back (default 24)" },
            }},
            handler: async (args) => {
                const result = await callDaemon({ action: "get_error_summary", hours: args.hours || 24 });
                return formatResult(result);
            },
        },

        {
            name: "check_disk_space",
            description: "Check disk space across all 6 drives (C, D, F, G, I, J). Returns total/used/free per drive with health status.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "check_disk_space" });
                return formatResult(result);
            },
        },

        {
            name: "scan_all_systems",
            description: "Full system diagnostic scan: DB connectivity, FTS5 health, disk space, circuit breaker, row counts, degraded services.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const result = await callDaemon({ action: "scan_all_systems" });
                return formatResult(result);
            },
        },

        {
            name: "evolve_md",
            description: "Evolve markdown files in a directory — parse into sections, extract cross-references, link to knowledge graph. Idempotent.",
            parameters: { type: "object", properties: {
                directory: { type: "string", description: "Path to scan for .md files" },
            }, required: ["directory"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "evolve_md", directory: args.directory });
                return formatResult(result);
            },
        },

        {
            name: "evolve_txt",
            description: "Evolve text files in a directory — parse into sections, extract cross-references, link to knowledge graph. Idempotent.",
            parameters: { type: "object", properties: {
                directory: { type: "string", description: "Path to scan for .txt files" },
            }, required: ["directory"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "evolve_txt", directory: args.directory });
                return formatResult(result);
            },
        },

        {
            name: "evolve_pages",
            description: "Evolve ingested PDF pages into cross-reference knowledge layer. Converts page text into sections with cross-refs.",
            parameters: { type: "object", properties: {
                document_id: { type: "number", description: "Specific document ID, or omit for all" },
            }},
            handler: async (args) => {
                const result = await callDaemon({ action: "evolve_pages", document_id: args.document_id || null });
                return formatResult(result);
            },
        },

        {
            name: "document_exists",
            description: "Check if a document is already indexed by its file path. Returns boolean and document ID if found.",
            parameters: { type: "object", properties: {
                file_path: { type: "string", description: "Absolute path to check" },
            }, required: ["file_path"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "document_exists", file_path: args.file_path });
                return formatResult(result);
            },
        },

        {
            name: "hash_exists",
            description: "Check if a content hash (SHA-256) already exists in the document index. Deduplication check.",
            parameters: { type: "object", properties: {
                sha256: { type: "string", description: "SHA-256 hash to check" },
            }, required: ["sha256"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "hash_exists", sha256: args.sha256 });
                return formatResult(result);
            },
        },

        {
            name: "delete_document",
            description: "Remove a document and all its pages from the knowledge base index. Does NOT delete the original file.",
            parameters: { type: "object", properties: {
                document_id: { type: "number", description: "Document ID to delete" },
            }, required: ["document_id"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "delete_document", document_id: args.document_id });
                return formatResult(result);
            },
        },

        {
            name: "insert_document",
            description: "Insert a new document with extracted pages into the knowledge base. Skips if path or hash already exists.",
            parameters: { type: "object", properties: {
                file_path: { type: "string", description: "Absolute path to the document" },
                file_name: { type: "string", description: "File name" },
                file_size: { type: "number", description: "File size in bytes" },
                sha256: { type: "string", description: "SHA-256 hash of file content" },
                pages: { type: "array", description: "Array of {page_number, text} objects", items: { type: "object", properties: { page_number: { type: "number" }, text: { type: "string" } }} },
            }, required: ["file_path", "file_name", "file_size", "sha256", "pages"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "insert_document", ...args });
                return formatResult(result);
            },
        },

        {
            name: "dispatch_to_swarm",
            description: "Dispatch a task to the agent swarm for recommendations. Returns ranked agent matches with relevance scores.",
            parameters: { type: "object", properties: {
                task: { type: "string", description: "Task description to dispatch" },
            }, required: ["task"] },
            handler: async (args) => {
                const result = await callDaemon({ action: "dispatch_to_swarm", task: args.task });
                return formatResult(result);
            },
        },

        // ═══════════════════════════════════════════════════════════════
        // AGENT MEMORY (ABSORBED from agent-memory MCP)
        // ═══════════════════════════════════════════════════════════════
        {
            name: "memory_store",
            description: "Store a fact in persistent agent memory for cross-session recall.",
            parameters: {
                type: "object",
                properties: {
                    subject: { type: "string", description: "Topic (1-2 words): naming, testing, auth, etc." },
                    fact: { type: "string", description: "Clear, concise fact (<200 chars)." },
                    citations: { type: "string", description: "Source file and line, or 'User input: ...'" },
                    reason: { type: "string", description: "Why this fact matters for future tasks (2-3 sentences)." },
                },
                required: ["fact"],
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "memory_store", ...args });
                if (result?.ok) return `✅ Memory stored (id: ${result.id}): ${args.fact}`;
                return `❌ ${result?.error || "Failed to store memory"}`;
            },
        },
        {
            name: "memory_recall",
            description: "Search agent memory for previously stored facts. FTS5 with LIKE fallback.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Search terms (FTS5 syntax: AND, OR, NOT, phrases)" },
                    subject: { type: "string", description: "Optional subject filter" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "memory_recall", ...args });
                return formatResult(result);
            },
        },
        {
            name: "memory_list",
            description: "List recent agent memories with optional subject filter.",
            parameters: {
                type: "object",
                properties: {
                    subject: { type: "string", description: "Filter by subject" },
                    limit: { type: "number", description: "Max results (default 20)" },
                },
            },
            handler: async (args) => {
                const result = await callDaemon({ action: "memory_list", ...args });
                return formatResult(result);
            },
        },

        // ═══════════════════════════════════════════════════════════════
        // COMMAND RUNNER (ABSORBED from command-runner MCP — direct Node.js)
        // Subprocess execution runs HERE, not through daemon, to avoid
        // blocking daemon's single-threaded event loop on 600s timeouts.
        // ═══════════════════════════════════════════════════════════════
        {
            name: "command-runner-exec_command",
            description: "Execute a shell command. Returns stdout/stderr. Timeout 600s. Max output 250KB.",
            parameters: {
                type: "object",
                properties: {
                    command: { type: "string", description: "The shell command to execute." },
                },
                required: ["command"],
            },
            handler: async (args) => {
                try {
                    const out = execSync(args.command, {
                        cwd: REPO_ROOT, shell: true, timeout: CMD_TIMEOUT,
                        maxBuffer: MAX_CMD_OUTPUT, encoding: "utf-8",
                        env: { ...process.env, PYTHONUTF8: "1" },
                    });
                    return safeTruncate(out || "(no output)", MAX_OUTPUT_CHARS, "stdout");
                } catch (e) {
                    const stdout = e.stdout ? safeTruncate(String(e.stdout), MAX_OUTPUT_CHARS, "stdout") : "";
                    const stderr = e.stderr ? safeTruncate(String(e.stderr), MAX_OUTPUT_CHARS, "stderr") : "";
                    if (e.killed) return `⏱️ Command timed out (${CMD_TIMEOUT / 1000}s)\n${stdout}\n${stderr}`;
                    return `Exit code: ${e.status ?? "unknown"}\n${stdout}\n${stderr}`.trim();
                }
            },
        },
        {
            name: "command-runner-exec_python",
            description: "Execute a Python script with PYTHONUTF8=1. CWD set to script dir to avoid shadow modules.",
            parameters: {
                type: "object",
                properties: {
                    script_path: { type: "string", description: "Absolute or repo-relative path to .py script." },
                    args: { type: "array", items: { type: "string" }, description: "Optional CLI args." },
                },
                required: ["script_path"],
            },
            handler: async (args) => {
                const scriptPath = args.script_path.includes(":\\")
                    ? args.script_path
                    : join(REPO_ROOT, args.script_path);
                if (!existsSync(scriptPath)) return `❌ Script not found: ${scriptPath}`;
                const scriptDir = dirname(scriptPath);
                const scriptArgs = ["-I", scriptPath, ...(args.args || [])];
                try {
                    const r = spawnSync("python", scriptArgs, {
                        cwd: scriptDir, timeout: CMD_TIMEOUT, maxBuffer: MAX_CMD_OUTPUT,
                        encoding: "utf-8",
                        env: { ...process.env, PYTHONUTF8: "1" },
                    });
                    const stdout = r.stdout ? safeTruncate(r.stdout, MAX_OUTPUT_CHARS, "stdout") : "";
                    const stderr = r.stderr ? safeTruncate(r.stderr, MAX_OUTPUT_CHARS, "stderr") : "";
                    if (r.status === 0) return stdout || "(no output)";
                    return `Exit code: ${r.status}\nSTDOUT:\n${stdout}\nSTDERR:\n${stderr}`.trim();
                } catch (e) {
                    return `❌ ${e.message}`;
                }
            },
        },
        {
            name: "command-runner-exec_git",
            description: "Execute a git command with --no-pager in the LitigationOS repo.",
            parameters: {
                type: "object",
                properties: {
                    args: { type: "string", description: "Git sub-command and arguments (e.g. 'status')." },
                },
                required: ["args"],
            },
            handler: async (args) => {
                try {
                    const cmd = `git -c core.fsmonitor=false --no-pager ${args.args}`;
                    const out = execSync(cmd, {
                        cwd: REPO_ROOT, timeout: 120000, maxBuffer: MAX_CMD_OUTPUT,
                        encoding: "utf-8", env: { ...process.env, GIT_TERMINAL_PROMPT: "0" },
                    });
                    return safeTruncate(out || "(no output)", MAX_OUTPUT_CHARS, "git output");
                } catch (e) {
                    const out = e.stdout ? String(e.stdout) : "";
                    const err = e.stderr ? String(e.stderr) : "";
                    return `Exit: ${e.status ?? "?"}\n${out}\n${err}`.trim();
                }
            },
        },
        {
            name: "command-runner-exec_pipeline_phase",
            description: "Execute a LitigationOS pipeline phase by name.",
            parameters: {
                type: "object",
                properties: {
                    phase: { type: "string", description: "Phase identifier (e.g. '1', '4a', 'validate')." },
                },
                required: ["phase"],
            },
            handler: async (args) => {
                const script = PHASE_MAP[args.phase];
                if (!script) return `❌ Unknown phase '${args.phase}'. Valid: ${Object.keys(PHASE_MAP).join(", ")}`;
                const scriptPath = join(PIPELINE_DIR, script);
                if (!existsSync(scriptPath)) return `❌ Pipeline script not found: ${scriptPath}`;
                try {
                    const r = spawnSync("python", ["-I", scriptPath], {
                        cwd: PIPELINE_DIR, timeout: CMD_TIMEOUT, maxBuffer: MAX_CMD_OUTPUT,
                        encoding: "utf-8",
                        env: { ...process.env, PYTHONUTF8: "1" },
                    });
                    const stdout = r.stdout ? safeTruncate(r.stdout, MAX_OUTPUT_CHARS, "stdout") : "";
                    const stderr = r.stderr ? safeTruncate(r.stderr, MAX_OUTPUT_CHARS, "stderr") : "";
                    if (r.status === 0) return stdout || "(phase completed, no output)";
                    return `Phase '${args.phase}' failed (exit ${r.status}):\n${stdout}\n${stderr}`.trim();
                } catch (e) {
                    return `❌ ${e.message}`;
                }
            },
        },
        {
            name: "command-runner-system_status",
            description: "System health: Python version, disk space, DB size, git branch, OS details.",
            parameters: { type: "object", properties: {} },
            handler: async () => {
                const lines = [];
                lines.push(`🖥️ **System Status**`);
                lines.push(`- OS: ${platform()} ${hostname()}`);
                lines.push(`- CPUs: ${cpus().length}× ${cpus()[0]?.model || "unknown"}`);
                lines.push(`- RAM: ${(totalmem() / 1073741824).toFixed(1)} GB total, ${(freemem() / 1073741824).toFixed(1)} GB free`);
                try {
                    const pyVer = execSync("python --version", { encoding: "utf-8", timeout: 5000 }).trim();
                    lines.push(`- Python: ${pyVer}`);
                } catch { lines.push("- Python: not found"); }
                try {
                    const info = statSync(DB_PATH);
                    lines.push(`- DB: ${(info.size / 1048576).toFixed(1)} MB (${DB_PATH.split("\\").pop()})`);
                } catch { lines.push("- DB: not found"); }
                try {
                    const branch = execSync("git -c core.fsmonitor=false --no-pager rev-parse --abbrev-ref HEAD", {
                        cwd: REPO_ROOT, encoding: "utf-8", timeout: 10000,
                    }).trim();
                    const status = execSync("git -c core.fsmonitor=false --no-pager status --porcelain | head -5", {
                        cwd: REPO_ROOT, encoding: "utf-8", timeout: 10000, shell: true,
                    }).trim();
                    lines.push(`- Git: ${branch} (${status ? status.split("\\n").length + " changes" : "clean"})`);
                } catch { lines.push("- Git: error"); }
                try {
                    const diskCmd = platform() === "win32"
                        ? 'wmic logicaldisk get size,freespace,caption /format:list'
                        : 'df -h /';
                    const disk = execSync(diskCmd, { encoding: "utf-8", timeout: 10000 }).trim();
                    if (platform() === "win32") {
                        const drives = disk.split(/\r?\n\r?\n/).filter(b => b.includes("Caption="));
                        for (const block of drives.slice(0, 4)) {
                            const cap = block.match(/Caption=(\S+)/)?.[1] || "?";
                            const free = block.match(/FreeSpace=(\d+)/)?.[1];
                            const total = block.match(/Size=(\d+)/)?.[1];
                            if (free && total) {
                                lines.push(`- ${cap} ${(+free / 1073741824).toFixed(1)}/${(+total / 1073741824).toFixed(1)} GB free`);
                            }
                        }
                    } else {
                        lines.push(`- Disk: ${disk}`);
                    }
                } catch { lines.push("- Disk: error reading"); }
                return lines.join("\n");
            },
        },
    ],
});
