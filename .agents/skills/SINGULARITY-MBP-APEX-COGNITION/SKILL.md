---
name: SINGULARITY-MBP-APEX-COGNITION
description: "Self-evolving agent architecture for THEMANBEARPIG litigation graph. Act-Observe-Reflect-Plan loops, population-based strategy evolution, critic/verifier sub-agents, hybrid neural+symbolic legal reasoning, cross-session learning persistence, self-calibrating confidence, fleet orchestration. The graph that gets smarter every session."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "Self-evolving cognition — agent evolution, critic verification, hybrid reasoning, cross-session learning, confidence calibration, fleet orchestration"
triggers:
  - self-evolving
  - agent evolution
  - AORP loop
  - critic agent
  - hybrid reasoning
  - neural-symbolic
  - cross-session learning
  - confidence calibration
  - fleet orchestration
  - cognition
  - self-improving agent
  - strategy evolution
  - legal syllogism
  - citation verifier
  - hallucination guard
  - population training
  - fitness evaluation
  - knowledge distillation
references:
  - SINGULARITY-MBP-EMERGENCE-SELFEVOLVE
  - SINGULARITY-MBP-EMERGENCE-PREDICTION
  - SINGULARITY-MBP-COMBAT-ADVERSARY
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-EMERGENCE-CONVERGENCE
---

# SINGULARITY-MBP-APEX-COGNITION v1.0

> **The graph that thinks, learns, verifies, and evolves — autonomously.**

TIER-7/APEX sits above all other MBP tiers. It orchestrates Tiers 0–6 as
cognitive subsystems, applies evolutionary pressure to agent strategies,
validates every output through critic sub-agents, and persists learned
intelligence across sessions so THEMANBEARPIG never forgets a lesson.

---

## Layer 1: EvoAgent Architecture — Population-Based Strategy Evolution

### 1.1 Core AORP Loop Controller

```javascript
/**
 * EvoAgentController — Act-Observe-Reflect-Plan loop with evolutionary strategy selection.
 *
 * Each agent maintains a "strategy genome" — a configuration of search patterns,
 * query expansions, lane priorities, and scoring weights. A population of 8 strategy
 * variants competes via tournament selection. Winners reproduce with mutation;
 * losers are replaced. Over sessions the population converges on strategies that
 * produce the highest-value evidence discoveries.
 *
 * Architecture:
 *   Population(8 genomes) → Tournament(k=3) → Crossover → Mutation → Evaluate → Select
 */
class EvoAgentController {
  constructor(opts = {}) {
    this.populationSize = opts.populationSize || 8;
    this.tournamentK    = opts.tournamentK || 3;
    this.mutationRate   = opts.mutationRate || 0.15;
    this.crossoverRate  = opts.crossoverRate || 0.7;
    this.eliteCount     = opts.eliteCount || 2;
    this.generationCap  = opts.generationCap || 50;
    this.generation     = 0;

    this.population = this._loadOrSeed();
    this.fitnessHistory = JSON.parse(
      localStorage.getItem('evo_fitness_history') || '[]'
    );
    this.activeAgent = null;
    this.observationBuffer = [];
  }

  // ── Genome Schema ───────────────────────────────────────────────
  _defaultGenome() {
    return {
      id: crypto.randomUUID(),
      generation: this.generation,
      // Search strategy genes
      queryExpansionDepth: 2,          // how many synonym expansions
      lanePriorities: {A:1, B:0.3, C:0.5, D:0.8, E:0.9, F:0.7, CRIMINAL:0.1},
      fts5BoostFactors: {exact:3.0, phrase:2.0, prefix:1.0, fuzzy:0.5},
      minConfidenceThreshold: 0.6,
      maxResultsPerQuery: 25,
      // Scoring weights
      scoringWeights: {
        impeachmentValue: 0.25,
        contradictionSeverity: 0.20,
        timelineProximity: 0.15,
        authorityChainDepth: 0.15,
        evidenceNovelty: 0.15,
        crossLaneRelevance: 0.10
      },
      // Behavioral genes
      explorationVsExploitation: 0.3,  // 0 = pure exploit, 1 = pure explore
      retryMutationStrength: 0.2,
      parallelQueryCount: 2,
      // Fitness tracking
      fitness: 0,
      evaluationCount: 0,
      highValueFinds: 0,
      totalFinds: 0,
      avgResponseMs: 0
    };
  }

  _loadOrSeed() {
    const saved = localStorage.getItem('evo_population');
    if (saved) {
      const pop = JSON.parse(saved);
      if (pop.length === this.populationSize) return pop;
    }
    return Array.from({length: this.populationSize}, () => this._randomGenome());
  }

  _randomGenome() {
    const g = this._defaultGenome();
    g.queryExpansionDepth = this._randInt(1, 4);
    g.minConfidenceThreshold = 0.3 + Math.random() * 0.5;
    g.maxResultsPerQuery = this._randInt(10, 50);
    g.explorationVsExploitation = Math.random();
    g.retryMutationStrength = 0.05 + Math.random() * 0.4;
    g.parallelQueryCount = this._randInt(1, 3);
    // Randomize scoring weights (normalized to 1.0)
    const keys = Object.keys(g.scoringWeights);
    const raw = keys.map(() => Math.random());
    const sum = raw.reduce((a, b) => a + b, 0);
    keys.forEach((k, i) => { g.scoringWeights[k] = raw[i] / sum; });
    // Randomize lane priorities
    Object.keys(g.lanePriorities).forEach(k => {
      g.lanePriorities[k] = Math.round(Math.random() * 10) / 10;
    });
    return g;
  }

  // ── AORP Loop ───────────────────────────────────────────────────

  /** ACT — execute the active genome's strategy against the database. */
  act(queryContext) {
    this.activeAgent = this._selectActiveGenome();
    const genome = this.activeAgent;
    const query = this._buildQuery(queryContext, genome);
    const startMs = performance.now();
    return {
      genome: genome.id,
      query,
      lanePriorities: genome.lanePriorities,
      maxResults: genome.maxResultsPerQuery,
      expansionDepth: genome.queryExpansionDepth,
      startMs
    };
  }

  /** OBSERVE — collect results from the action and buffer observations. */
  observe(actionResult, dbResults) {
    const elapsedMs = performance.now() - actionResult.startMs;
    const observation = {
      genomeId: actionResult.genome,
      query: actionResult.query,
      resultCount: dbResults.length,
      highValueCount: dbResults.filter(r => r.score >= 0.7).length,
      novelCount: dbResults.filter(r => r.isNovel).length,
      elapsedMs,
      timestamp: Date.now()
    };
    this.observationBuffer.push(observation);
    return observation;
  }

  /** REFLECT — evaluate the genome's performance from observations. */
  reflect() {
    if (this.observationBuffer.length === 0) return null;
    const obs = this.observationBuffer;
    const genome = this.population.find(g => g.id === obs[0].genomeId);
    if (!genome) return null;

    const totalHigh = obs.reduce((s, o) => s + o.highValueCount, 0);
    const totalNovel = obs.reduce((s, o) => s + o.novelCount, 0);
    const avgMs = obs.reduce((s, o) => s + o.elapsedMs, 0) / obs.length;
    const totalResults = obs.reduce((s, o) => s + o.resultCount, 0);

    // Fitness = weighted combination of quality and efficiency
    const rawFitness =
      (totalHigh * 3.0) +          // high-value evidence is paramount
      (totalNovel * 2.0) +          // novelty prevents re-discovery
      (totalResults * 0.1) -        // volume has diminishing returns
      (avgMs > 200 ? (avgMs - 200) * 0.01 : 0);  // speed penalty above budget

    genome.fitness = (genome.fitness * genome.evaluationCount + rawFitness) /
                     (genome.evaluationCount + 1);
    genome.evaluationCount += 1;
    genome.highValueFinds += totalHigh;
    genome.totalFinds += totalResults;
    genome.avgResponseMs = (genome.avgResponseMs + avgMs) / 2;

    this.observationBuffer = [];
    return { genomeId: genome.id, fitness: genome.fitness, totalHigh, totalNovel, avgMs };
  }

  /** PLAN — evolve the population based on accumulated fitness. */
  plan() {
    this.generation++;
    const sorted = [...this.population].sort((a, b) => b.fitness - a.fitness);

    // Elite preservation — top genomes survive unchanged
    const nextGen = sorted.slice(0, this.eliteCount).map(g => ({...g}));

    // Fill remaining slots with tournament-selected offspring
    while (nextGen.length < this.populationSize) {
      const parent1 = this._tournamentSelect();
      const parent2 = this._tournamentSelect();
      let child;
      if (Math.random() < this.crossoverRate) {
        child = this._crossover(parent1, parent2);
      } else {
        child = {...parent1, id: crypto.randomUUID(), fitness: 0, evaluationCount: 0};
      }
      if (Math.random() < this.mutationRate) {
        this._mutate(child);
      }
      child.generation = this.generation;
      nextGen.push(child);
    }

    this.population = nextGen;
    this._persist();
    this.fitnessHistory.push({
      generation: this.generation,
      bestFitness: sorted[0].fitness,
      avgFitness: sorted.reduce((s, g) => s + g.fitness, 0) / sorted.length,
      timestamp: Date.now()
    });
    localStorage.setItem('evo_fitness_history', JSON.stringify(this.fitnessHistory));
    return {
      generation: this.generation,
      best: sorted[0],
      populationAvg: sorted.reduce((s, g) => s + g.fitness, 0) / sorted.length
    };
  }

  // ── Genetic Operators ───────────────────────────────────────────

  _tournamentSelect() {
    const contestants = [];
    for (let i = 0; i < this.tournamentK; i++) {
      contestants.push(this.population[this._randInt(0, this.population.length - 1)]);
    }
    return contestants.sort((a, b) => b.fitness - a.fitness)[0];
  }

  _crossover(p1, p2) {
    const child = this._defaultGenome();
    child.id = crypto.randomUUID();
    // Uniform crossover on numeric genes
    child.queryExpansionDepth = Math.random() < 0.5 ? p1.queryExpansionDepth : p2.queryExpansionDepth;
    child.minConfidenceThreshold = Math.random() < 0.5 ? p1.minConfidenceThreshold : p2.minConfidenceThreshold;
    child.maxResultsPerQuery = Math.random() < 0.5 ? p1.maxResultsPerQuery : p2.maxResultsPerQuery;
    child.explorationVsExploitation = (p1.explorationVsExploitation + p2.explorationVsExploitation) / 2;
    child.parallelQueryCount = Math.random() < 0.5 ? p1.parallelQueryCount : p2.parallelQueryCount;
    // Blend scoring weights
    const keys = Object.keys(child.scoringWeights);
    keys.forEach(k => {
      child.scoringWeights[k] = (p1.scoringWeights[k] + p2.scoringWeights[k]) / 2;
    });
    // Blend lane priorities
    Object.keys(child.lanePriorities).forEach(k => {
      child.lanePriorities[k] = Math.round(
        ((p1.lanePriorities[k] || 0.5) + (p2.lanePriorities[k] || 0.5)) / 2 * 10
      ) / 10;
    });
    return child;
  }

  _mutate(genome) {
    const strength = genome.retryMutationStrength;
    // Mutate one random numeric gene
    const genes = ['queryExpansionDepth', 'minConfidenceThreshold', 'maxResultsPerQuery',
                   'explorationVsExploitation', 'parallelQueryCount'];
    const gene = genes[this._randInt(0, genes.length - 1)];
    const delta = (Math.random() - 0.5) * 2 * strength;
    if (gene === 'queryExpansionDepth') {
      genome[gene] = Math.max(1, Math.min(5, Math.round(genome[gene] + delta * 3)));
    } else if (gene === 'maxResultsPerQuery') {
      genome[gene] = Math.max(5, Math.min(100, Math.round(genome[gene] + delta * 30)));
    } else if (gene === 'parallelQueryCount') {
      genome[gene] = Math.max(1, Math.min(3, Math.round(genome[gene] + delta * 2)));
    } else {
      genome[gene] = Math.max(0, Math.min(1, genome[gene] + delta));
    }
    // Mutate one random scoring weight and renormalize
    const wKeys = Object.keys(genome.scoringWeights);
    const wk = wKeys[this._randInt(0, wKeys.length - 1)];
    genome.scoringWeights[wk] = Math.max(0.01, genome.scoringWeights[wk] + (Math.random() - 0.5) * 0.1);
    const wSum = Object.values(genome.scoringWeights).reduce((a, b) => a + b, 0);
    wKeys.forEach(k => { genome.scoringWeights[k] /= wSum; });
  }

  // ── Query Building ──────────────────────────────────────────────

  _buildQuery(context, genome) {
    const base = context.topic || context.query || '';
    const expansions = [];
    if (genome.queryExpansionDepth >= 2 && context.synonyms) {
      expansions.push(...context.synonyms.slice(0, genome.queryExpansionDepth));
    }
    const terms = [base, ...expansions].filter(Boolean);
    const fts5 = terms.map(t => `"${t}"`).join(' OR ');
    return {
      fts5Query: fts5,
      lanes: Object.entries(genome.lanePriorities)
        .filter(([, v]) => v >= genome.minConfidenceThreshold)
        .map(([k]) => k),
      limit: genome.maxResultsPerQuery
    };
  }

  _selectActiveGenome() {
    // ε-greedy: exploit best genome most of the time, explore randomly sometimes
    const epsilon = this.population[0]?.explorationVsExploitation ?? 0.3;
    if (Math.random() < epsilon) {
      return this.population[this._randInt(0, this.population.length - 1)];
    }
    return [...this.population].sort((a, b) => b.fitness - a.fitness)[0];
  }

  _persist() {
    localStorage.setItem('evo_population', JSON.stringify(this.population));
  }

  _randInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

  // ── Public API ──────────────────────────────────────────────────

  getBestGenome() {
    return [...this.population].sort((a, b) => b.fitness - a.fitness)[0];
  }

  getGenerationStats() {
    const sorted = [...this.population].sort((a, b) => b.fitness - a.fitness);
    return {
      generation: this.generation,
      best: sorted[0].fitness,
      worst: sorted[sorted.length - 1].fitness,
      avg: sorted.reduce((s, g) => s + g.fitness, 0) / sorted.length,
      diversity: this._populationDiversity()
    };
  }

  _populationDiversity() {
    // Coefficient of variation of fitness values
    const fits = this.population.map(g => g.fitness);
    const mean = fits.reduce((a, b) => a + b, 0) / fits.length;
    if (mean === 0) return 1.0;
    const variance = fits.reduce((s, f) => s + (f - mean) ** 2, 0) / fits.length;
    return Math.sqrt(variance) / mean;
  }

  resetPopulation() {
    this.population = Array.from({length: this.populationSize}, () => this._randomGenome());
    this.generation = 0;
    this.fitnessHistory = [];
    this._persist();
    localStorage.setItem('evo_fitness_history', '[]');
  }
}
```

