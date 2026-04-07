---
name: SINGULARITY-agent-nexus
version: "2.0.0"
description: "Transcendent agent architecture and fleet orchestration for LitigationOS. Use when: designing agents, multi-agent systems, fleet management, tool integration, agent evaluation, NEXUS daemon operations, extension development, parallel dispatch, agent lifecycle, error recovery, agent memory, planning strategies, CrewAI patterns, agent communication, genetic memory, MCP replacement architecture."
---

# SINGULARITY-agent-nexus — Transcendent Agent Fleet Orchestration

> **Version:** 2.0.0 | **Tier:** CORE | **Domain:** Agent Architecture & Fleet Orchestration
> **Absorbs:** agent-architect + agent-evaluation + mcp-tools
> **Activation:** "agent", "fleet", "MCP", "orchestration", "parallel", "multi-agent", "delta999", "extension", "tool", "daemon"

---

## Layer 1: Agent Fleet Architecture (28 Active Agents)

### Agent Type Taxonomy

| Type | Model | Use For | Isolation | Cost |
|------|-------|---------|-----------|------|
| **explore** | Haiku | Fast codebase research, DB queries, file analysis | ISOLATED pipes | Low |
| **task** | Haiku | Commands with success/fail (builds, tests, installs) | ISOLATED pipes | Low |
| **general-purpose** | Sonnet | Complex multi-step tasks, drafting, analysis | ISOLATED pipes | Medium |
| **rubber-duck** | Sonnet | Plan validation, bug catching, design critique | ISOLATED pipes | Medium |
| **code-review** | Sonnet | Staged/unstaged change review, security audit | ISOLATED pipes | Medium |
| **custom agents** | Varies | Specialized domain tasks (28 custom agents) | ISOLATED pipes | Varies |

### Agent Selection Matrix

| Task | Best Agent | Why |
|------|-----------|-----|
| Quick DB query or file lookup | Do it yourself (grep/glob/view) | Faster than spawning agent |
| Research across 5+ files/modules | explore (parallel) | Parallelism wins |
| Build/test/lint command | task | Clean output on success |
| Draft a motion or brief | general-purpose | Full reasoning needed |
| Validate plan before implementing | rubber-duck | Catches blind spots |
| Review git diff for bugs | code-review | Specialized for diffs |
| Evidence hunting across drives | kraken-hunter (custom) | Domain-specialized |
| Filing package assembly | filing-forge-master (custom) | Filing workflow |
| Judicial misconduct analysis | judicial-accountability-engine | JTC domain |
| Adversary profiling | adversary-war-room (custom) | Adversary intelligence |

### Parallel Dispatch Rules (Rule 26 — HARD LIMIT)

```
MAXIMUM: 2 concurrent agents (launching 3+ triggers 429 rate limits)

Pre-spawn checklist:
1. list_agents → count RUNNING agents (exclude completed/idle)
2. Running agents must be < 3
3. Wait 1 second between agent spawns
4. Can spawn 2 agents in ONE tool call (same response block)
5. Can spawn 1 agent + 1 shell in same call (different pipe pools)
```

### Shell Budget Management

```
Agents use ISOLATED pipes (separate from main session).
Shells use SHARED pipes (direct EAGAIN risk).

Budget:
  - Max 2 concurrent async shells (SHARED pipe budget)
  - Max 3 concurrent agents (ISOLATED pipe budget)
  - Agents do NOT count against shell budget
  - Shell pre-spawn: list_powershell → count < 2
  - Agent pre-spawn: list_agents → running count < 3
```

### Agent Lifecycle

```
SPAWN → RUNNING → COMPLETED/FAILED
  │                    │
  │                    ├─ read_agent → get results
  │                    └─ stop if idle/stuck
  │
  └─ write_agent (if idle) → RUNNING again (multi-turn)
```

---

## Layer 2: NEXUS Daemon (MCP Replacement)

### Architecture

```
Copilot CLI Session
  └── extension.mjs (Node.js — Copilot CLI Extension)
       │
       ├── 72 tool definitions (name, description, parameters, handler)
       │
       └── nexus_daemon.py (PERSISTENT Python subprocess)
            ├── SQLite WAL connection (warm, always open)
            ├── DuckDB analytical engine (ATTACH'd read-only)
            ├── LanceDB vector store (75K vectors)
            ├── 67 action handlers
            └── JSON-RPC over stdin/stdout (line-delimited)
```

### Performance vs Legacy MCP

