from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

from scipy import stats


EXPECTED_DECISION = "PASS_ALL_TEN_MATCHED_REPLICATE_CLOSURES_ASSEMBLED"
EXPECTED_REPLICATES = tuple(f"M{i:02d}" for i in range(1, 11))
EXPECTED_CONTRASTS = ("R-F", "P-F", "R-P", "L-R", "L-L0", "L-F", "L-P")
CONFIRMATORY_CONTRASTS = ("R-F", "R-P", "L-R", "L-L0")
SUPPORTING_CONTRASTS = ("P-F", "L-F", "L-P")
INFERENTIAL_ENDPOINTS = (
    "primary_scoped_new_rate_per_1000_calls",
    "formal_admission_rate_per_1000_calls",
)


class InferenceError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def validate_binding(binding: dict[str, Any]) -> None:
    if binding.get("schema") != "paper-v1-main-inference-binding-v1":
        raise InferenceError("inference binding schema drift")
    if binding.get("decision") != "FROZEN_BEFORE_COMPLETE_M01_M10_MATCHED_RESULTS":
        raise InferenceError("inference binding is not pre-final frozen")
    method = binding.get("method") or {}
    if float(method.get("alpha", -1)) != 0.05:
        raise InferenceError("alpha drift")
    if method.get("effect_estimator") != "ARITHMETIC_MEAN_OF_MATCHED_REPLICATE_DIFFERENCES":
        raise InferenceError("effect estimator drift")
    if method.get("confidence_interval") != "TWO_SIDED_PAIRED_T_INTERVAL_DF_N_MINUS_1":
        raise InferenceError("confidence interval drift")
    if method.get("primary_p_value") != "TWO_SIDED_PAIRED_T_TEST":
        raise InferenceError("primary p-value drift")
    if method.get("robustness_p_value") != "EXACT_TWO_SIDED_SIGN_FLIP_ON_ABSOLUTE_MEAN_ALL_2_POW_N_PATTERNS":
        raise InferenceError("robustness p-value drift")
    if method.get("multiplicity") != "HOLM_STEP_DOWN_ACROSS_ALL_SEVEN_PLANNED_CONTRASTS_WITHIN_EACH_ENDPOINT_FAMILY":
        raise InferenceError("multiplicity drift")