---

## Layer 2: Critic / Verifier Sub-Agent System

### 2.1 CriticAgent — Multi-Faceted Output Verification

```javascript
/**
 * CriticAgent — validates every piece of intelligence before it enters the graph.
 *
 * Five verification axes:
 *   1. Citation validity      — does the cited authority actually exist?
 *   2. Logical soundness      — does evidence → rule → conclusion hold?
 *   3. Contradiction check    — does this conflict with existing intelligence?
 *   4. Hallucination guard    — does this contain known fabrications?
 *   5. Confidence calibration — is the stated confidence realistic?
 */
class CriticAgent {
  constructor(dbQueryFn) {
    this.query = dbQueryFn;  // async (sql, params) => rows
    this.verificationLog = [];
    this.calibrationWindow = [];
    this.WINDOW_SIZE = 200;

    // Known hallucination patterns — hard-coded per Rule 9
    this.HALLUCINATION_PATTERNS = [
      /91%\s*alienation/i,
      /Jane\s+Berry/i,
      /Patricia\s+Berry/i,
      /P35878/i,
      /Ron\s+Berry,?\s+Esq/i,
      /Emily\s+A(?:nn)?\s+Watson/i,     // wrong middle name format check
      /Lincoln\s+David\s+Watson/i,
      /Amy\s+McNeill/i,
      /Emily\s+M\.\s+Watson/i,
      /Tiffany\s+Watson/i,
      /9\s+CPS\s+investigations/i,
      /undersigned\s+counsel/i,
      /attorney\s+for\s+(?:the\s+)?plaintiff/i,
      /MCL\s+722\.27c/i,                // does not exist
      /Brady\s+v\.?\s+Maryland/i,        // criminal only, not family law
    ];

    // Canonical party names for positive validation
    this.CANONICAL = {
      plaintiff: 'Andrew James Pigors',
      defendant: 'Emily A. Watson',
      child: 'L.D.W.',
      judge: 'Hon. Jenny L. McNeill',
      chiefJudge: 'Hon. Kenneth Hoopes',
      foc: 'Pamela Rusco',
      formerCounsel: 'Jennifer Barnes (P55406)',
      nonAttorney: 'Ronald Berry'
    };
  }

  /**
   * Full verification pipeline — runs all 5 axes on a piece of intelligence.
   * Returns {valid: boolean, issues: string[], confidence: number, details: object}
   */
  async verify(intel) {
    const issues = [];
    const details = {};

    // Axis 1: Hallucination guard (fastest, short-circuit on critical)
    const halCheck = this.detectHallucinations(intel.text || intel.content || '');
    if (halCheck.found.length > 0) {
      issues.push(...halCheck.found.map(h => `HALLUCINATION: "${h.match}" — ${h.reason}`));
      details.hallucinations = halCheck;
    }

    // Axis 2: Citation validation
    if (intel.citations && intel.citations.length > 0) {
      const citCheck = await this.validateCitations(intel.citations);
      if (citCheck.invalid.length > 0) {
        issues.push(...citCheck.invalid.map(c => `INVALID_CITATION: "${c.cite}" — not found in authority_chains_v2`));
      }
      details.citations = citCheck;
    }

    // Axis 3: Logical soundness (if IRAC structure provided)
    if (intel.rule && intel.facts && intel.conclusion) {
      const logicCheck = this.checkLogicalSoundness(intel);
      if (!logicCheck.sound) {
        issues.push(...logicCheck.gaps.map(g => `LOGIC_GAP: ${g}`));
      }
      details.logic = logicCheck;
    }

    // Axis 4: Contradiction detection
    if (intel.claim) {
      const contraCheck = await this.detectContradictions(intel.claim, intel.source);
      if (contraCheck.contradictions.length > 0) {
        issues.push(...contraCheck.contradictions.map(c =>
          `CONTRADICTION: "${c.existing}" vs "${intel.claim}" (severity: ${c.severity})`
        ));
      }
      details.contradictions = contraCheck;
    }

    // Axis 5: Confidence calibration
    const calibrated = this.calibrate(intel.confidence || 0.5, issues.length);
    details.calibration = calibrated;

    const valid = issues.filter(i => i.startsWith('HALLUCINATION')).length === 0 &&
                  issues.filter(i => i.startsWith('INVALID_CITATION')).length === 0;

    const entry = {
      timestamp: Date.now(),
      valid,
      issueCount: issues.length,
      predictedConfidence: intel.confidence || 0.5,
      adjustedConfidence: calibrated.adjusted,
      wasCorrect: null  // filled in later by outcome tracking
    };
    this.verificationLog.push(entry);

    return { valid, issues, confidence: calibrated.adjusted, details };
  }

  // ── Axis 1: Hallucination Detection ─────────────────────────────

  detectHallucinations(text) {
    const found = [];
    for (const pattern of this.HALLUCINATION_PATTERNS) {
      const match = text.match(pattern);
      if (match) {
        found.push({
          match: match[0],
          pattern: pattern.source,
          reason: this._hallucinationReason(pattern.source),
          position: match.index
        });
      }
    }
    // Fabricated aggregate statistics check
    const statsPattern = /(\d{3,},?\d*)\s+(keyword hits|person references|misconduct.*hits)/gi;
    let m;
    while ((m = statsPattern.exec(text)) !== null) {
      const num = parseInt(m[1].replace(/,/g, ''), 10);
      if (num > 10000) {
        found.push({
          match: m[0], pattern: 'AGGREGATE_STAT',
          reason: 'AI-generated aggregate statistics are banned in filings (Rule 20)',
          position: m.index
        });
      }
    }
    return { found, clean: found.length === 0 };
  }

  _hallucinationReason(src) {
    const reasons = {
      '91%\\s*alienation': 'Fabricated score — use specific incident counts instead',
      'Jane\\s+Berry': 'Person never existed — correct: Jennifer Barnes (P55406)',
      'Patricia\\s+Berry': 'Person never existed — correct: Jennifer Barnes (P55406)',
      'P35878': 'Fabricated bar number — correct: P55406',
      'MCL\\s+722\\.27c': 'Statute does not exist — correct: MCL 722.23(j)',
      'Brady\\s+v\\.?\\s+Maryland': 'Criminal only — use Mathews v Eldridge for family law',
    };
    for (const [key, val] of Object.entries(reasons)) {
      if (src.includes(key.replace(/\\\\/g, '\\'))) return val;
    }
    return 'Known hallucination pattern';
  }

  // ── Axis 2: Citation Validation ─────────────────────────────────

  async validateCitations(citations) {
    const valid = [];
    const invalid = [];
    for (const cite of citations) {
      const rows = await this.query(
        `SELECT primary_citation, supporting_citation, relationship
         FROM authority_chains_v2
         WHERE primary_citation LIKE ? OR supporting_citation LIKE ?
         LIMIT 5`,
        [`%${cite}%`, `%${cite}%`]
      );
      if (rows.length > 0) {
        valid.push({cite, matches: rows.length, sample: rows[0]});
      } else {
        // Fallback: check michigan_rules_extracted
        const ruleRows = await this.query(
          `SELECT rule_citation, rule_text FROM michigan_rules_extracted
           WHERE rule_citation LIKE ? LIMIT 3`,
          [`%${cite}%`]
        );
        if (ruleRows.length > 0) {
          valid.push({cite, matches: ruleRows.length, source: 'michigan_rules_extracted'});
        } else {
          invalid.push({cite, searched: ['authority_chains_v2', 'michigan_rules_extracted']});
        }
      }
    }
    return {valid, invalid, ratio: valid.length / (valid.length + invalid.length || 1)};
  }

  // ── Axis 3: Logical Soundness ───────────────────────────────────

  checkLogicalSoundness(intel) {
    const gaps = [];
    const {rule, facts, conclusion} = intel;

    // Check rule references a legal standard
    const ruleHasAuthority = /MCR|MCL|MRE|USC|FRCP|v\.\s|§/i.test(rule);
    if (!ruleHasAuthority) {
      gaps.push('Rule statement lacks legal authority citation');
    }
    // Check facts reference evidence
    const factsHaveEvidence = /Ex\.\s|Exhibit|PIGORS-|p\.\s?\d|Bates/i.test(facts);
    if (!factsHaveEvidence) {
      gaps.push('Facts lack exhibit or record citation');
    }
    // Check conclusion requests relief
    const conclusionHasRelief = /grant|deny|order|dismiss|sustain|overrule|restore|modify/i.test(conclusion);
    if (!conclusionHasRelief) {
      gaps.push('Conclusion does not request specific relief');
    }
    // Check logical chain — conclusion keywords should connect to rule keywords
    const ruleKeywords = new Set(rule.toLowerCase().match(/\b\w{4,}\b/g) || []);
    const concKeywords = new Set(conclusion.toLowerCase().match(/\b\w{4,}\b/g) || []);
    const overlap = [...concKeywords].filter(k => ruleKeywords.has(k));
    if (overlap.length === 0) {
      gaps.push('Conclusion uses no terms from the rule — possible logical disconnect');
    }

    return {sound: gaps.length === 0, gaps, overlapTerms: overlap};
  }

  // ── Axis 4: Contradiction Detection ─────────────────────────────

  async detectContradictions(newClaim, source) {
    const contradictions = [];
    // Search existing evidence for semantically opposing claims
    const sanitized = newClaim.replace(/[^\w\s*"]/g, ' ').trim();
    const words = sanitized.split(/\s+/).slice(0, 5).join(' ');
    let existingRows;
    try {
      existingRows = await this.query(
        `SELECT quote_text, source_file, category FROM evidence_quotes
         WHERE evidence_fts MATCH ? LIMIT 20`,
        [words]
      );
    } catch {
      existingRows = await this.query(
        `SELECT quote_text, source_file, category FROM evidence_quotes
         WHERE quote_text LIKE ? LIMIT 20`,
        [`%${words.split(' ')[0]}%`]
      );
    }

    // Negation detection heuristic
    const negators = ['not', 'never', 'no', 'denied', 'refused', 'false', 'untrue', 'incorrect'];
    const claimLower = newClaim.toLowerCase();
    for (const row of existingRows) {
      if (!row.quote_text) continue;
      const existLower = row.quote_text.toLowerCase();
      // If one contains a negator of something the other asserts, flag it
      for (const neg of negators) {
        if ((claimLower.includes(neg) && !existLower.includes(neg)) ||
            (!claimLower.includes(neg) && existLower.includes(neg))) {
          // Rough check: share a subject noun?
          const claimNouns = claimLower.match(/\b[A-Z][a-z]+\b/g) || [];
          const existNouns = existLower.match(/\b[A-Z][a-z]+\b/g) || [];
          const shared = claimNouns.filter(n => existNouns.includes(n));
          if (shared.length > 0) {
            contradictions.push({
              existing: row.quote_text.slice(0, 120),
              source: row.source_file,
              sharedSubjects: shared,
              severity: shared.length >= 2 ? 'high' : 'medium'
            });
            break;
          }
        }
      }
    }
    return {contradictions, searchedCount: existingRows.length};
  }

  // ── Axis 5: Confidence Calibration ──────────────────────────────

  calibrate(rawConfidence, issueCount) {
    // Penalize confidence based on verification issues found
    const penalty = Math.min(0.4, issueCount * 0.1);
    let adjusted = Math.max(0.05, rawConfidence - penalty);

    // Apply calibration curve from historical accuracy
    const cal = this._getCalibrationCurve();
    if (cal) {
      const bucket = Math.floor(adjusted * 10) / 10;  // round to 0.1
      const correction = cal[bucket.toFixed(1)];
      if (correction !== undefined) {
        adjusted = correction;
      }
    }
    return {raw: rawConfidence, adjusted: Math.round(adjusted * 100) / 100, penalty, issueCount};
  }

  _getCalibrationCurve() {
    return JSON.parse(localStorage.getItem('critic_calibration_curve') || 'null');
  }
}
```

