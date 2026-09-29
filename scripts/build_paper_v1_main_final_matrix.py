from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPLICATES = tuple(f"M{i:02d}" for i in range(1, 11))
ARMS = ("F", "P", "R", "L", "L0")
PLANNED_CONTRASTS = (
    ("R-F", "R", "F"),
    ("P-F", "P", "F"),
    ("R-P", "R", "P"),
    ("L-R", "L", "R"),
    ("L-L0", "L", "L0"),
    ("L-F", "L", "F"),
    ("L-P", "L", "P"),
)


class FinalMatrixError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def closure_path(root: Path, replicate: str) -> Path:
    return root / replicate / f"PAPER_V1_{replicate}_MAIN_CLOSURE_V2.json"


def validate_closure(replicate: str, path: Path, obj: dict[str, Any]) -> None:
    if obj.get("schema") != "paper-v1-main-replicate-closure-v2":
        raise FinalMatrixError(f"{replicate}: closure schema drift")
    if obj.get("decision") != "COMPLETE_MATCHED_MAIN_REPLICATE_V2":
        raise FinalMatrixError(f"{replicate}: closure not complete")
    if obj.get("replicate_id") != replicate:
        raise FinalMatrixError(f"{replicate}: closure identity drift")
    if obj.get("q0_read") is not False or obj.get("oos_read") is not False:
        raise FinalMatrixError(f"{replicate}: closure firewall drift")

    integ = obj.get("integrity") or {}
    required_integrity = (
        "all_final_resume_states_absent",
        "all_five_ledgers_hash_chain_valid",
        "all_formal_admissions_have_resolved_novelty",
        "all_ledgers_q0_oos_false",
        "all_results_oos_false",
        "all_results_q0_false",
    )
    bad = [k for k in required_integrity if integ.get(k) is not True]
    if bad:
        raise FinalMatrixError(f"{replicate}: closure integrity failed {bad}")

    matched = obj.get("matched_design") or {}
    if int(matched.get("arm_count", -1)) != 5:
        raise FinalMatrixError(f"{replicate}: arm count drift")
    if int(matched.get("epochs_per_arm", -1)) != 16:
        raise FinalMatrixError(f"{replicate}: epoch count drift")
    if int(matched.get("completed_arm_epochs", -1)) != 80:
        raise FinalMatrixError(f"{replicate}: incomplete arm epochs")
    if int(matched.get("total_fixed_search_calls", -1)) != 5120:
        raise FinalMatrixError(f"{replicate}: fixed-search budget drift")

    arms = obj.get("arms") or []
    if [str(x.get("arm")) for x in arms] != list(ARMS):
        raise FinalMatrixError(f"{replicate}: arm order/identity drift")
    for arm in arms:
        if int(arm.get("epochs_complete", -1)) != 16:
            raise FinalMatrixError(f"{replicate}/{arm.get('arm')}: incomplete epochs")
        if int(arm.get("search_calls", -1)) != 1024:
            raise FinalMatrixError(f"{replicate}/{arm.get('arm')}: search budget drift")

    if not path.is_file():
        raise FinalMatrixError(f"{replicate}: closure disappeared during validation")


def arm_row(replicate: str, arm: dict[str, Any]) -> dict[str, Any]:
    charged = int(arm["charged_economic_calls"])
    formal = int(arm["formal_admission_epochs"])
    scoped_new = int(arm["scoped_reference_new_formal_epochs"])
    return {
        "replicate_id": replicate,
        "arm": str(arm["arm"]),
        "search_calls": int(arm["search_calls"]),
        "qualification_calls": int(arm["qualification_calls"]),
        "charged_economic_calls": charged,
        "formal_admissions": formal,
        "scoped_new_admissions": scoped_new,
        "formal_admissions_per_1000_calls": (1000.0 * formal / charged) if charged else 0.0,
        "scoped_new_admissions_per_1000_calls": (1000.0 * scoped_new / charged) if charged else 0.0,
        "within_arm_unique_new_behavior_clusters": int(
            arm.get("within_arm_unique_new_behavior_clusters", 0)
        ),
        "screen8_terminal_visits": int(arm.get("screen8_terminal_visits", 0)),
        "extended24_terminal_visits": int(arm.get("extended24_terminal_visits", 0)),
        "fulltrain_visits": int(arm.get("fulltrain_visits", 0)),
    }