| Metric | Legacy MCP (spawn-per-call) | NEXUS Daemon (persistent) |
|--------|---------------------------|--------------------------|
| Process spawn | ~500 ms per call | 0 ms (already alive) |
| DB connection | ~50 ms per call | 0 ms (warm connection) |
| PRAGMA setup | ~10 ms per call | 0 ms (set once at startup) |
| Analytics | SQLite only | DuckDB (10-100× faster) |
| Semantic search | None | LanceDB 75K vectors |
| Write support | ❌ Read-only | ✅ Full CRUD |
| **Per-call latency** | **~600 ms** | **~2-5 ms** |

### Tool Routing Hierarchy

```
Priority 1: NEXUS extension tools (warm daemon, 2-5ms)
    query_litigation_db, search_evidence, nexus_fuse, vector_search, etc.

Priority 2: SINGULARITY extension tools (specialized handlers)
    lottery_harvest, krack_a_lack, adversary_scan, intel_dashboard, etc.

Priority 3: MCP tools (DEPRECATED — spawn-per-call, 600ms)
    litigation_context-* tools — use ONLY as fallback if NEXUS is down
```

### Action Handler Development

```python
# Adding a new action to nexus_daemon.py

def handle_new_action(req):
    """Handler for the 'new_action' action."""
    pool = ConnectionPool()
    param = req.get("param", "default")

    try:
        rows = pool.sqlite.execute(
            "SELECT * FROM some_table WHERE col = ? LIMIT ?",
            (param, req.get("limit", 25))
        ).fetchall()

        columns = [d[0] for d in pool.sqlite.description]
        return {"ok": True, "rows": [list(r) for r in rows],
                "columns": columns, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Register in HANDLERS dict
HANDLERS = {
    # ... existing handlers ...
    "new_action": handle_new_action,
}
```

### Extension Tool Definition (extension.mjs)

```javascript
// Adding corresponding tool in extension.mjs
{
    name: "my_new_tool",
    description: "Does something useful with litigation data.",
    parameters: {
        type: "object",
        properties: {
            param: { type: "string", description: "The parameter" },
            limit: { type: "number", description: "Max results (default 25)" }
        },
        required: ["param"]
    },
    handler: async (args) => {
        const result = await callDaemon({
            action: "new_action",
            param: args.param,
            limit: args.limit || 25
        });
        return formatResult(result);
    }
}
```

### Error Recovery & Auto-Restart

```javascript
// extension.mjs daemon lifecycle management
function startDaemon() {
    daemon = spawn("python", [DAEMON_PATH], { stdio: ["pipe", "pipe", "pipe"] });

    daemon.on("exit", (code) => {
        if (restartCount < MAX_RESTARTS) {
            restartCount++;
            const delay = Math.min(1000 * Math.pow(2, restartCount), 30000);
            setTimeout(startDaemon, delay);  // exponential backoff
        }
    });

    // Wait for ready signal
    // {"ok": true, "status": "ready", "pid": 12345}
}

process.once("exit", () => { if (daemon) daemon.kill(); });
```

---

## Layer 3: Multi-Agent Orchestration Patterns

### Pattern 1: Parallel Exploration (2 Agents × N Questions)

```
Use when: Multiple independent research questions

Agent A (explore): "Search evidence_quotes for parental alienation"
Agent B (explore): "Search judicial_violations for ex parte orders"
                ↓ (both run simultaneously)
Collect results → synthesize answer
```

```python
# Launch 2 explore agents in parallel (one tool call)
task(agent_type="explore", name="evidence-search",
     prompt="Search evidence_quotes FTS5 for 'parental alienation'...")
task(agent_type="explore", name="judicial-search",
     prompt="Search judicial_violations for ex parte patterns...")
# Read both results, synthesize
```

### Pattern 2: Pipeline (Sequential Handoff)

```
Use when: Each step depends on previous output

Agent A (explore): Research facts → output facts list
    ↓
Agent B (general-purpose): Draft motion using facts
    ↓
Agent C (rubber-duck): Critique the draft
    ↓
Revise based on critique → final output
```

### Pattern 3: Specialist Routing

```
Use when: Task requires domain expertise

Analyze task → select specialist agent:
  Filing task     → filing-forge-master
  Evidence task   → evidence-warfare-commander
  Judicial task   → judicial-accountability-engine
  Strategy task   → case-strategy-architect
  Appellate task  → appellate-record-builder
```

### Pattern 4: Self-Improving (Rubber-Duck Loop)

```
Use when: Non-trivial implementation needing validation

Step 1: Plan your approach
Step 2: rubber-duck agent validates plan → catches blind spots
Step 3: Implement with fixes from critique
Step 4: rubber-duck agent validates implementation
Step 5: Final refinements
```

### Pattern 5: Multi-Turn Refinement

Start agent in `background` mode → `read_agent` → `write_agent` (refinement) → `read_agent`
(since_turn) → repeat until quality target met. Never launch a new agent for refinement.