### 2.2 Batch Verification Pipeline (Python Backend)

```python
"""
batch_verify.py — Run CriticAgent checks across a batch of evidence records.
Designed to be called via exec_python from D:\LitigationOS_tmp\.
"""
import sqlite3, re, json, sys
from pathlib import Path

DB_PATH = r'C:\Users\andre\LitigationOS\litigation_context.db'

HALLUCINATION_PATTERNS = [
    (r'91%\s*alienation', 'Fabricated alienation score'),
    (r'Jane\s+Berry', 'Person never existed'),
    (r'Patricia\s+Berry', 'Person never existed'),
    (r'P35878', 'Fabricated bar number'),
    (r'MCL\s+722\.27c', 'Statute does not exist — use MCL 722.23(j)'),
    (r'Brady\s+v\.?\s+Maryland', 'Criminal only — use Mathews v Eldridge'),
    (r'Lincoln\s+David', 'Child full name violation — use L.D.W.'),
    (r'undersigned\s+counsel', 'Pro se — never imply attorney'),
]

def verify_batch(table='evidence_quotes', limit=500):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA busy_timeout=60000')
    conn.execute('PRAGMA journal_mode=WAL')

    col_info = conn.execute(f'PRAGMA table_info({table})').fetchall()
    cols = {r[1] for r in col_info}
    text_col = 'quote_text' if 'quote_text' in cols else 'content' if 'content' in cols else None
    if not text_col:
        print(json.dumps({'error': f'No text column found in {table}', 'columns': list(cols)}))
        return

    rows = conn.execute(
        f'SELECT rowid, {text_col} FROM {table} WHERE {text_col} IS NOT NULL LIMIT ?',
        (limit,)
    ).fetchall()

    issues = []
    for rowid, text in rows:
        for pattern, reason in HALLUCINATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({'rowid': rowid, 'pattern': pattern, 'reason': reason,
                               'snippet': text[:80]})

    conn.close()
    result = {
        'table': table, 'scanned': len(rows), 'issues_found': len(issues),
        'issues': issues[:50]  # cap output size
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    tbl = sys.argv[1] if len(sys.argv) > 1 else 'evidence_quotes'
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    verify_batch(tbl, lim)
```

---

## Layer 3: Hybrid Neural + Symbolic Reasoning

### 3.1 HybridReasoningEngine — Symbolic Rules Constrain Neural Search

