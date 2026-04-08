"""
Predictive Litigation Engine — Uses scikit-learn GradientBoosting and statistical
models to predict judicial behavior, adversary actions, and filing outcomes.

Falls back gracefully to frequency-based statistical models if sklearn unavailable.
"""
import sys
import os
import sqlite3
import pickle
import math
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, r"C:\Users\andre\LitigationOS")

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import cross_val_score
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "litigation_context.db"
)
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


class PredictiveEngine:
    """Predictive litigation intelligence using ML and statistical models."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or DB_PATH
        self._conn = None
        self._models = {}
        os.makedirs(MODELS_DIR, exist_ok=True)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _table_has_column(self, table: str, column: str) -> bool:
        cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info([{table}])").fetchall()}
        return column in cols

    def _safe_query(self, sql: str, params=()) -> list:
        try:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        except sqlite3.OperationalError:
            return []

    # ─── JUDICIAL VIOLATION PREDICTION ─────────────────────────────

    def build_judicial_model(self) -> dict:
        """Build a model predicting future judicial violations by type.

        Uses GradientBoostingClassifier if sklearn available, else frequency-based.
        Features: violation_type counts, temporal patterns, severity scores.
        """
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(judicial_violations)").fetchall()}
        if not cols:
            return {"error": "judicial_violations table not found"}

        has_date = "date_occurred" in cols
        has_severity = "severity" in cols
        has_type = "violation_type" in cols

        rows = self._safe_query("SELECT * FROM judicial_violations")
        if not rows:
            return {"error": "No judicial violations data", "row_count": 0}

        type_counts = Counter()
        monthly_counts = defaultdict(lambda: Counter())
        severity_by_type = defaultdict(list)

        for row in rows:
            vtype = row.get("violation_type", "unknown") or "unknown"
            type_counts[vtype] += 1

            if has_date and row.get("date_occurred"):
                try:
                    dt = row["date_occurred"][:7]
                    monthly_counts[dt][vtype] += 1
                except (TypeError, IndexError):
                    pass

            if has_severity and row.get("severity"):
                try:
                    sev = float(row["severity"]) if row["severity"] else 0
                    severity_by_type[vtype].append(sev)
                except (ValueError, TypeError):
                    pass

        total = sum(type_counts.values())
        type_probabilities = {k: round(v / total, 4) for k, v in type_counts.most_common()}

        avg_severity = {}
        for vtype, sevs in severity_by_type.items():
            if sevs:
                avg_severity[vtype] = round(sum(sevs) / len(sevs), 2)

        months_sorted = sorted(monthly_counts.keys())
        trend = {}
        if len(months_sorted) >= 2:
            for vtype in type_counts:
                counts_over_time = [monthly_counts[m].get(vtype, 0) for m in months_sorted]
                if len(counts_over_time) >= 2:
                    recent_half = counts_over_time[len(counts_over_time)//2:]
                    early_half = counts_over_time[:len(counts_over_time)//2]
                    recent_avg = sum(recent_half) / max(len(recent_half), 1)
                    early_avg = sum(early_half) / max(len(early_half), 1)
                    if early_avg > 0:
                        trend[vtype] = round((recent_avg - early_avg) / early_avg, 3)
                    elif recent_avg > 0:
                        trend[vtype] = 1.0

        model_result = {
            "model_type": "statistical_frequency",
            "total_violations": total,
            "unique_types": len(type_counts),
            "type_probabilities": type_probabilities,
            "average_severity": avg_severity,
            "temporal_trend": trend,
            "months_analyzed": len(months_sorted),
        }

        if HAS_SKLEARN and total >= 20:
            model_result = self._build_sklearn_model(rows, model_result, cols)

        predictions = {}
        for vtype, prob in type_probabilities.items():
            trend_factor = 1.0 + trend.get(vtype, 0)
            adjusted_prob = min(prob * trend_factor, 1.0)
            predictions[vtype] = {
                "base_probability": prob,
                "trend_adjustment": trend.get(vtype, 0),
                "predicted_probability": round(adjusted_prob, 4),
                "avg_severity": avg_severity.get(vtype, 0),
                "historical_count": type_counts[vtype],
            }

        model_result["predictions"] = dict(
            sorted(predictions.items(), key=lambda x: x[1]["predicted_probability"], reverse=True)[:10]
        )

        model_path = os.path.join(MODELS_DIR, "judicial_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model_result, f)
        model_result["model_saved"] = model_path

        return model_result

    def _build_sklearn_model(self, rows: list, base_result: dict, cols: set) -> dict:
        """Build sklearn GradientBoosting model from judicial violation data."""
        type_encoder = LabelEncoder()
        all_types = [r.get("violation_type", "unknown") or "unknown" for r in rows]
        encoded_types = type_encoder.fit_transform(all_types)

        features = []
        targets = []
        type_counts_running = Counter()

        for i, row in enumerate(rows):
            vtype = row.get("violation_type", "unknown") or "unknown"
            type_counts_running[vtype] += 1

            feature_vec = [
                type_counts_running[vtype],
                len(type_counts_running),
                sum(type_counts_running.values()),
                float(row.get("severity", 0) or 0),
                i,
            ]

            if "date_occurred" in cols and row.get("date_occurred"):
                try:
                    dt = datetime.fromisoformat(row["date_occurred"][:10])
                    feature_vec.append(dt.month)
                    feature_vec.append(dt.weekday())
                except (ValueError, TypeError):
                    feature_vec.extend([0, 0])
            else:
                feature_vec.extend([0, 0])

            features.append(feature_vec)
            targets.append(encoded_types[i])

        X = np.array(features)
        y = np.array(targets)

        n_classes = len(set(y))
        if n_classes < 2:
            base_result["sklearn_note"] = "Only 1 violation type — classifier needs 2+"
            return base_result

        clf = GradientBoostingClassifier(
            n_estimators=min(100, max(10, len(rows) // 5)),
            max_depth=min(4, max(2, int(math.log2(max(n_classes, 2))))),
            learning_rate=0.1,
            random_state=42,
        )

        try:
            n_cv = min(5, max(2, len(rows) // 10))
            if n_cv >= 2 and len(set(y)) >= 2:
                scores = cross_val_score(clf, X, y, cv=n_cv, scoring="accuracy")
                base_result["cv_accuracy"] = round(float(scores.mean()), 4)
                base_result["cv_std"] = round(float(scores.std()), 4)
        except Exception:
            pass

        clf.fit(X, y)

        last_features = X[-1:].copy()
        last_features[0][0] += 1
        last_features[0][2] += 1
        last_features[0][4] += 1

        probas = clf.predict_proba(last_features)[0]
        class_names = type_encoder.inverse_transform(range(len(probas)))
        sklearn_predictions = {
            name: round(float(p), 4)
            for name, p in sorted(zip(class_names, probas), key=lambda x: x[1], reverse=True)[:10]
        }

        model_path = os.path.join(MODELS_DIR, "judicial_sklearn.pkl")
        with open(model_path, "wb") as f:
            pickle.dump({"classifier": clf, "encoder": type_encoder}, f)

        base_result["model_type"] = "sklearn_gradient_boosting"
        base_result["sklearn_predictions"] = sklearn_predictions
        base_result["sklearn_model_saved"] = model_path
        base_result["feature_importances"] = {
            name: round(float(imp), 4)
            for name, imp in zip(
                ["type_freq", "unique_types", "total_count", "severity", "sequence", "month", "weekday"],
                clf.feature_importances_,
            )
        }

        return base_result

    # ─── ADVERSARY BEHAVIOR PREDICTION ─────────────────────────────

    def predict_adversary_behavior(self, actor_name: str) -> dict:
        """Predict most likely next actions for an adversary using Markov chains.

        Builds a first-order Markov chain from event sequences where state = event
        category and transitions = observed sequential pairs.
        """
        events = self._safe_query(
            """SELECT event_date, event_description, category, lane
               FROM timeline_events
               WHERE actors LIKE ? OR event_description LIKE ?
               ORDER BY event_date ASC, id ASC""",
            (f"%{actor_name}%", f"%{actor_name}%"),
        )

        quotes = self._safe_query(
            """SELECT category, source_file, created_at
               FROM evidence_quotes
               WHERE quote_text LIKE ? OR source_file LIKE ?
               ORDER BY created_at ASC""",
            (f"%{actor_name}%", f"%{actor_name}%"),
        )

        if not events and not quotes:
            return {
                "actor": actor_name,
                "error": f"No events or evidence found for '{actor_name}'",
                "events_found": 0,
            }

        categories = []
        for ev in events:
            cat = ev.get("category") or "unknown"
            categories.append(cat)

        for q in quotes:
            cat = q.get("category") or "evidence"
            categories.append(cat)

        cat_counts = Counter(categories)
        total_events = len(categories)

        transitions = defaultdict(Counter)
        for i in range(len(categories) - 1):
            transitions[categories[i]][categories[i + 1]] += 1

        transition_probs = {}
        for state, next_counts in transitions.items():
            total_from_state = sum(next_counts.values())
            transition_probs[state] = {
                next_state: round(count / total_from_state, 4)
                for next_state, count in next_counts.most_common()
            }

        last_state = categories[-1] if categories else "unknown"
        if last_state in transition_probs:
            next_predictions = transition_probs[last_state]
        else:
            next_predictions = {k: round(v / total_events, 4) for k, v in cat_counts.most_common(5)}

        top_5 = sorted(next_predictions.items(), key=lambda x: x[1], reverse=True)[:5]

        recent_events = events[-10:] if events else []
        recent_trend = Counter(ev.get("category", "unknown") for ev in recent_events)

        date_spans = []
        for ev in events:
            if ev.get("event_date"):
                try:
                    date_spans.append(ev["event_date"][:10])
                except (TypeError, IndexError):
                    pass

        escalation_indicator = 0.0
        if len(date_spans) >= 4:
            recent_dates = date_spans[len(date_spans)//2:]
            early_dates = date_spans[:len(date_spans)//2]
            recent_span = len(set(recent_dates))
            early_span = len(set(early_dates))
            if early_span > 0:
                escalation_indicator = round((recent_span - early_span) / early_span, 3)

        return {
            "actor": actor_name,
            "total_events": total_events,
            "unique_categories": len(cat_counts),
            "category_distribution": dict(cat_counts.most_common(10)),
            "current_state": last_state,
            "predicted_next_actions": [
                {"action": action, "probability": prob, "confidence": "high" if prob > 0.3 else "medium" if prob > 0.15 else "low"}
                for action, prob in top_5
            ],
            "transition_matrix_size": len(transition_probs),
            "recent_trend": dict(recent_trend.most_common(5)),
            "escalation_indicator": escalation_indicator,
            "escalation_assessment": (
                "ESCALATING" if escalation_indicator > 0.3
                else "STABLE" if abs(escalation_indicator) <= 0.3
                else "DE-ESCALATING"
            ),
        }

    # ─── FILING OUTCOME PREDICTION ─────────────────────────────────

    def predict_filing_outcome(self, filing_lane: str) -> dict:
        """Predict filing outcome using Bayesian probability.

        P(success | lane, judge) based on historical timeline events and
        filing outcomes from the case record.
        """
        outcome_events = self._safe_query(
            """SELECT event_date, event_description, category, lane
               FROM timeline_events
               WHERE lane = ? OR lane IS NULL
               ORDER BY event_date ASC""",
            (filing_lane,),
        )

        success_keywords = frozenset({
            "granted", "sustained", "approved", "ordered", "modified",
            "won", "favorable", "accepted", "relief granted",
        })
        failure_keywords = frozenset({
            "denied", "dismissed", "overruled", "rejected", "lost",
            "unfavorable", "quashed", "struck", "sanctions",
        })

        lane_events = [e for e in outcome_events if e.get("lane") == filing_lane]
        all_events = outcome_events

        successes_lane = 0
        failures_lane = 0
        successes_all = 0
        failures_all = 0

        for ev in lane_events:
            desc = (ev.get("event_description") or "").lower()
            if any(kw in desc for kw in success_keywords):
                successes_lane += 1
            elif any(kw in desc for kw in failure_keywords):
                failures_lane += 1

        for ev in all_events:
            desc = (ev.get("event_description") or "").lower()
            if any(kw in desc for kw in success_keywords):
                successes_all += 1
            elif any(kw in desc for kw in failure_keywords):
                failures_all += 1

        total_lane = successes_lane + failures_lane
        total_all = successes_all + failures_all

        alpha, beta = 1, 1
        if total_lane > 0:
            p_success = (successes_lane + alpha) / (total_lane + alpha + beta)
        elif total_all > 0:
            p_success = (successes_all + alpha) / (total_all + alpha + beta)
        else:
            p_success = 0.5

        if total_lane > 0:
            n = total_lane
            std_dev = math.sqrt(p_success * (1 - p_success) / n)
            ci_lower = max(0, p_success - 1.96 * std_dev)
            ci_upper = min(1, p_success + 1.96 * std_dev)
        else:
            ci_lower = 0.1
            ci_upper = 0.9

        lane_labels = {
            "A": "Custody (14th Circuit — McNeill)",
            "B": "Housing (14th Circuit — Hoopes, DISMISSED)",
            "C": "Federal §1983 (WDMI)",
            "D": "PPO (14th Circuit — McNeill)",
            "E": "Judicial Misconduct (JTC/MSC)",
            "F": "Appellate (COA 366810)",
        }

        risk_factors = []
        if filing_lane in ("A", "D"):
            risk_factors.append("Same judge (McNeill) — documented 85% adverse ruling rate for Father")
        if filing_lane == "B":
            risk_factors.append("Case dismissed with prejudice — refiling unlikely to succeed")
        if filing_lane == "E":
            risk_factors.append("JTC complaints rarely result in removal — but create public record")
        if filing_lane == "F":
            risk_factors.append("Appellate review is de novo for legal issues — best venue for reversal")
        if filing_lane == "C":
            risk_factors.append("Federal forum — fresh eyes, no local cartel influence")

        return {
            "filing_lane": filing_lane,
            "lane_description": lane_labels.get(filing_lane, f"Lane {filing_lane}"),
            "probability_of_success": round(p_success, 4),
            "confidence_interval": {
                "lower": round(ci_lower, 4),
                "upper": round(ci_upper, 4),
                "confidence_level": "95%",
            },
            "historical_basis": {
                "lane_successes": successes_lane,
                "lane_failures": failures_lane,
                "lane_total": total_lane,
                "all_successes": successes_all,
                "all_failures": failures_all,
                "all_total": total_all,
            },
            "data_quality": "strong" if total_lane >= 10 else "moderate" if total_lane >= 3 else "weak — using prior",
            "risk_factors": risk_factors,
            "recommendation": (
                "FAVORABLE — historical data supports filing"
                if p_success > 0.6
                else "NEUTRAL — outcome uncertain, consider strategy strengthening"
                if p_success > 0.4
                else "UNFAVORABLE — consider alternative venue or approach"
            ),
        }

    # ─── COMPREHENSIVE PREDICTIONS REPORT ──────────────────────────

    def get_predictions_report(self) -> dict:
        """Run all prediction models and return comprehensive results."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "sklearn_available": HAS_SKLEARN,
        }

        print("  Building judicial violation model...")
        report["judicial_model"] = self.build_judicial_model()

        print("  Predicting adversary behavior (Emily A. Watson)...")
        report["adversary_watson"] = self.predict_adversary_behavior("Watson")

        print("  Predicting adversary behavior (McNeill)...")
        report["adversary_mcneill"] = self.predict_adversary_behavior("McNeill")

        print("  Predicting filing outcomes per lane...")
        report["filing_outcomes"] = {}
        for lane in ["A", "B", "C", "D", "E", "F"]:
            report["filing_outcomes"][lane] = self.predict_filing_outcome(lane)

        total_violations = report["judicial_model"].get("total_violations", 0)
        watson_events = report["adversary_watson"].get("total_events", 0)
        mcneill_events = report["adversary_mcneill"].get("total_events", 0)

        report["summary"] = {
            "total_data_points": total_violations + watson_events + mcneill_events,
            "judicial_violations_analyzed": total_violations,
            "watson_events_analyzed": watson_events,
            "mcneill_events_analyzed": mcneill_events,
            "highest_risk_lane": max(
                report["filing_outcomes"].items(),
                key=lambda x: 1 - x[1].get("probability_of_success", 0.5)
            )[0] if report["filing_outcomes"] else "unknown",
            "best_lane_for_filing": max(
                report["filing_outcomes"].items(),
                key=lambda x: x[1].get("probability_of_success", 0.5)
            )[0] if report["filing_outcomes"] else "unknown",
        }

        report_path = os.path.join(MODELS_DIR, "predictions_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        report["report_saved"] = report_path

        return report


if __name__ == "__main__":
    engine = PredictiveEngine()
    print("PredictiveEngine initialized")
    print(f"DB: {engine._db_path}")
    print(f"sklearn available: {HAS_SKLEARN}")
    print()

    report = engine.get_predictions_report()
    print("\n" + "=" * 70)
    print("PREDICTIONS REPORT SUMMARY")
    print("=" * 70)
    print(f"Data points analyzed: {report['summary']['total_data_points']}")
    print(f"Best lane for filing: {report['summary']['best_lane_for_filing']}")
    print(f"Highest risk lane: {report['summary']['highest_risk_lane']}")

    jm = report.get("judicial_model", {})
    print(f"\nJudicial model type: {jm.get('model_type', 'N/A')}")
    if jm.get("predictions"):
        print("Top predicted violation types:")
        for vtype, info in list(jm["predictions"].items())[:5]:
            print(f"  {vtype}: {info['predicted_probability']:.1%} "
                  f"(count={info['historical_count']}, severity={info['avg_severity']})")

    for actor_key in ["adversary_watson", "adversary_mcneill"]:
        adv = report.get(actor_key, {})
        print(f"\n{adv.get('actor', 'Unknown')} ({adv.get('total_events', 0)} events):")
        print(f"  Escalation: {adv.get('escalation_assessment', 'N/A')}")
        for pred in adv.get("predicted_next_actions", [])[:3]:
            print(f"  -> {pred['action']}: {pred['probability']:.1%} ({pred['confidence']})")

    print("\nFiling outcomes:")
    for lane, outcome in report.get("filing_outcomes", {}).items():
        print(f"  Lane {lane}: {outcome['probability_of_success']:.1%} "
              f"[{outcome['confidence_interval']['lower']:.1%}-{outcome['confidence_interval']['upper']:.1%}] "
              f"— {outcome['recommendation']}")

    print(f"\nReport saved: {report.get('report_saved', 'N/A')}")
    engine.close()
