"""
Module 4 -- ML-based Anomaly & Regression Detector
Module 5 -- Risk-based Prioritization Engine

Module 4 combines two signals:
  * unsupervised  -- IsolationForest over per-response numeric features,
                     catching statistical outliers (e.g. latency blow-ups)
  * supervised    -- RandomForest trained on labelled normal / faulty response
                     records, recognising known defect signatures

Module 5 converts detector output into a ranked P1-P4 action list.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split

from m3_executor import ExecutionResult

FEATURE_NAMES = [
    "status_code",
    "is_server_error",
    "is_client_error",
    "is_success",
    "latency_ms",
    "log_latency",
    "response_size",
    "n_schema_violations",
    "status_unexpected",
    "is_security_probe",
    "echoes_probe_payload",
    "is_json",
]


# ---------------------------------------------------------------------------
def featurize(r: ExecutionResult) -> List[float]:
    """Turns one execution result into a fixed-length numeric feature vector."""
    sc = r.status_code
    echoes = 0.0
    if r.security_probe == "injection" and r.body_preview:
        low = r.body_preview.lower()
        if any(tok in low for tok in ["select ", "drop table", "<script>", "or '1'='1", "/etc/passwd"]):
            echoes = 1.0
    return [
        float(sc),
        1.0 if 500 <= sc < 600 else 0.0,
        1.0 if 400 <= sc < 500 else 0.0,
        1.0 if 200 <= sc < 300 else 0.0,
        float(r.latency_ms),
        float(np.log1p(max(r.latency_ms, 0.0))),
        float(r.response_size),
        float(len(r.schema_violations)),
        0.0 if r.status_as_expected else 1.0,
        1.0 if r.security_probe else 0.0,
        echoes,
        1.0 if "json" in (r.content_type or "").lower() else 0.0,
    ]


def heuristic_label(r: ExecutionResult) -> int:
    """
    Ground-truth-free weak label used to TRAIN the supervised model.

    A response is labelled faulty (1) when it exhibits an objectively wrong
    behaviour relative to the API's own declared contract:
      * a 5xx server error (never a valid contract response)
      * a response that violates the declared success schema
      * a status code outside every declared expectation
      * a security probe that was answered successfully or echoed back
    Note: these are contract violations derived from the spec, NOT from the
    seeded-defect register, which the pipeline never reads.
    """
    if 500 <= r.status_code < 600 and r.status_code != 501:
        return 1
    if r.schema_violations:
        return 1
    if not r.status_as_expected and r.status_code != 501:
        return 1
    if r.security_probe in ("auth-bypass", "bola") and 200 <= r.status_code < 300:
        return 1
    if r.security_probe == "injection" and featurize(r)[10] == 1.0:
        return 1
    return 0


@dataclass
class Finding:
    test_id: str
    endpoint: str
    category: str
    intent: str
    status_code: int
    latency_ms: float
    anomaly_score: float          # 0..1, higher == more anomalous
    supervised_prob: float        # P(faulty) from RandomForest
    isolation_outlier: bool
    label: str                    # regression | security | schema-drift | performance
    evidence: str
    risk_score: float = 0.0
    priority: str = "P4"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnomalyDetector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.iso = IsolationForest(n_estimators=200, contamination=0.25, random_state=seed)
        self.rf = RandomForestClassifier(n_estimators=200, random_state=seed,
                                         class_weight="balanced", min_samples_leaf=1)
        self.metrics: Dict[str, Any] = {}

    # ---------------------------------------------------------------- fit
    def fit(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        X = np.array([featurize(r) for r in results], dtype=float)
        y = np.array([heuristic_label(r) for r in results], dtype=int)

        self.iso.fit(X)

        # Held-out evaluation of the supervised model
        if len(set(y)) > 1 and len(y) >= 12:
            X_tr, X_te, y_tr, y_te = train_test_split(
                X, y, test_size=0.3, random_state=self.seed, stratify=y)
            self.rf.fit(X_tr, y_tr)
            y_pred = self.rf.predict(X_te)
            p, r_, f1, _ = precision_recall_fscore_support(
                y_te, y_pred, average="binary", zero_division=0)
            tn, fp, fn, tp = confusion_matrix(y_te, y_pred, labels=[0, 1]).ravel()
            self.metrics = {
                "precision": round(float(p), 4),
                "recall": round(float(r_), 4),
                "f1": round(float(f1), 4),
                "false_positive_rate": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
                "test_set_size": int(len(y_te)),
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                "train_set_size": int(len(y_tr)),
                "positive_rate": round(float(y.mean()), 4),
            }
            # refit on everything for inference
            self.rf.fit(X, y)
        else:
            self.rf.fit(X, y)
            self.metrics = {"note": "insufficient class balance for held-out evaluation"}

        self.metrics["feature_importance"] = {
            name: round(float(w), 4)
            for name, w in sorted(zip(FEATURE_NAMES, self.rf.feature_importances_),
                                  key=lambda kv: -kv[1])
        }
        return self.metrics

    # ------------------------------------------------------------ predict
    def detect(self, results: List[ExecutionResult]) -> List[Finding]:
        X = np.array([featurize(r) for r in results], dtype=float)
        iso_pred = self.iso.predict(X)                       # -1 outlier, 1 inlier
        iso_raw = self.iso.score_samples(X)
        # normalise isolation score to 0..1 (higher == more anomalous)
        lo, hi = iso_raw.min(), iso_raw.max()
        iso_norm = (hi - iso_raw) / (hi - lo) if hi > lo else np.zeros_like(iso_raw)
        rf_prob = self.rf.predict_proba(X)[:, 1] if len(self.rf.classes_) > 1 \
            else np.zeros(len(results))

        findings: List[Finding] = []
        for r, outlier, isc, prob in zip(results, iso_pred, iso_norm, rf_prob):
            label, evidence = self._classify(r)
            if label is None:
                continue
            findings.append(Finding(
                test_id=r.test_id, endpoint=r.endpoint, category=r.category,
                intent=r.intent, status_code=r.status_code, latency_ms=r.latency_ms,
                anomaly_score=round(float(0.5 * isc + 0.5 * prob), 4),
                supervised_prob=round(float(prob), 4),
                isolation_outlier=bool(outlier == -1),
                label=label, evidence=evidence,
            ))
        return findings

    @staticmethod
    def _classify(r: ExecutionResult) -> Tuple[str | None, str]:
        """Assigns a defect class and a human-readable evidence string."""
        if r.security_probe in ("auth-bypass", "bola") and 200 <= r.status_code < 300:
            kind = "missing authentication" if r.security_probe == "auth-bypass" \
                else "broken object-level authorization"
            return "security", f"Probe succeeded with HTTP {r.status_code} -- {kind}."
        if r.security_probe == "injection" and featurize(r)[10] == 1.0:
            return "security", ("Injection payload reflected in the response body "
                                f"(HTTP {r.status_code}) -- possible information disclosure.")
        if r.status_code == 501:
            return "unimplemented", ("HTTP 501: the specification documents this operation but the "
                                     "server declares it unsupported.")
        if 500 <= r.status_code < 600:
            return "regression", (f"Unhandled server error (HTTP {r.status_code}) "
                                  f"for input described as: {r.intent}.")
        if r.schema_violations:
            return "schema-drift", ("Response violates the declared success schema: "
                                    + "; ".join(r.schema_violations[:3]))
        if not r.status_as_expected:
            return "regression", (f"HTTP {r.status_code} returned, but the contract "
                                  f"declares {r.expected_status} for this request.")
        if r.latency_ms > 1000:
            return "performance", f"Response took {r.latency_ms:.0f} ms (>1000 ms threshold)."
        return None, ""


# ---------------------------------------------------------------------------
#  Module 5 -- Risk-based Prioritization
# ---------------------------------------------------------------------------
class RiskEngine:
    """Ranks findings by business risk, not just by anomaly score."""

    LABEL_WEIGHT = {
        "security": 1.00,
        "regression": 0.70,
        "schema-drift": 0.55,
        "performance": 0.40,
        "unimplemented": 0.30,
    }
    # endpoints matching these fragments are treated as business-critical
    CRITICAL_FRAGMENTS = ("auth", "login", "order", "payment", "token", "admin", "user")

    def __init__(self, critical_fragments: Tuple[str, ...] | None = None):
        self.critical_fragments = critical_fragments or self.CRITICAL_FRAGMENTS

    def endpoint_criticality(self, endpoint: str) -> float:
        low = endpoint.lower()
        if any(f in low for f in self.critical_fragments):
            return 1.0
        if endpoint.startswith(("DELETE", "POST", "PUT", "PATCH")):
            return 0.75            # state-changing operations
        return 0.5

    def score(self, findings: List[Finding], blast_radius: Dict[str, int] | None = None) -> List[Finding]:
        blast_radius = blast_radius or {}
        max_blast = max(blast_radius.values()) if blast_radius else 1

        for f in findings:
            w_label = self.LABEL_WEIGHT.get(f.label, 0.4)
            w_crit = self.endpoint_criticality(f.endpoint)
            w_blast = (blast_radius.get(f.endpoint, 0) / max_blast) if max_blast else 0.0
            raw = (0.45 * w_label
                   + 0.25 * w_crit
                   + 0.20 * f.anomaly_score
                   + 0.10 * w_blast)
            f.risk_score = round(float(raw), 4)
            f.priority = ("P1" if raw >= 0.75 else
                          "P2" if raw >= 0.60 else
                          "P3" if raw >= 0.45 else "P4")

        findings.sort(key=lambda x: (-x.risk_score, x.endpoint, x.test_id))
        return findings