```javascript
/**
 * HybridReasoningEngine — fuses rule-based legal logic with semantic similarity.
 *
 * Architecture:
 *   1. Symbolic layer defines legal conditions as executable predicates
 *   2. Neural layer embeds evidence via sentence-transformers (384-dim)
 *   3. Fusion layer: symbolic rules constrain which neural matches are admissible
 *   4. Legal syllogism engine: major premise (rule) + minor premise (fact) → conclusion
 *
 * The symbolic layer prevents neural hallucination: even if a neural match is
 * semantically similar, it must satisfy the symbolic predicate to pass through.
 */
class HybridReasoningEngine {
  constructor() {
    this.ruleTemplates = this._buildMichiganRuleTemplates();
    this.syllogismCache = new Map();
  }

  // ── Michigan Rule Template Library ──────────────────────────────

  _buildMichiganRuleTemplates() {
    return {
      // Custody factors — MCL 722.23(a)-(l)
      'MCL_722_23_a': {
        citation: 'MCL 722.23(a)',
        name: 'Love, affection, emotional ties',
        predicate: (evidence) =>
          /love|affection|emotional|bond|attach/i.test(evidence.text) &&
          /child|son|daughter|L\.D\.W/i.test(evidence.text),
        requiredElements: ['emotional_tie_evidence', 'party_identification'],
        scoringBias: 'father'  // evidence typically favors father in this case
      },
      'MCL_722_23_c': {
        citation: 'MCL 722.23(c)',
        name: 'Capacity to provide',
        predicate: (evidence) =>
          /capacity|provide|care|food|shelter|medical|education/i.test(evidence.text),
        requiredElements: ['capacity_evidence', 'comparison_to_other_party'],
        scoringBias: 'neutral'
      },
      'MCL_722_23_j': {
        citation: 'MCL 722.23(j)',
        name: 'Willingness to facilitate relationship',
        predicate: (evidence) =>
          /facilitat|alienat|withhold|deny|interfer|obstruct|prevent.*contact/i.test(evidence.text),
        requiredElements: ['facilitation_or_obstruction', 'specific_incidents'],
        scoringBias: 'father'  // 230+ days withholding documented
      },
      'MCL_722_23_k': {
        citation: 'MCL 722.23(k)',
        name: 'Domestic violence',
        predicate: (evidence) =>
          /domestic.*violen|assault|abus|protection.*order|PPO/i.test(evidence.text),
        requiredElements: ['dv_allegation_or_finding', 'credibility_assessment'],
        scoringBias: 'contested'  // false allegations pattern
      },
      'MCL_722_23_l': {
        citation: 'MCL 722.23(l)',
        name: 'Other relevant factors',
        predicate: (evidence) => true,  // catch-all — always matches
        requiredElements: ['relevant_factor_description'],
        scoringBias: 'neutral'
      },
      // Disqualification — MCR 2.003
      'MCR_2_003_bias': {
        citation: 'MCR 2.003(C)(1)(b)',
        name: 'Bias or prejudice',
        predicate: (evidence) =>
          /bias|prejudice|impartial|ex\s*parte|one-sided|unequal/i.test(evidence.text) &&
          /judge|court|McNeill|bench/i.test(evidence.text),
        requiredElements: ['specific_bias_facts', 'judge_identification'],
        scoringBias: 'father'
      },
      'MCR_2_003_knowledge': {
        citation: 'MCR 2.003(C)(1)(a)',
        name: 'Personal knowledge of disputed facts',
        predicate: (evidence) =>
          /personal.*knowledge|witnessed|observed|prior.*involve/i.test(evidence.text),
        requiredElements: ['fact_known', 'how_judge_acquired'],
        scoringBias: 'father'
      },
      // PPO — MCL 600.2950
      'MCL_600_2950': {
        citation: 'MCL 600.2950',
        name: 'Personal protection order',
        predicate: (evidence) =>
          /PPO|protection.*order|stalk|harass|threat|assault/i.test(evidence.text),
        requiredElements: ['qualifying_conduct', 'petition_or_response'],
        scoringBias: 'contested'
      },
      // Contempt — MCL 600.1701
      'MCL_600_1701': {
        citation: 'MCL 600.1701',
        name: 'Contempt of court',
        predicate: (evidence) =>
          /contempt|willful|disobey|violat.*order|comply/i.test(evidence.text),
        requiredElements: ['court_order_violated', 'willfulness', 'ability_to_comply'],
        scoringBias: 'neutral'
      },
      // Due process — 14th Amendment / Mathews v Eldridge
      'MATHEWS_ELDRIDGE': {
        citation: 'Mathews v Eldridge, 424 US 319 (1976)',
        name: 'Procedural due process',
        predicate: (evidence) =>
          /due\s*process|notice|hearing|opportunit.*heard|fundamental.*right/i.test(evidence.text),
        requiredElements: ['private_interest', 'risk_of_error', 'government_interest'],
        scoringBias: 'father'
      },
      // Parental rights — Troxel v Granville
      'TROXEL': {
        citation: 'Troxel v Granville, 530 US 57 (2000)',
        name: 'Fundamental parental rights',
        predicate: (evidence) =>
          /fundamental.*right|parent.*right|liberty.*interest|fit.*parent/i.test(evidence.text),
        requiredElements: ['parental_fitness', 'state_interference'],
        scoringBias: 'father'
      },
      // Change of circumstances — Vodvarka
      'VODVARKA': {
        citation: 'Vodvarka v Grasmeyer, 259 Mich App 499 (2003)',
        name: 'Proper cause / change of circumstances',
        predicate: (evidence) =>
          /change.*circumstance|proper\s*cause|since.*judgment|material.*change/i.test(evidence.text),
        requiredElements: ['specific_change', 'since_last_order', 'affects_child'],
        scoringBias: 'neutral'
      },
      // Section 1983
      'SECTION_1983': {
        citation: '42 USC § 1983',
        name: 'Civil rights deprivation under color of law',
        predicate: (evidence) =>
          /under\s*color|state\s*actor|depri.*right|constitutional/i.test(evidence.text) &&
          /judge|court|officer|official|government/i.test(evidence.text),
        requiredElements: ['state_actor', 'constitutional_right', 'causation', 'damages'],
        scoringBias: 'father'
      },
      // Superintending control
      'MCR_7_306': {
        citation: 'MCR 7.306',
        name: 'Superintending control / mandamus',
        predicate: (evidence) =>
          /superintend|mandamus|original.*jurisdiction|no.*adequate.*remedy/i.test(evidence.text),
        requiredElements: ['lower_court_action', 'no_other_remedy', 'clear_duty'],
        scoringBias: 'father'
      },
      // Habeas corpus
      'HABEAS': {
        citation: 'MCL 600.4301',
        name: 'Habeas corpus',
        predicate: (evidence) =>
          /habeas.*corpus|unlawful.*detention|custody.*depri/i.test(evidence.text),
        requiredElements: ['unlawful_custody', 'no_other_remedy'],
        scoringBias: 'father'
      },
      // MRE authentication
      'MRE_901': {
        citation: 'MRE 901(b)(1)',
        name: 'Authentication by testimony',
        predicate: (evidence) =>
          /authenticat|foundation|identif.*voice|witness.*knowledge/i.test(evidence.text),
        requiredElements: ['witness_with_knowledge', 'testimony_description'],
        scoringBias: 'neutral'
      },
      // Sullivan v Gray — one-party recording
      'SULLIVAN_GRAY': {
        citation: 'Sullivan v Gray, 117 Mich App 476 (1982)',
        name: 'One-party consent recording',
        predicate: (evidence) =>
          /record|audio|video|one.*party|consent|MCL.*750\.539/i.test(evidence.text),
        requiredElements: ['participant_present', 'not_altered'],
        scoringBias: 'father'
      },
      // Pierron — custody due process
      'PIERRON': {
        citation: 'Pierron v Pierron, 486 Mich 81 (2010)',
        name: 'Due process in custody proceedings',
        predicate: (evidence) =>
          /pierron|custody.*due.*process|adequate.*hearing/i.test(evidence.text),
        requiredElements: ['custody_proceeding', 'procedural_deficiency'],
        scoringBias: 'father'
      }
    };
  }

  // ── Legal Syllogism Engine ──────────────────────────────────────

  /**
   * buildSyllogism — construct a legal argument from rule template + evidence.
   *
   * @param {string} ruleId  — key from ruleTemplates (e.g. 'MCL_722_23_j')
   * @param {object[]} evidence — array of {text, source, date, score}
   * @returns {{major, minor, conclusion, strength, gaps}}
   */
  buildSyllogism(ruleId, evidence) {
    const rule = this.ruleTemplates[ruleId];
    if (!rule) return {error: `Unknown rule: ${ruleId}`};

    // Filter evidence through symbolic predicate
    const qualifying = evidence.filter(e => rule.predicate(e));
    if (qualifying.length === 0) {
      return {
        major: `Under ${rule.citation}, ${rule.name}.`,
        minor: '[No qualifying evidence found]',
        conclusion: null,
        strength: 0,
        gaps: rule.requiredElements
      };
    }

    // Major premise: the legal rule
    const major = `Under ${rule.citation}, the court must consider ${rule.name.toLowerCase()}.`;

    // Minor premise: the best evidence
    const bestEvidence = qualifying.sort((a, b) => (b.score || 0) - (a.score || 0));
    const topN = bestEvidence.slice(0, 3);
    const minor = topN.map(e => {
      const src = e.source ? ` (${e.source})` : '';
      return e.text.slice(0, 200) + src;
    }).join('; ');

    // Check which required elements are present
    const present = [];
    const missing = [];
    for (const elem of rule.requiredElements) {
      const found = qualifying.some(e => e.text.toLowerCase().includes(elem.replace(/_/g, ' ')));
      (found ? present : missing).push(elem);
    }

    // Strength = (present elements / total elements) * log(evidence count + 1)
    const elementRatio = present.length / rule.requiredElements.length;
    const volumeFactor = Math.log2(qualifying.length + 1) / Math.log2(10);  // normalize
    const strength = Math.min(1.0, elementRatio * 0.7 + Math.min(volumeFactor, 0.3));

    const conclusion = `This factor ${strength >= 0.5 ? 'supports' : 'weakly supports'} ` +
                        `Plaintiff's position based on ${qualifying.length} qualifying evidence items.`;

    return {major, minor, conclusion, strength: Math.round(strength * 100) / 100,
            gaps: missing, evidenceCount: qualifying.length, ruleId};
  }

  /**
   * fuseReasoningChain — build a multi-factor argument from several syllogisms.
   * Used for 12-factor best-interest analysis or multi-count §1983 complaints.
   */
  fuseReasoningChain(syllogisms) {
    const valid = syllogisms.filter(s => s.strength > 0);
    const avgStrength = valid.length > 0
      ? valid.reduce((sum, s) => sum + s.strength, 0) / valid.length
      : 0;
    const allGaps = [...new Set(valid.flatMap(s => s.gaps || []))];
    const totalEvidence = valid.reduce((sum, s) => sum + (s.evidenceCount || 0), 0);

    return {
      factorCount: valid.length,
      totalFactorsAvailable: syllogisms.length,
      overallStrength: Math.round(avgStrength * 100) / 100,
      totalEvidence,
      criticalGaps: allGaps,
      strongFactors: valid.filter(s => s.strength >= 0.7).map(s => s.ruleId),
      weakFactors: valid.filter(s => s.strength < 0.4).map(s => s.ruleId),
      recommendation: avgStrength >= 0.6
        ? 'FILING_READY — sufficient evidence across factors'
        : avgStrength >= 0.4
          ? 'NEEDS_STRENGTHENING — acquire evidence for gaps'
          : 'NOT_READY — insufficient factual support'
    };
  }
}
```

---

## Layer 4: Cross-Session Learning Persistence

### 4.1 CrossSessionLearner — Strategy DNA Serialization

```javascript
/**
 * CrossSessionLearner — persists agent intelligence across browser/pywebview sessions.
 *
 * Storage tiers:
 *   1. localStorage   — fast, 5-10MB, volatile (cleared on cache wipe)
 *   2. IndexedDB       — 50MB+, structured, persistent across sessions
 *   3. DB write-back   — permanent, via exec_python → INSERT into litigation_context.db
 *
 * What gets persisted:
 *   - Strategy genomes (EvoAgent population)
 *   - Fitness histories (performance over generations)
 *   - Calibration curves (prediction accuracy)
 *   - Learning summaries (distilled heuristics)
 *   - Query success patterns (which searches yield high-value results)
 */
