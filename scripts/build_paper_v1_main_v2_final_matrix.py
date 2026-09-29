from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "protocol" / "PAPER_V1_MAIN_V2_EXECUTION_BINDING.json"
BASE_BUILDER = ROOT / "scripts" / "build_paper_v1_main_final_matrix.py"
EXPECTED_FRESH_HEAD = "50535d2c6406575db5d8fe1f116c67afd71fadc5"
EXPECTED_CARRY = ["M01","M02","M03","M04","M05","M06","M07","M09","M10"]


class V2FinalMatrixError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    return json.loads(text)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_bound_path(raw: str) -> Path:
    p = Path(raw.replace("\\", "/"))
    if p.is_absolute():
        return p
    return ROOT / p


def require_bound_artifact(parent: dict[str, Any], key: str, expected_decision: str | None = None) -> tuple[Path, dict[str, Any]]:
    row = parent[key]
    path = resolve_bound_path(str(row["path"]))
    if not path.is_file():
        raise V2FinalMatrixError(f"missing bound artifact {key}: {path}")
    got = sha(path)
    if got != str(row["sha256"]):
        raise V2FinalMatrixError(f"bound artifact hash drift {key}: {got} != {row['sha256']}")
    obj = load(path)
    if expected_decision is not None and obj.get("decision") != expected_decision:
        raise V2FinalMatrixError(f"bound artifact decision drift {key}: {obj.get('decision')}")
    return path, obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Paper V1 Main V2 final matched matrix with carry-forward authority checks.")
    ap.add_argument("--prospective-root", type=Path, default=ROOT / "artifacts" / "prospective")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if not BINDING.is_file():
        raise V2FinalMatrixError("missing V2 execution binding")
    binding = load(BINDING)
    if binding.get("schema") != "paper-v1-main-v2-execution-binding-v1":
        raise V2FinalMatrixError("V2 binding schema drift")
    if binding.get("decision") != "READY_FOR_M08_FRESH_V2_RERUN_WITH_NINE_REPLICATE_ECONOMIC_PATH_CARRY_FORWARD":
        raise V2FinalMatrixError("V2 binding not launch/final-matrix compatible")
    if binding.get("frozen_before_first_v2_economic_call") is not True or int(binding.get("main_v2_economic_calls_before_binding", -1)) != 0:
        raise V2FinalMatrixError("V2 binding was not frozen before first V2 economic call")

    _, incident = require_bound_artifact(
        binding, "v1_incident", "INVALIDATE_PAPER_V1_MAIN_CONFIRMATORY_FIXED_BUDGET_INFERENCE_NO_RESTART3"
    )
    _, carry = require_bound_artifact(
        binding, "carry_forward", "PASS_NINE_REPLICATE_ECONOMIC_PATH_EQUIVALENCE_M08_FRESH_V2_REQUIRED"
    )
    _, selftest = require_bound_artifact(
        binding, "v2_selftest", "PASS_V2_TOTAL_STATE_MACHINE_NONEXHAUSTED_V1_PARITY"
    )
    if incident.get("q0_read") is not False or incident.get("oos_read") is not False:
        raise V2FinalMatrixError("incident firewall drift")
    if carry.get("q0_read") is not False or carry.get("oos_read") is not False:
        raise V2FinalMatrixError("carry-forward firewall drift")
    if selftest.get("q0_read") is not False or selftest.get("oos_read") is not False:
        raise V2FinalMatrixError("V2 selftest firewall drift")

    carried = list(binding["carry_forward"]["replicates"])
    fresh = list(binding["carry_forward"]["fresh_v2_replicates"])
    if carried != EXPECTED_CARRY or fresh != ["M08"]:
        raise V2FinalMatrixError(f"carry/fresh replicate set drift carried={carried} fresh={fresh}")
    if list(carry.get("carry_forward_replicates") or []) != EXPECTED_CARRY:
        raise V2FinalMatrixError("carry-forward audit replicate set drift")
    if list(carry.get("fresh_v2_replicates") or []) != ["M08"]:
        raise V2FinalMatrixError("carry-forward audit fresh set drift")

    fresh_closure = args.prospective_root / "M08" / "PAPER_V1_M08_MAIN_CLOSURE_V2.json"
    if not fresh_closure.is_file():
        raise V2FinalMatrixError(f"fresh V2 M08 closure not present: {fresh_closure}")
    m08 = load(fresh_closure)
    if m08.get("decision") != "COMPLETE_MATCHED_MAIN_REPLICATE_V2":
        raise V2FinalMatrixError("M08 closure is not complete")
    heads = sorted(str(x) for x in (m08.get("scientific_execution_git_heads") or []))
    if heads != [EXPECTED_FRESH_HEAD]:
        raise V2FinalMatrixError(f"M08 V2 execution head drift: {heads}")
    md = m08.get("matched_design") or {}
    if int(md.get("completed_arm_epochs", -1)) != 80 or int(md.get("total_fixed_search_calls", -1)) != 5120:
        raise V2FinalMatrixError("M08 V2 matched-budget closure drift")
    integ = m08.get("integrity") or {}
    for key in (
        "all_final_resume_states_absent",
        "all_five_ledgers_hash_chain_valid",
        "all_formal_admissions_have_resolved_novelty",
        "all_ledgers_q0_oos_false",
        "all_results_oos_false",
        "all_results_q0_false",
    ):
        if integ.get(key) is not True:
            raise V2FinalMatrixError(f"M08 V2 closure integrity failed: {key}")

    with tempfile.TemporaryDirectory(prefix="paper_v2_final_") as raw:
        base_out = Path(raw) / "base_matrix.json"
        proc = subprocess.run(
            [sys.executable, str(BASE_BUILDER), "--prospective-root", str(args.prospective_root), "--out", str(base_out)],
            cwd=str(ROOT), text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise V2FinalMatrixError(
                "base final-matrix builder failed closed: " + (proc.stderr or proc.stdout)[-4000:]
            )
        base = load(base_out)
        base_sha = sha(base_out)

    if base.get("decision") != "PASS_ALL_TEN_MATCHED_REPLICATE_CLOSURES_ASSEMBLED":
        raise V2FinalMatrixError("base matched matrix decision drift")
    if list(base.get("replicates") or []) != [f"M{i:02d}" for i in range(1, 11)]:
        raise V2FinalMatrixError("base matrix replicate set drift")
    if base.get("q0_read") is not False or base.get("oos_read") is not False:
        raise V2FinalMatrixError("base matrix firewall drift")

    result = dict(base)
    result["schema"] = "paper-v1-main-v2-final-matched-matrix-v1"
    result["decision"] = "PASS_V2_CARRY_FORWARD_PLUS_FRESH_M08_ALL_TEN_MATCHED_REPLICATES_ASSEMBLED"
    result["v2_authority"] = {
        "execution_binding_path": str(BINDING.relative_to(ROOT)),
        "execution_binding_sha256": sha(BINDING),
        "carry_forward_audit_path": str(resolve_bound_path(binding["carry_forward"]["path"]).relative_to(ROOT)),
        "carry_forward_audit_sha256": str(binding["carry_forward"]["sha256"]),
        "v2_selftest_path": str(resolve_bound_path(binding["v2_selftest"]["path"]).relative_to(ROOT)),
        "v2_selftest_sha256": str(binding["v2_selftest"]["sha256"]),
        "carry_forward_replicates": EXPECTED_CARRY,
        "fresh_v2_replicates": ["M08"],
        "fresh_m08_closure_sha256": sha(fresh_closure),
        "fresh_m08_execution_git_head": EXPECTED_FRESH_HEAD,
        "underlying_v1_compatible_matrix_sha256": base_sha,
        "economic_outcomes_used_to_choose_carry_forward": False,
    }
    result["q0_read"] = False
    result["oos_read"] = False

    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    args.out.write_bytes(raw)
    print(json.dumps({
        "decision": result["decision"],
        "out": str(args.out),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "replicate_arm_rows": len(result.get("arm_rows") or []),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except V2FinalMatrixError as exc:
        print(f"V2_FINAL_MATRIX_FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