def validate_matrix(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != "paper-v1-main-final-matched-matrix-v1":
        raise InferenceError("final matrix schema drift")
    if matrix.get("decision") != EXPECTED_DECISION:
        raise InferenceError("final matrix is not complete")
    if tuple(matrix.get("replicates") or []) != EXPECTED_REPLICATES:
        raise InferenceError("replicate identity/order drift")
    if matrix.get("q0_read") is not False or matrix.get("oos_read") is not False:
        raise InferenceError("Q0/OOS firewall drift")
    planned = matrix.get("planned_contrasts") or {}
    for endpoint in INFERENTIAL_ENDPOINTS:
        family = planned.get(endpoint)
        if not isinstance(family, dict):
            raise InferenceError(f"missing endpoint family {endpoint}")
        if tuple(family.keys()) != EXPECTED_CONTRASTS:
            raise InferenceError(f"contrast identity/order drift for {endpoint}")
        for label in EXPECTED_CONTRASTS:
            values = family[label].get("matched_replicate_differences") or []
            ids = tuple(str(x.get("replicate_id")) for x in values)
            if ids != EXPECTED_REPLICATES:
                raise InferenceError(f"matched replicate drift for {endpoint}/{label}")
            for row in values:
                left = float(row["left"])
                right = float(row["right"])
                diff = float(row["difference"])
                if not math.isfinite(left) or not math.isfinite(right) or not math.isfinite(diff):
                    raise InferenceError(f"non-finite value for {endpoint}/{label}")
                if not math.isclose(diff, left - right, rel_tol=0.0, abs_tol=1e-12):
                    raise InferenceError(f"difference arithmetic drift for {endpoint}/{label}")


def paired_t_summary(differences: list[float], alpha: float = 0.05) -> dict[str, Any]:
    n = len(differences)
    if n < 2:
        raise InferenceError("paired inference requires n >= 2")
    mean = sum(differences) / n
    variance = sum((x - mean) ** 2 for x in differences) / (n - 1)
    sd = math.sqrt(max(0.0, variance))
    se = sd / math.sqrt(n)
    df = n - 1
    critical = float(stats.t.ppf(1.0 - alpha / 2.0, df))
    if se == 0.0:
        lo = hi = mean
        if mean == 0.0:
            t_stat = 0.0
            p_value = 1.0
        else:
            t_stat = math.copysign(math.inf, mean)
            p_value = 0.0
    else:
        t_stat = mean / se
        p_value = float(2.0 * stats.t.sf(abs(t_stat), df))
        lo = mean - critical * se
        hi = mean + critical * se
    return {
        "n": n,
        "mean_paired_difference": mean,
        "sample_sd_paired_difference": sd,
        "standard_error": se,
        "df": df,
        "t_statistic": t_stat,
        "p_value_unadjusted": p_value,
        "ci_level": 1.0 - alpha,
        "ci_lower": lo,
        "ci_upper": hi,
    }


def exact_sign_flip_p_value(differences: list[float]) -> float:
    n = len(differences)
    observed = abs(sum(differences) / n)
    if observed == 0.0 and all(x == 0.0 for x in differences):
        return 1.0
    extreme = 0
    total = 1 << n
    tolerance = 1e-15
    for signs in itertools.product((-1.0, 1.0), repeat=n):
        statistic = abs(sum(s * d for s, d in zip(signs, differences)) / n)
        if statistic + tolerance >= observed:
            extreme += 1
    return extreme / total


def holm_adjust(raw: dict[str, float]) -> dict[str, float]:
    labels = list(raw)
    ordered = sorted(labels, key=lambda label: (raw[label], labels.index(label)))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, label in enumerate(ordered, start=1):
        candidate = (m - rank + 1) * raw[label]
        running = max(running, candidate)
        adjusted[label] = min(1.0, running)
    return {label: adjusted[label] for label in labels}


def analyze_family(family: dict[str, Any], alpha: float) -> dict[str, Any]:
    results: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for label in EXPECTED_CONTRASTS:
        rows = family[label]["matched_replicate_differences"]
        diffs = [float(x["difference"]) for x in rows]
        summary = paired_t_summary(diffs, alpha=alpha)
        summary["exact_sign_flip_p_value_robustness"] = exact_sign_flip_p_value(diffs)
        summary["matched_replicate_differences"] = [
            {"replicate_id": str(x["replicate_id"]), "difference": float(x["difference"])}
            for x in rows
        ]
        summary["contrast_role"] = (
            "CONFIRMATORY" if label in CONFIRMATORY_CONTRASTS else "SUPPORTING_PLANNED"
        )
        results[label] = summary
        raw_p[label] = float(summary["p_value_unadjusted"])
    adjusted = holm_adjust(raw_p)
    for label in EXPECTED_CONTRASTS:
        results[label]["holm_adjusted_p_value_within_endpoint_family"] = adjusted[label]
        results[label]["reject_at_alpha_after_holm"] = adjusted[label] < alpha
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply the pre-final frozen Paper V1 paired inference procedure to the complete M01-M10 matrix."
    )
    ap.add_argument("--matrix", type=Path, required=True)
    ap.add_argument(
        "--binding",
        type=Path,
        default=Path("protocol/PAPER_V1_MAIN_INFERENCE_BINDING.json"),
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    binding = load(args.binding)
    matrix = load(args.matrix)
    validate_binding(binding)
    validate_matrix(matrix)
    alpha = float(binding["method"]["alpha"])

    planned = matrix["planned_contrasts"]
    endpoint_results = {
        endpoint: analyze_family(planned[endpoint], alpha)
        for endpoint in INFERENTIAL_ENDPOINTS
    }
    result = {
        "schema": "paper-v1-main-inference-v1",
        "decision": "PASS_FROZEN_PAIRED_INFERENCE_APPLIED",
        "binding": {"path": str(args.binding), "sha256": sha256(args.binding)},
        "matrix": {"path": str(args.matrix), "sha256": sha256(args.matrix)},
        "method": binding["method"],
        "endpoint_results": endpoint_results,
        "interpretation_guard": {
            "sign_flip_is_robustness_only": True,
            "holm_uses_primary_p_values_only": True,
            "supporting_contrasts_are_not_promoted_to_confirmatory": True,
            "no_directional_winner_rule": True,
            "no_endpoint_substitution": True,
        },
        "q0_read": False,
        "oos_read": False,
    }
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "out": str(args.out),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "endpoint_families": list(endpoint_results),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