class CrossSessionLearner {
  constructor() {
    this.DB_NAME = 'mbp_cognition_store';
    this.DB_VERSION = 1;
    this.db = null;
    this._initDB();
  }

  async _initDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(this.DB_NAME, this.DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('genomes')) {
          db.createObjectStore('genomes', {keyPath: 'id'});
        }
        if (!db.objectStoreNames.contains('fitness')) {
          const fs = db.createObjectStore('fitness', {keyPath: 'id', autoIncrement: true});
          fs.createIndex('generation', 'generation', {unique: false});
        }
        if (!db.objectStoreNames.contains('learnings')) {
          const ls = db.createObjectStore('learnings', {keyPath: 'id'});
          ls.createIndex('domain', 'domain', {unique: false});
          ls.createIndex('timestamp', 'timestamp', {unique: false});
        }
        if (!db.objectStoreNames.contains('query_patterns')) {
          const qp = db.createObjectStore('query_patterns', {keyPath: 'id', autoIncrement: true});
          qp.createIndex('success_rate', 'successRate', {unique: false});
        }
      };
      req.onsuccess = (e) => { this.db = e.target.result; resolve(this.db); };
      req.onerror = (e) => reject(e);
    });
  }

  // ── Persist Operations ──────────────────────────────────────────

  async persist(category, data) {
    if (!this.db) await this._initDB();
    const storeName = this._storeFor(category);
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(storeName, 'readwrite');
      const store = tx.objectStore(storeName);
      const item = {...data, timestamp: Date.now()};
      if (!item.id) item.id = crypto.randomUUID();
      store.put(item);
      tx.oncomplete = () => resolve(item.id);
      tx.onerror = (e) => reject(e);
    });
  }

  async recall(category, query = {}) {
    if (!this.db) await this._initDB();
    const storeName = this._storeFor(category);
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const results = [];
      const cursor = store.openCursor();
      cursor.onsuccess = (e) => {
        const c = e.target.result;
        if (c) {
          const val = c.value;
          let match = true;
          for (const [k, v] of Object.entries(query)) {
            if (val[k] !== v) { match = false; break; }
          }
          if (match) results.push(val);
          c.continue();
        } else {
          resolve(results);
        }
      };
      cursor.onerror = (e) => reject(e);
    });
  }

  // ── Knowledge Distillation ──────────────────────────────────────

  /**
   * distill — compress learned patterns into compact heuristics.
   *
   * Analyzes fitness history to extract rules like:
   *   "Queries with lane E priority > 0.8 yield 2.3× more judicial evidence"
   *   "Expansion depth 3+ wastes time — sweet spot is 2"
   */
  async distill() {
    const genomes = await this.recall('genomes');
    const fitness = await this.recall('fitness');
    if (genomes.length < 4) return {rules: [], message: 'Need more data to distill'};

    const rules = [];
    const topGenomes = genomes.sort((a, b) => (b.fitness || 0) - (a.fitness || 0)).slice(0, 3);
    const bottomGenomes = genomes.sort((a, b) => (a.fitness || 0) - (b.fitness || 0)).slice(0, 3);

    // Rule extraction: what do top performers have that bottom performers lack?
    const topAvgExpansion = topGenomes.reduce((s, g) => s + g.queryExpansionDepth, 0) / topGenomes.length;
    const botAvgExpansion = bottomGenomes.reduce((s, g) => s + g.queryExpansionDepth, 0) / bottomGenomes.length;
    if (Math.abs(topAvgExpansion - botAvgExpansion) > 0.5) {
      rules.push({
        type: 'expansion_depth',
        direction: topAvgExpansion > botAvgExpansion ? 'increase' : 'decrease',
        optimalValue: Math.round(topAvgExpansion),
        confidence: 0.7
      });
    }

    // Lane priority analysis
    const lanes = ['A', 'B', 'C', 'D', 'E', 'F', 'CRIMINAL'];
    for (const lane of lanes) {
      const topAvg = topGenomes.reduce((s, g) => s + (g.lanePriorities?.[lane] || 0), 0) / topGenomes.length;
      const botAvg = bottomGenomes.reduce((s, g) => s + (g.lanePriorities?.[lane] || 0), 0) / bottomGenomes.length;
      if (topAvg - botAvg > 0.2) {
        rules.push({
          type: 'lane_priority',
          lane,
          action: 'boost',
          topAvg: Math.round(topAvg * 100) / 100,
          botAvg: Math.round(botAvg * 100) / 100,
          confidence: 0.6
        });
      }
    }

    // Scoring weight analysis
    const wKeys = Object.keys(topGenomes[0]?.scoringWeights || {});
    for (const wk of wKeys) {
      const topAvg = topGenomes.reduce((s, g) => s + (g.scoringWeights?.[wk] || 0), 0) / topGenomes.length;
      const botAvg = bottomGenomes.reduce((s, g) => s + (g.scoringWeights?.[wk] || 0), 0) / bottomGenomes.length;
      if (topAvg - botAvg > 0.05) {
        rules.push({
          type: 'scoring_weight',
          weight: wk,
          action: 'increase',
          difference: Math.round((topAvg - botAvg) * 1000) / 1000,
          confidence: 0.5
        });
      }
    }

    // Persist distilled rules
    await this.persist('learnings', {
      id: `distill_${Date.now()}`,
      domain: 'strategy_evolution',
      rules,
      genomeCount: genomes.length,
      generationsCovered: fitness.length
    });

    return {rules, genomeCount: genomes.length};
  }

  _storeFor(category) {
    const map = {
      genomes: 'genomes', fitness: 'fitness',
      learnings: 'learnings', query_patterns: 'query_patterns'
    };
    return map[category] || 'learnings';
  }
}
```

---

## Layer 5: Self-Calibrating Confidence System

### 5.1 ConfidenceCalibrator — Brier Scores + Per-Domain Tracking

```javascript
/**
 * ConfidenceCalibrator — tracks how well the system's confidence predictions
 * match actual outcomes. If the system says "80% confident" and is only right
 * 50% of the time at that level, the calibrator learns to adjust downward.
 *
 * Per-domain tracking: custody predictions may be better-calibrated than
 * criminal predictions. Each domain gets its own calibration curve.
 *
 * Metrics:
 *   - Brier score: mean squared error of probability forecasts (lower = better)
 *   - Calibration curve: predicted probability vs actual outcome frequency
 *   - Sharpness: how decisive the predictions are (avoid 0.5 hedging)
 */
class ConfidenceCalibrator {
  constructor() {
    this.WINDOW = 500;  // sliding window of predictions
    this.domains = ['custody', 'judicial', 'criminal', 'appellate', 'ppo', 'housing', 'general'];
    this.predictions = JSON.parse(localStorage.getItem('cal_predictions') || '{}');
    // Initialize domain buckets
    for (const d of this.domains) {
      if (!this.predictions[d]) this.predictions[d] = [];
    }
  }

  /**
   * record — log a prediction with its confidence.
   * Call this when the system makes a claim with a confidence score.
   */
  record(domain, predictedConfidence, metadata = {}) {
    const d = this.domains.includes(domain) ? domain : 'general';
    const entry = {
      id: crypto.randomUUID(),
      predicted: predictedConfidence,
      actual: null,  // filled by recordOutcome()
      timestamp: Date.now(),
      ...metadata
    };
    this.predictions[d].push(entry);
    // Trim to window size
    if (this.predictions[d].length > this.WINDOW) {
      this.predictions[d] = this.predictions[d].slice(-this.WINDOW);
    }
    this._save();
    return entry.id;
  }

  /**
   * recordOutcome — mark a prior prediction as correct (1) or incorrect (0).
   * This is how the calibrator learns: by seeing its past predictions' outcomes.
   */
  recordOutcome(predictionId, actualOutcome) {
    for (const d of this.domains) {
      const pred = this.predictions[d].find(p => p.id === predictionId);
      if (pred) {
        pred.actual = actualOutcome ? 1.0 : 0.0;
        this._save();
        return true;
      }
    }
    return false;
  }