def contrast_vectors(
    rows_by_rep_arm: dict[tuple[str, str], dict[str, Any]],
    metric: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, left, right in PLANNED_CONTRASTS:
        values = []
        for rep in REPLICATES:
            lv = float(rows_by_rep_arm[(rep, left)][metric])
            rv = float(rows_by_rep_arm[(rep, right)][metric])
            values.append(
                {
                    "replicate_id": rep,
                    "left": lv,
                    "right": rv,
                    "difference": lv - rv,
                }
            )
        out[label] = {
            "left_arm": left,
            "right_arm": right,
            "metric": metric,
            "matched_replicate_differences": values,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build the complete Paper V1 matched-replicate endpoint matrix. "
            "Fails closed unless all M01-M10 closure V2 artifacts are present and valid."
        )
    )
    ap.add_argument(
        "--prospective-root",
        type=Path,
        default=Path("artifacts/prospective"),
    )
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    missing = [r for r in REPLICATES if not closure_path(args.prospective_root, r).is_file()]
    if missing:
        raise FinalMatrixError(
            "final matched matrix is sealed until all ten closures exist; missing="
            + ",".join(missing)
        )

    closures: dict[str, dict[str, Any]] = {}
    closure_receipts = []
    arm_rows = []
    execution_heads: set[str] = set()
    for rep in REPLICATES:
        path = closure_path(args.prospective_root, rep)
        obj = load(path)
        validate_closure(rep, path, obj)
        closures[rep] = obj
        execution_heads.update(str(x) for x in (obj.get("scientific_execution_git_heads") or []))
        closure_receipts.append(
            {
                "replicate_id": rep,
                "path": str(path),
                "sha256": sha256(path),
            }
        )
        for arm in obj["arms"]:
            arm_rows.append(arm_row(rep, arm))

    rows_by_rep_arm = {(x["replicate_id"], x["arm"]): x for x in arm_rows}
    if len(rows_by_rep_arm) != 50:
        raise FinalMatrixError("expected exactly 50 replicate-arm rows")

    total_search = sum(int(x["matched_design"]["total_fixed_search_calls"]) for x in closures.values())
    total_qual = sum(int(x["matched_design"]["total_qualification_calls"]) for x in closures.values())
    total_charged = sum(int(x["matched_design"]["total_charged_economic_calls"]) for x in closures.values())
    excluded_infra = sum(
        int(x["matched_design"].get("infrastructure_calls_excluded_from_experimental_budget", 0))
        for x in closures.values()
    )

    result = {
        "schema": "paper-v1-main-final-matched-matrix-v1",
        "decision": "PASS_ALL_TEN_MATCHED_REPLICATE_CLOSURES_ASSEMBLED",
        "inference_status": "RAW_MATCHED_ENDPOINTS_AND_CONTRAST_VECTORS_ONLY",
        "inference_guard": (
            "This artifact intentionally does not invent a confidence-interval, permutation, "
            "bootstrap, or p-value procedure that was not frozen by repository authority."
        ),
        "replicates": list(REPLICATES),
        "arms": list(ARMS),
        "closure_receipts": closure_receipts,
        "scientific_execution_git_heads": sorted(execution_heads),
        "budget": {
            "total_fixed_search_calls": total_search,
            "total_qualification_calls": total_qual,
            "total_charged_economic_calls": total_charged,
            "infrastructure_calls_excluded_from_experimental_budget": excluded_infra,
        },
        "arm_rows": arm_rows,
        "planned_contrasts": {
            "primary_scoped_new_rate_per_1000_calls": contrast_vectors(
                rows_by_rep_arm, "scoped_new_admissions_per_1000_calls"
            ),
            "formal_admission_rate_per_1000_calls": contrast_vectors(
                rows_by_rep_arm, "formal_admissions_per_1000_calls"
            ),
            "qualification_calls": contrast_vectors(rows_by_rep_arm, "qualification_calls"),
        },
        "q0_read": False,
        "oos_read": False,
    }

    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(raw)
        print(
            json.dumps(
                {
                    "decision": result["decision"],
                    "out": str(args.out),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "replicate_arm_rows": len(arm_rows),
                },
                indent=2,
            )
        )
    else:
        print(raw.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FinalMatrixError as exc:
        print(f"FINAL_MATRIX_FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