### Pattern 6: Consensus Voting

Launch 2 explore agents with different approaches → compare results → choose best with justification.

---

## Layer 4: Agent Evaluation & Quality

### Agent Output Quality Scoring

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Completeness | 30% | All requested information provided |
| Accuracy | 25% | Facts verified against DB, no hallucinations |
| Actionability | 20% | Output directly usable (not advisory) |
| Efficiency | 15% | Minimal tool calls, no redundant work |
| Format | 10% | Structured, parseable, consistent |

### Test-Driven Agent Development

```python
# Agent behavioral tests
def test_evidence_agent_finds_relevant():
    """Evidence search agent returns relevant results."""
    result = run_agent("explore", "Search evidence_quotes for 'parental alienation'")
    assert result["status"] == "completed"
    assert "parental alienation" in result["output"].lower()
    assert "MCL 722.23" in result["output"]

def test_filing_agent_includes_required_components():
    """Filing agent produces complete packet family."""
    result = run_agent("filing-forge-master", "Assemble motion packet for Lane A")
    required = ["motion", "affidavit", "certificate of service", "proposed order"]
    for component in required:
        assert component.lower() in result["output"].lower()
```

### LLM-as-Judge Evaluation

Use `rubber-duck` agent as quality judge: provide original task + agent output, ask it to score
on completeness/accuracy/actionability and grade as PASS/NEEDS_WORK/FAIL.

### Cost Profile

| Agent Type | Model | Avg Cost | Use For |
|------------|-------|----------|---------|
| explore | Haiku | ~$0.001 | Quick research, DB queries |
| task | Haiku | ~$0.0005 | Build/test commands |
| general-purpose | Sonnet | ~$0.03 | Complex analysis, drafting |
| rubber-duck | Sonnet | ~$0.02 | Plan/impl validation |

---

## Layer 5: Extension Development

### Extension Anatomy (extension.mjs)

```javascript
// .github/extensions/singularity/extension.mjs

// 1. Daemon lifecycle
let daemon = null;
function startDaemon() { /* spawn nexus_daemon.py */ }

// 2. Communication helpers
async function callDaemon(payload) { /* JSON-RPC over stdin/stdout */ }
async function queryDB(request) { /* wrapper with error formatting */ }

// 3. Result formatters
function formatResult(result) { /* convert daemon response to user string */ }
function formatTable(rows, columns) { /* ASCII table output */ }

// 4. Tool definitions (72 tools)
export default [
    {
        name: "query_litigation_db",
        description: "Read-only SQL against litigation_context.db...",
        parameters: { /* JSON Schema */ },
        handler: async (args) => { /* route to daemon */ }
    },
    // ... 71 more tools
];
```

### Tool Definition Checklist

Every extension tool must have: (1) clear `description` with examples, (2) typed `parameters`
with JSON Schema, (3) `required` array for mandatory params, (4) `handler` that calls
`callDaemon()` and wraps result with `formatResult()`, (5) error path returning `⚠️ Error: ...`.

---

## Layer 6: Agent Memory & Persistence

### Memory Tools

| Tool | Purpose | Persistence |
|------|---------|-------------|
| `store_memory` | Save facts for future sessions | Permanent (memory DB) |
| `memory_recall` | Search stored memories (FTS5) | Read from memory DB |
| `memory_list` | List recent memories by subject | Read from memory DB |
| `sql` (session DB) | Track todos, state, batch items | Per-session |
| `sql` (session_store) | Query ALL past sessions | Read-only, cross-session |

### store_memory Best Practices

```python
# GOOD — actionable, specific, with citations
store_memory(
    subject="database",
    fact="exFAT drives (J:\\) require PRAGMA journal_mode=DELETE, not WAL",
    citations="infrastructure.instructions.md, line 45",
    reason="WAL mode fails silently on exFAT. Future scripts touching J:\\ "
           "databases will corrupt data without this knowledge."
)

# BAD — vague, no citations, no future utility
store_memory(
    subject="general",
    fact="databases are important",
    citations="",
    reason="good to know"
)
```

### Plan.md as Post-Compaction Lifeline

```markdown
# Current Plan (updated after each milestone)

## Phase: [current phase name]
## Status: [in_progress / blocked / complete]

## Completed
- [x] Task 1: description + key finding
- [x] Task 2: description + rows inserted

## In Progress
- [ ] Task 3: description + next step

## Key Discoveries (survive compaction)
- Finding A: [detail] — persisted to evidence_quotes row ID 12345
- Finding B: [detail] — persisted to timeline_events

## Blockers
- Blocker 1: [description] — mitigation: [plan]
```

### SQL Todos for Execution Tracking