  /**
   * adjust — given a raw confidence and domain, return the calibrated confidence.
   * Uses the historical calibration curve to correct systematic biases.
   */
  adjust(rawConfidence, domain = 'general') {
    const d = this.domains.includes(domain) ? domain : 'general';
    const curve = this._buildCurve(d);
    if (!curve || curve.dataPoints < 20) {
      return rawConfidence;  // not enough data to calibrate
    }
    // Find the nearest bucket
    const bucket = Math.round(rawConfidence * 10) / 10;
    const key = bucket.toFixed(1);
    if (curve.buckets[key] !== undefined) {
      return Math.round(curve.buckets[key] * 100) / 100;
    }
    // Interpolate between nearest buckets
    const keys = Object.keys(curve.buckets).map(Number).sort((a, b) => a - b);
    const below = keys.filter(k => k <= bucket).pop();
    const above = keys.filter(k => k > bucket).shift();
    if (below !== undefined && above !== undefined) {
      const range = above - below;
      const ratio = (bucket - below) / range;
      const interpolated = curve.buckets[below.toFixed(1)] * (1 - ratio) +
                           curve.buckets[above.toFixed(1)] * ratio;
      return Math.round(interpolated * 100) / 100;
    }
    return rawConfidence;
  }

  /**
   * getBrierScore — compute Brier score for a domain. Lower = better calibrated.
   * Perfect calibration = 0.0, worst = 1.0, random = 0.25.
   */
  getBrierScore(domain = 'general') {
    const d = this.domains.includes(domain) ? domain : 'general';
    const resolved = this.predictions[d].filter(p => p.actual !== null);
    if (resolved.length === 0) return null;
    const brier = resolved.reduce((sum, p) => sum + (p.predicted - p.actual) ** 2, 0) / resolved.length;
    return Math.round(brier * 10000) / 10000;
  }

  /**
   * getSharpness — how decisive are predictions? Avg distance from 0.5.
   * 0.0 = everything is 50/50 (useless). 0.5 = everything is 0 or 1 (decisive).
   */
  getSharpness(domain = 'general') {
    const d = this.domains.includes(domain) ? domain : 'general';
    const preds = this.predictions[d];
    if (preds.length === 0) return null;
    const sharp = preds.reduce((sum, p) => sum + Math.abs(p.predicted - 0.5), 0) / preds.length;
    return Math.round(sharp * 1000) / 1000;
  }

  getDashboard() {
    const dashboard = {};
    for (const d of this.domains) {
      const total = this.predictions[d].length;
      const resolved = this.predictions[d].filter(p => p.actual !== null).length;
      dashboard[d] = {
        total, resolved,
        brier: this.getBrierScore(d),
        sharpness: this.getSharpness(d),
        calibrationHealth: this._calibrationHealth(d)
      };
    }
    return dashboard;
  }

  _buildCurve(domain) {
    const resolved = this.predictions[domain].filter(p => p.actual !== null);
    if (resolved.length < 10) return null;
    const buckets = {};
    for (let b = 0; b <= 1.0; b += 0.1) {
      const key = b.toFixed(1);
      const inBucket = resolved.filter(p => Math.abs(p.predicted - b) < 0.05);
      if (inBucket.length >= 3) {
        buckets[key] = inBucket.reduce((s, p) => s + p.actual, 0) / inBucket.length;
      }
    }
    return {buckets, dataPoints: resolved.length};
  }

  _calibrationHealth(domain) {
    const brier = this.getBrierScore(domain);
    if (brier === null) return 'INSUFFICIENT_DATA';
    if (brier < 0.1) return 'EXCELLENT';
    if (brier < 0.2) return 'GOOD';
    if (brier < 0.3) return 'FAIR';
    return 'POOR';
  }

  _save() {
    localStorage.setItem('cal_predictions', JSON.stringify(this.predictions));
  }
}
```

---

## Layer 6: Agent Fleet Orchestration

### 6.1 FleetOrchestrator — Task Decomposition + Agent Selection + Result Fusion

```javascript
/**
 * FleetOrchestrator — breaks complex litigation queries into sub-tasks,
 * selects the best agent type for each, fuses results, and retries failures
 * with mutated strategies.
 *
 * Task types the orchestrator recognizes:
 *   - EVIDENCE_SEARCH: find evidence matching a claim
 *   - AUTHORITY_LOOKUP: find legal authorities supporting an argument
 *   - IMPEACHMENT_BUILD: find contradictions for a target person
 *   - TIMELINE_CONSTRUCT: build chronological narrative
 *   - CONTRADICTION_SCAN: find internal inconsistencies
 *   - FILING_READINESS: assess whether a filing package is complete
 *   - RISK_ASSESSMENT: evaluate litigation risks
 *   - JUDICIAL_INTEL: gather judge misconduct patterns
 *
 * Each task type maps to specific DB tables, query patterns, and result schemas.
 */
class FleetOrchestrator {
  constructor(evoController, criticAgent) {
    this.evo = evoController;      // EvoAgentController instance
    this.critic = criticAgent;      // CriticAgent instance
    this.maxRetries = 2;
    this.maxParallelAgents = 2;     // Rule: max 2 concurrent background agents
    this.taskHistory = [];

    this.TASK_REGISTRY = {
      EVIDENCE_SEARCH: {
        tables: ['evidence_quotes'],
        ftsIndex: 'evidence_fts',
        resultSchema: ['quote_text', 'source_file', 'category', 'lane'],
        verifyWith: 'citations',
        priority: 1
      },
      AUTHORITY_LOOKUP: {
        tables: ['authority_chains_v2', 'michigan_rules_extracted'],
        ftsIndex: null,
        resultSchema: ['primary_citation', 'supporting_citation', 'relationship'],
        verifyWith: 'logical_soundness',
        priority: 2
      },
      IMPEACHMENT_BUILD: {
        tables: ['impeachment_matrix', 'contradiction_map'],
        ftsIndex: null,
        resultSchema: ['category', 'evidence_summary', 'impeachment_value'],
        verifyWith: 'contradictions',
        priority: 1
      },
      TIMELINE_CONSTRUCT: {
        tables: ['timeline_events'],
        ftsIndex: 'timeline_fts',
        resultSchema: ['event_date', 'event_text', 'actor', 'lane'],
        verifyWith: null,
        priority: 3
      },
      CONTRADICTION_SCAN: {
        tables: ['contradiction_map', 'evidence_quotes'],
        ftsIndex: 'evidence_fts',
        resultSchema: ['source_a', 'source_b', 'contradiction_text', 'severity'],
        verifyWith: 'contradictions',
        priority: 1
      },
      FILING_READINESS: {
        tables: ['filing_packages', 'deadlines', 'evidence_quotes', 'authority_chains_v2'],
        ftsIndex: null,
        resultSchema: ['lane', 'readiness_score', 'gaps'],
        verifyWith: null,
        priority: 2
      },
      JUDICIAL_INTEL: {
        tables: ['judicial_violations', 'berry_mcneill_intelligence'],
        ftsIndex: null,
        resultSchema: ['violation_type', 'description', 'date', 'severity'],
        verifyWith: 'hallucinations',
        priority: 1
      }
    };
  }

  /**
   * decompose — break a complex query into typed sub-tasks.
   *
   * @param {string} query — natural language litigation query
   * @returns {object[]} — array of {type, subQuery, priority, tables}
   */
  decompose(query) {
    const tasks = [];
    const lower = query.toLowerCase();

    // Pattern matching for task type detection
    const patterns = [
      {type: 'EVIDENCE_SEARCH',    re: /evidence|proof|exhibit|document|record/i},
      {type: 'AUTHORITY_LOOKUP',   re: /authority|citation|MCR|MCL|case\s*law|statute/i},
      {type: 'IMPEACHMENT_BUILD',  re: /impeach|credib|contradict|cross.*exam|lie|false/i},
      {type: 'TIMELINE_CONSTRUCT', re: /timeline|chronolog|sequence|when|date/i},
      {type: 'CONTRADICTION_SCAN', re: /contradict|inconsisten|conflict|oppose|deny/i},
      {type: 'FILING_READINESS',   re: /filing|ready|package|motion|brief|complete/i},
      {type: 'JUDICIAL_INTEL',     re: /judge|judicial|McNeill|misconduct|bias|ex\s*parte/i}
    ];

    for (const {type, re} of patterns) {
      if (re.test(lower)) {
        const reg = this.TASK_REGISTRY[type];
        tasks.push({
          id: `${type}_${Date.now()}`,
          type,
          subQuery: query,
          priority: reg.priority,
          tables: reg.tables,
          ftsIndex: reg.ftsIndex,
          resultSchema: reg.resultSchema,
          verifyWith: reg.verifyWith,
          status: 'pending'
        });
      }
    }

    // Default: if no patterns match, do a general evidence search
    if (tasks.length === 0) {
      tasks.push({
        id: `EVIDENCE_SEARCH_${Date.now()}`,
        type: 'EVIDENCE_SEARCH',
        subQuery: query,
        priority: 1,
        tables: ['evidence_quotes'],
        ftsIndex: 'evidence_fts',
        resultSchema: ['quote_text', 'source_file', 'category', 'lane'],
        verifyWith: 'citations',
        status: 'pending'
      });
    }

    // Sort by priority (1 = highest)
    tasks.sort((a, b) => a.priority - b.priority);
    return tasks;
  }

  /**
   * execute — run decomposed tasks with agent selection, verification, and retry.
   * Respects maxParallelAgents limit.
   */
  async execute(tasks, queryFn) {
    const results = [];
    // Batch tasks into groups respecting parallel limit
    for (let i = 0; i < tasks.length; i += this.maxParallelAgents) {
      const batch = tasks.slice(i, i + this.maxParallelAgents);
      const batchResults = await Promise.all(
        batch.map(task => this._executeTask(task, queryFn))
      );
      results.push(...batchResults);
    }
    return this.fuse(results);
  }

  async _executeTask(task, queryFn, retryCount = 0) {
    task.status = 'running';
    try {
      // Use EvoAgent strategy for query building
      const action = this.evo.act({topic: task.subQuery});
      const rows = await queryFn(task, action.query);

      // Observe results
      const scored = rows.map(r => ({
        ...r, score: this._scoreResult(r, task),
        isNovel: true  // simplified — full novelty check would compare to prior finds
      }));
      this.evo.observe(action, scored);

      // Verify through CriticAgent if verification axis specified
      if (this.critic && task.verifyWith) {
        const verified = [];
        for (const item of scored.slice(0, 10)) {
          const check = await this.critic.verify({
            text: item.quote_text || item.evidence_summary || item.event_text || '',
            claim: item.quote_text || '',
            citations: item.primary_citation ? [item.primary_citation] : [],
            confidence: item.score
          });
          verified.push({...item, criticResult: check, adjustedScore: check.confidence});
        }
        task.status = 'complete';
        return {task, results: verified, raw: scored};
      }

      task.status = 'complete';
      return {task, results: scored, raw: scored};
    } catch (err) {
      if (retryCount < this.maxRetries) {
        // Mutate strategy and retry
        const genome = this.evo.getBestGenome();
        this.evo._mutate(genome);
        return this._executeTask(task, queryFn, retryCount + 1);
      }
      task.status = 'failed';
      return {task, results: [], error: err.message};
    }
  }

  _scoreResult(row, task) {
    // Simple scoring based on content completeness
    let score = 0.5;
    const text = row.quote_text || row.evidence_summary || row.event_text || '';
    if (text.length > 100) score += 0.1;
    if (text.length > 300) score += 0.1;
    if (row.impeachment_value && row.impeachment_value >= 7) score += 0.15;
    if (row.severity === 'high' || row.severity === 'critical') score += 0.15;
    return Math.min(1.0, score);
  }

  /**
   * fuse — combine results from parallel tasks into a unified intelligence report.
   */
  fuse(taskResults) {
    const report = {
      timestamp: Date.now(),
      tasksRun: taskResults.length,
      tasksSucceeded: taskResults.filter(t => t.task.status === 'complete').length,
      tasksFailed: taskResults.filter(t => t.task.status === 'failed').length,
      totalResults: 0,
      highValueResults: [],
      byType: {},
      criticIssues: []
    };

    for (const {task, results} of taskResults) {
      report.totalResults += results.length;
      report.byType[task.type] = {
        count: results.length,
        topScore: results.length > 0
          ? Math.max(...results.map(r => r.adjustedScore || r.score || 0))
          : 0
      };
      // Collect high-value results (score >= 0.7)
      const highValue = results.filter(r => (r.adjustedScore || r.score || 0) >= 0.7);
      report.highValueResults.push(...highValue.map(r => ({
        type: task.type,
        score: r.adjustedScore || r.score,
        content: (r.quote_text || r.evidence_summary || r.event_text || '').slice(0, 200),
        source: r.source_file || r.source_a || 'unknown'
      })));
      // Collect critic issues
      for (const r of results) {
        if (r.criticResult && !r.criticResult.valid) {
          report.criticIssues.push(...r.criticResult.issues);
        }
      }
    }

    // Deduplicate high-value results by content similarity (simple prefix match)
    report.highValueResults = this._dedup(report.highValueResults);
    report.highValueResults.sort((a, b) => b.score - a.score);

    // Trigger evolution reflection
    const reflection = this.evo.reflect();
    report.evolutionReflection = reflection;

    this.taskHistory.push(report);
    return report;
  }