```sql
-- Descriptive IDs, full context in description
INSERT INTO todos (id, title, description, status) VALUES
  ('search-alienation-evidence', 'Search alienation evidence',
   'Query evidence_quotes FTS5 for parental alienation, MCL 722.23(j)', 'pending');

-- Find ready todos (no pending dependencies)
SELECT t.* FROM todos t WHERE t.status = 'pending'
AND NOT EXISTS (SELECT 1 FROM todo_deps td JOIN todos dep ON td.depends_on = dep.id
    WHERE td.todo_id = t.id AND dep.status != 'done');
```

### Checkpoint Strategy

After every 3 agent completions OR major milestone: (1) update SQL todos, (2) update plan.md,
(3) write critical discoveries to DB immediately. Never batch for "later" — compaction strikes.

---

## Anti-Patterns (VIOLATIONS = IMMEDIATE FAILURE)

| # | Anti-Pattern | Correct Pattern |
|---|-------------|-----------------|
| 1 | Launch 3+ parallel agents | Max 2 concurrent (429 rate limits) |
| 2 | Use MCP when NEXUS extension tool exists | NEXUS first (100× faster) |
| 3 | Leave completed shells/agents alive | `stop_powershell` / cleanup immediately |
| 4 | Skip rubber-duck for non-trivial tasks | Always validate plans before implementing |
| 5 | Hardcode agent IDs | Use descriptive names ("evidence-search", not "42") |
| 6 | Spawn explore agent for simple lookup | Do it yourself with grep/glob/view |
| 7 | Launch agent without full context | Provide complete context (agents are stateless) |
| 8 | Duplicate agent's work after reading results | Trust agent output, don't re-search |
| 9 | Sequential operations that can be parallelized | 2 explore agents in one tool call |
| 10 | Forget to read agent results | Always `read_agent` after completion |
| 11 | Use generic shell IDs | Descriptive: "build-engine", "test-fts5" |
| 12 | Poll agents with long waits | Short delays (5-10s), rely on notifications |
| 13 | Create new agent for refinement | `write_agent` to existing idle agent |
| 14 | Missing error handling in extension tool | formatResult must handle `ok: false` |
| 15 | Store transient facts in memory | Only store facts meeting criteria (actionable, durable) |

## Performance Budgets

| Operation | Target | Degraded | Unacceptable |
|-----------|--------|----------|--------------|
| Agent spawn (explore) | < 2 s | < 5 s | > 10 s |
| Agent spawn (general-purpose) | < 3 s | < 8 s | > 15 s |
| Agent round-trip (explore, simple query) | < 15 s | < 30 s | > 60 s |
| Agent round-trip (general-purpose, complex) | < 60 s | < 120 s | > 300 s |
| NEXUS tool call (warm daemon) | < 5 ms | < 50 ms | > 200 ms |
| MCP tool call (spawn-per-call) | < 600 ms | < 2 s | > 5 s |
| Extension reload | < 3 s | < 10 s | > 30 s |
| Memory store/recall | < 100 ms | < 500 ms | > 2 s |
| Plan.md read/write | < 50 ms | < 200 ms | > 1 s |

## Decision Matrix: Agent vs Direct Action

| Scenario | Do It Yourself | Use Agent |
|----------|---------------|-----------|
| Read 1-3 known files | ✅ grep/glob/view | ❌ Overkill |
| Search for a symbol | ✅ grep | ❌ Overkill |
| Research 5+ modules in parallel | ❌ Sequential bottleneck | ✅ 2 explore agents |
| Run build/test command | ❌ Pollutes main context | ✅ task agent |
| Draft complex document | ❌ Context-heavy | ✅ general-purpose |
| Validate plan | ❌ Self-bias | ✅ rubber-duck |
| Review code changes | ❌ Miss blind spots | ✅ code-review |
| Simple DB query | ✅ query_litigation_db | ❌ Overkill |
| Multi-step filing workflow | ❌ Too many steps | ✅ filing-forge-master |

## Custom Agent Fleet (28 Active)

Key specialists: `filing-forge-master` (packets/QA), `evidence-warfare-commander` (triage/gaps),
`judicial-accountability-engine` (JTC/misconduct), `case-strategy-architect` (war planning),
`timeline-forensics` (chronology), `appellate-record-builder` (appendices), `damages-calculator`
(constitutional/economic), `kraken-hunter` (multi-round evidence lottery), `deep-research`
(web + DB research fusion). Full fleet: see `.agents/agents/` and activation matrix in instructions.

---

*END OF SINGULARITY-agent-nexus v2.0.0 — 28 Agents · 67 NEXUS Actions · 72 Extension Tools · Fleet Orchestration*