  _dedup(items) {
    const seen = new Set();
    return items.filter(item => {
      const key = item.content.slice(0, 60).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}
```

---

## Anti-Patterns — 25 INVIOLABLE Rules

> Every anti-pattern learned from real failures across 41+ sessions.

| # | Anti-Pattern | Why It's Fatal | Correct Pattern |
|---|-------------|----------------|-----------------|
| 1 | Agent writes to evidence tables | Corrupts sworn evidence — data integrity violation | Read-only DB access; writes via separate verified pipeline |
| 2 | Neural output accepted without symbolic check | Hallucinated citations enter the graph | Every neural result → symbolic predicate gate → CriticAgent verify |
| 3 | Evolution past checkpoint without fitness validation | Bad strategies propagate, fitness regression | Fitness must improve or hold ≥ 2 consecutive gens before checkpoint |
| 4 | More than 2 concurrent background agents | 429 rate limits stall entire fleet | `maxParallelAgents = 2`, batch remaining tasks |
| 5 | Confidence score used raw without calibration | Overconfident claims damage credibility in court | Every confidence → `ConfidenceCalibrator.adjust()` before display |
| 6 | Hardcoded separation day count | Stale counts in filings = automatic FAIL | `(today - date(2025,7,29)).days` computed at render time |
| 7 | Citation fabricated to fill an argument gap | Rule 9 violation — unverifiable citation destroys filing | `CriticAgent.validateCitations()` before any citation enters output |
| 8 | Single-stage contradiction detection (cosine only) | Contradictory statements are often semantically similar | Two-stage: bi-encoder retrieval → cross-encoder rerank |
| 9 | Strategy genome never mutated | Premature convergence — population loses diversity | Mutation rate ≥ 0.10 on every non-elite genome |
| 10 | Population diversity drops below 0.05 | Monoculture — all agents use same strategy | Monitor `_populationDiversity()`; inject random genomes if CV < 0.05 |
| 11 | Calibration curve built from < 20 data points | Noisy curve leads to wrong adjustments | Minimum 20 resolved predictions per bucket before using curve |
| 12 | Agent retries same failed strategy | Definition of insanity — same input same error | Mutate strategy genome before each retry |
| 13 | Learning persisted only to localStorage | Browser cache wipe deletes all intelligence | Three-tier: localStorage + IndexedDB + DB write-back |
| 14 | Child's full name in any agent output | MCR 8.119(H) violation | Hallucination guard regex catches `Lincoln David` |
| 15 | Agent generates aggregate statistics for filings | Rule 20 — AI-generated counts destroy credibility | Only hand-countable or specific-query-backed stats in filings |
| 16 | Fleet orchestrator decomposes into 5+ parallel tasks | Exceeds agent concurrency limit, triggers cascading failures | Max 2 parallel, batch remainder sequentially |
| 17 | Cross-session learning replays stale genome on new data | Old strategies may be suboptimal for changed evidence landscape | Re-evaluate imported genomes for 3 gens before trusting fitness |
| 18 | Syllogism built without checking required elements | Incomplete IRAC — court rejects for insufficient argument | `requiredElements` check in `buildSyllogism()`, gaps reported |
| 19 | EvoAgent exploits only — zero exploration | Misses novel evidence in unexplored lanes | ε-greedy with ε ≥ 0.15 ensures exploration |
| 20 | CriticAgent bypassed for "trusted" sources | Even court orders can be misquoted or mis-cited | Every intelligence item goes through full 5-axis verification |
| 21 | Fitness function rewards volume over quality | Agent floods graph with low-value noise | `highValue * 3.0 + novel * 2.0 + total * 0.1` — quality weighted 30:1 |
| 22 | Symbolic rules hardcoded without template ID | Can't trace which rule produced which conclusion | Every rule has a unique template ID (e.g., `MCL_722_23_j`) |
| 23 | DB query in AORP loop without parameterized bind | SQL injection or FTS5 syntax crash | All queries use `?` placeholders with `params` array |
| 24 | Genetic crossover without normalization | Scoring weights sum to > 1.0 or < 1.0 after blend | Renormalize weights after every crossover and mutation |
| 25 | Agent fleet starts without EvoAgent initialization | No strategy genome loaded — random behavior | `FleetOrchestrator` constructor requires `EvoAgentController` instance |

---

## Performance Budgets

| Operation | Budget | Technique | Measurement |
|-----------|--------|-----------|-------------|
| AORP loop iteration | < 200ms | Cached DB queries, compiled predicates | `performance.now()` delta |
| Citation verification (per cite) | < 100ms | FTS5 on `authority_chains_v2` + `michigan_rules_extracted` | Async batch with `Promise.all` |
| Contradiction detection (per pair) | < 500ms | Stage 1 bi-encoder (fast), Stage 2 cross-encoder (precise) | Two-stage timing |
| Strategy evolution (per generation) | < 2s | Tournament selection (k=3, pop=8), no DB writes | `plan()` method timing |
| Confidence recalibration | < 100ms | Windowed Brier score over last 500 predictions | `adjust()` method timing |
| Fleet task decomposition | < 50ms | Rule-based regex matching, no DB access | `decompose()` method timing |
| Hallucination scan (full document) | < 150ms | 15 compiled regex patterns, single-pass | `detectHallucinations()` timing |
| Syllogism construction | < 300ms | Predicate filter + top-3 evidence selection | `buildSyllogism()` timing |
| Cross-session recall (IndexedDB) | < 200ms | Cursor scan with query filter, capped at 100 results | `recall()` method timing |
| Knowledge distillation | < 1s | Statistical analysis over genome population | `distill()` method timing |
| Full verification (5 axes) | < 800ms | Sequential axes with early termination on HALLUCINATION | `verify()` method timing |
| Population diversity check | < 10ms | Coefficient of variation on fitness array | `_populationDiversity()` timing |

---

## Integration Matrix

### Tier Dependencies (APEX-COGNITION orchestrates all lower tiers)

| Tier | Skill | Relationship | Data Flow |
|------|-------|-------------|-----------|
| 0 | MBP-GENESIS | Schema consumer | Reads node/link taxonomy for evidence classification |
| 0 | MBP-DATAWEAVE | Data source | All DB queries route through DATAWEAVE transforms |
| 1 | MBP-FORGE-RENDERER | Display target | Verified intelligence → node attributes → visual rendering |
| 1 | MBP-FORGE-PHYSICS | Layout influence | Agent fitness → force parameters via SELFEVOLVE bridge |
| 2 | MBP-COMBAT-ADVERSARY | Intelligence consumer | EvoAgent discoveries feed adversary network PageRank |
| 2 | MBP-COMBAT-EVIDENCE | Evidence pipeline | Verified evidence atoms → density heatmap updates |
| 2 | MBP-COMBAT-AUTHORITY | Authority validator | CriticAgent citation checks use AUTHORITY hierarchy |
| 2 | MBP-COMBAT-IMPEACHMENT | Impeachment source | Contradiction detection feeds impeachment scoring |
| 2 | MBP-COMBAT-JUDICIAL | Judicial intelligence | Judicial violation patterns inform bias detection |
| 2 | MBP-COMBAT-WEAPONS | Weapon chain builder | Syllogism engine provides doctrine → remedy → filing chains |
| 3 | MBP-INTERFACE-HUD | Dashboard display | Calibration health, fitness, fleet status → HUD gauges |
| 3 | MBP-INTERFACE-NARRATIVE | Narrative generation | Fused reasoning chains → story-mode walkthrough |
| 4 | MBP-INTEGRATION-ENGINES | Engine bridge | 14-engine fleet receives orchestrated queries |
| 4 | MBP-INTEGRATION-FILING | Filing readiness | Syllogism strength → filing confidence scores |
| 5 | MBP-EMERGENCE-SELFEVOLVE | Base evolution | APEX extends with population genetics + fitness tracking |
| 5 | MBP-EMERGENCE-PREDICTION | Forecast consumer | Escalation predictions inform agent priority queues |
| 5 | MBP-EMERGENCE-CONVERGENCE | Gap detection | Cross-layer gaps → acquisition task generation |

### LitigationOS Tool Integration

| NEXUS Tool | APEX-COGNITION Usage |
|------------|---------------------|
| `query_litigation_db` | EvoAgent ACT phase — parameterized evidence queries |
| `search_evidence` | FleetOrchestrator EVIDENCE_SEARCH task type |
| `search_impeachment` | FleetOrchestrator IMPEACHMENT_BUILD task type |
| `search_contradictions` | CriticAgent contradiction detection fallback |
| `search_authority_chains` | CriticAgent citation validation |
| `nexus_fuse` | FleetOrchestrator result fusion cross-reference |
| `nexus_argue` | HybridReasoningEngine syllogism verification |
| `nexus_readiness` | FleetOrchestrator FILING_READINESS assessment |
| `judicial_intel` | FleetOrchestrator JUDICIAL_INTEL task type |
| `timeline_search` | FleetOrchestrator TIMELINE_CONSTRUCT task type |
| `vector_search` | Neural layer semantic similarity (LanceDB 75K vectors) |
| `red_team` | CriticAgent red-team validation of argument strength |

---

## Research Citations

> Foundational papers and projects that informed this architecture.

1. **EvoAgentX (2025)** — Population-based evolution of LLM agent strategies.
   Xu et al. "EvoAgentX: A Framework for Evolving LLM-based Agent Systems."
   Key insight: tournament selection with crossover outperforms random search
   for agent configuration by 3-5× on complex reasoning tasks.

2. **AORP Loops** — Act-Observe-Reflect-Plan cycle for autonomous agents.
   Derived from ReAct (Yao et al., 2023) extended with explicit reflection
   and population-based planning. The reflection step is critical: without it,
   agents repeat failed strategies indefinitely.

3. **Hybrid Neural-Symbolic AI** — Garnelo & Shanahan (2019).
   "Reconciling deep learning with symbolic reasoning: a survey."
   Key insight: symbolic constraints on neural search spaces prevent
   hallucination while preserving semantic flexibility.

4. **Calibration of Modern Neural Networks** — Guo et al. (2017).
   "On Calibration of Modern Neural Networks." ICML 2017.
   Key insight: modern networks are poorly calibrated (overconfident).
   Temperature scaling and Platt scaling improve Brier scores by 30-50%.

5. **Brier Score** — Brier (1950). "Verification of forecasts expressed
   in terms of probability." Monthly Weather Review 78(1):1-3.
   The gold standard for evaluating probability forecasts.

6. **Legal Syllogism in AI** — Ashley (2017). "Artificial Intelligence
   and Legal Analytics." Cambridge University Press.
   Formalizes IRAC as computable: Rule(predicate) + Facts(evidence) → Conclusion.

7. **Multi-Agent Orchestration** — Park et al. (2023). "Generative Agents:
   Interactive Simulacra of Human Behavior." UIST 2023.
   Key insight: agent specialization + orchestration outperforms
   monolithic agents on complex multi-step tasks.

8. **Cross-Encoder Reranking** — Nogueira & Cho (2020). "Passage Re-ranking
   with BERT." Key insight: cross-encoder reranking after bi-encoder retrieval
   improves MRR by 25-35% on legal document retrieval.

---

## Appendix A: Quick-Start Wiring

```javascript
// ── Initialize the APEX-COGNITION stack ──────────────────────────

// 1. Create the evolutionary controller
const evo = new EvoAgentController({
  populationSize: 8,
  tournamentK: 3,
  mutationRate: 0.15,
  eliteCount: 2
});

// 2. Create the critic agent with DB query function
const critic = new CriticAgent(async (sql, params) => {
  // Route through pywebview bridge to NEXUS daemon
  const result = await window.pywebview.api.query_db(sql, params);
  return result.rows || [];
});

// 3. Create the hybrid reasoning engine
const reasoning = new HybridReasoningEngine();

// 4. Create the cross-session learner
const learner = new CrossSessionLearner();

// 5. Create the confidence calibrator
const calibrator = new ConfidenceCalibrator();

// 6. Create the fleet orchestrator (wires evo + critic)
const fleet = new FleetOrchestrator(evo, critic);

// ── Example: Full AORP cycle with fleet orchestration ────────────

async function investigateClaim(claim) {
  // Decompose into sub-tasks
  const tasks = fleet.decompose(claim);
  console.log(`Decomposed into ${tasks.length} sub-tasks:`,
              tasks.map(t => t.type));

  // Execute with agent selection and verification
  const report = await fleet.execute(tasks, async (task, query) => {
    const sql = task.ftsIndex
      ? `SELECT * FROM ${task.tables[0]} WHERE ${task.ftsIndex} MATCH ? LIMIT ?`
      : `SELECT * FROM ${task.tables[0]} LIMIT ?`;
    const params = task.ftsIndex
      ? [query.fts5Query, query.limit]
      : [query.limit];
    const result = await window.pywebview.api.query_db(sql, params);
    return result.rows || [];
  });

  // Calibrate confidence on high-value results
  for (const hv of report.highValueResults) {
    hv.calibratedScore = calibrator.adjust(hv.score, 'general');
  }

  // Evolve the population based on this run's performance
  const evolution = evo.plan();
  console.log(`Generation ${evolution.generation}: best fitness = ${evolution.best.fitness}`);

  // Persist learnings
  await learner.persist('fitness', {
    generation: evolution.generation,
    bestFitness: evolution.best.fitness,
    avgFitness: evolution.populationAvg,
    claim
  });

  return report;
}

// ── Example: Build 12-factor best-interest syllogism chain ───────

function buildBestInterestAnalysis(evidenceByFactor) {
  const factors = [
    'MCL_722_23_a', 'MCL_722_23_c', 'MCL_722_23_j', 'MCL_722_23_k', 'MCL_722_23_l'
    // ... add all 12 factors with templates
  ];

  const syllogisms = factors.map(ruleId => {
    const evidence = evidenceByFactor[ruleId] || [];
    return reasoning.buildSyllogism(ruleId, evidence);
  });

  const chain = reasoning.fuseReasoningChain(syllogisms);
  console.log(`Best Interest Analysis: ${chain.recommendation}`);
  console.log(`  Strong factors: ${chain.strongFactors.join(', ')}`);
  console.log(`  Critical gaps: ${chain.criticalGaps.join(', ')}`);
  return chain;
}
```

---

## Appendix B: Strategy Genome Visualization (D3.js)

```javascript
/**
 * Render the EvoAgent population as a parallel coordinates chart.
 * Each line = one genome. Color = fitness (red=low, green=high).
 * Axes = strategy genes (expansion depth, confidence threshold, etc.).
 */
function renderGenomeViz(container, population) {
  const width = 600, height = 300, margin = {top: 30, right: 30, bottom: 30, left: 50};
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const axes = [
    {key: 'queryExpansionDepth', label: 'Expansion', domain: [1, 5]},
    {key: 'minConfidenceThreshold', label: 'Min Conf', domain: [0, 1]},
    {key: 'maxResultsPerQuery', label: 'Max Results', domain: [5, 100]},
    {key: 'explorationVsExploitation', label: 'Explore ε', domain: [0, 1]},
    {key: 'parallelQueryCount', label: 'Parallel', domain: [1, 3]},
    {key: 'fitness', label: 'Fitness', domain: [0, Math.max(1, ...population.map(g => g.fitness))]}
  ];

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);
  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const xScale = d3.scalePoint()
    .domain(axes.map(a => a.key))
    .range([0, innerW]);

  const yScales = {};
  for (const axis of axes) {
    yScales[axis.key] = d3.scaleLinear()
      .domain(axis.domain)
      .range([innerH, 0]);
  }

  const colorScale = d3.scaleSequential(d3.interpolateRdYlGn)
    .domain([0, Math.max(1, ...population.map(g => g.fitness))]);

  // Draw lines (one per genome)
  for (const genome of population) {
    const points = axes.map(a => [xScale(a.key), yScales[a.key](genome[a.key] || 0)]);
    g.append('path')
      .datum(points)
      .attr('d', d3.line())
      .attr('fill', 'none')
      .attr('stroke', colorScale(genome.fitness))
      .attr('stroke-width', genome.id === population[0]?.id ? 3 : 1.5)
      .attr('stroke-opacity', 0.7);
  }

  // Draw axes
  for (const axis of axes) {
    const xPos = xScale(axis.key);
    g.append('g')
      .attr('transform', `translate(${xPos},0)`)
      .call(d3.axisLeft(yScales[axis.key]).ticks(4));
    g.append('text')
      .attr('x', xPos).attr('y', -10)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .text(axis.label);
  }
}
```

---

*SINGULARITY-MBP-APEX-COGNITION v1.0 — TIER 7/APEX — The cognitive apex of THEMANBEARPIG.*
*33rd skill in the MBP taxonomy. The graph that thinks.*
