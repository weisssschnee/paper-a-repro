from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V2_BINDING = ROOT / "protocol" / "PAPER_V1_MAIN_V2_EXECUTION_BINDING.json"
DEFAULT_INFERENCE_BINDING = ROOT / "protocol" / "PAPER_V1_MAIN_INFERENCE_BINDING.json"
FROZEN_ANALYZER = ROOT / "scripts" / "analyze_paper_v1_main_inference.py"

EXPECTED_V2_MATRIX_DECISION = "PASS_V2_CARRY_FORWARD_PLUS_FRESH_M08_ALL_TEN_MATCHED_REPLICATES_ASSEMBLED"
EXPECTED_V1_COMPAT_DECISION = "PASS_ALL_TEN_MATCHED_REPLICATE_CLOSURES_ASSEMBLED"
EXPECTED_V1_COMPAT_SCHEMA = "paper-v1-main-final-matched-matrix-v1"
EXPECTED_ANALYZER_DECISION = "PASS_FROZEN_PAIRED_INFERENCE_APPLIED"


class V2InferenceAdapterError(RuntimeError):
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


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply the pre-final frozen Paper V1 inference implementation to an authority-validated V2 final matrix without changing statistical content."
    )
    ap.add_argument("--matrix", type=Path, required=True)
    ap.add_argument("--v2-binding", type=Path, default=DEFAULT_V2_BINDING)
    ap.add_argument("--inference-binding", type=Path, default=DEFAULT_INFERENCE_BINDING)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    for p in (args.matrix, args.v2_binding, args.inference_binding, FROZEN_ANALYZER):
        if not p.is_file():
            raise V2InferenceAdapterError(f"missing required artifact: {p}")

    v2_binding = load(args.v2_binding)
    inf_binding = load(args.inference_binding)
    matrix = load(args.matrix)

    if v2_binding.get("schema") != "paper-v1-main-v2-execution-binding-v1":
        raise V2InferenceAdapterError("V2 binding schema drift")
    if matrix.get("decision") != EXPECTED_V2_MATRIX_DECISION:
        raise V2InferenceAdapterError(f"unexpected V2 matrix decision: {matrix.get('decision')}")
    if matrix.get("q0_read") is not False or matrix.get("oos_read") is not False:
        raise V2InferenceAdapterError("V2 matrix firewall drift")

    va = matrix.get("v2_authority") or {}
    if va.get("execution_binding_sha256") != sha(args.v2_binding):
        raise V2InferenceAdapterError("V2 matrix execution-binding hash drift")
    if va.get("economic_outcomes_used_to_choose_carry_forward") is not False:
        raise V2InferenceAdapterError("carry-forward authority is outcome-conditioned")

    impl = inf_binding.get("implementation") or {}
    expected_analyzer_sha = str(impl.get("sha256") or "")
    got_analyzer_sha = sha(FROZEN_ANALYZER)
    if got_analyzer_sha != expected_analyzer_sha:
        raise V2InferenceAdapterError(
            f"frozen inference implementation hash drift: {got_analyzer_sha} != {expected_analyzer_sha}"
        )
    if inf_binding.get("decision") != "FROZEN_BEFORE_COMPLETE_M01_M10_MATCHED_RESULTS":
        raise V2InferenceAdapterError("inference binding is not pre-final frozen")

    compat = copy.deepcopy(matrix)
    compat["decision"] = EXPECTED_V1_COMPAT_DECISION
    compat["schema"] = EXPECTED_V1_COMPAT_SCHEMA

    expected_contrasts = ("R-F", "P-F", "R-P", "L-R", "L-L0", "L-F", "L-P")
    inferential_endpoints = (
        "primary_scoped_new_rate_per_1000_calls",
        "formal_admission_rate_per_1000_calls",
    )
    planned = compat.get("planned_contrasts") or {}
    for endpoint in inferential_endpoints:
        family = planned.get(endpoint)
        if not isinstance(family, dict) or set(family.keys()) != set(expected_contrasts):
            raise V2InferenceAdapterError(f"contrast set drift for {endpoint}")
        planned[endpoint] = {label: family[label] for label in expected_contrasts}

    with tempfile.TemporaryDirectory(prefix="paper_v2_inference_") as raw:
        tmp = Path(raw)
        compat_path = tmp / "v1_compatible_matrix.json"
        base_out = tmp / "frozen_inference.json"
        compat_path.write_text(
            json.dumps(compat, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(FROZEN_ANALYZER),
                "--matrix",
                str(compat_path),
                "--binding",
                str(args.inference_binding),
                "--out",
                str(base_out),
            ],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise V2InferenceAdapterError(
                "frozen analyzer failed closed: " + (proc.stderr or proc.stdout)[-5000:]
            )
        base = load(base_out)
        if base.get("decision") != EXPECTED_ANALYZER_DECISION:
            raise V2InferenceAdapterError(f"frozen analyzer decision drift: {base.get('decision')}")

        # Guard that the temporary adaptation changed authority metadata only.
        for key, value in matrix.items():
            if key in {"decision", "schema"}:
                continue
            if key == "planned_contrasts":
                if compat.get(key) != value:
                    raise V2InferenceAdapterError("compatibility adapter changed planned contrast values")
                continue
            if compat.get(key) != value:
                raise V2InferenceAdapterError(f"compatibility adapter changed matrix field: {key}")

        result = {
            "schema": "paper-v1-main-v2-inference-result-v1",
            "decision": "PASS_V2_FROZEN_PAIRED_INFERENCE_APPLIED",
            "v2_matrix": {
                "path": str(args.matrix),
                "sha256": sha(args.matrix),
                "decision": matrix["decision"],
            },
            "v2_execution_binding": {
                "path": str(args.v2_binding),
                "sha256": sha(args.v2_binding),
            },
            "frozen_inference_binding": {
                "path": str(args.inference_binding),
                "sha256": sha(args.inference_binding),
            },
            "frozen_analyzer": {
                "path": str(FROZEN_ANALYZER.relative_to(ROOT)),
                "sha256": got_analyzer_sha,
            },
            "compatibility_adapter": {
                "only_changed_fields": ["decision", "schema", "planned_contrasts_key_order"],
                "from": EXPECTED_V2_MATRIX_DECISION,
                "to_decision": EXPECTED_V1_COMPAT_DECISION,
                "to_schema": EXPECTED_V1_COMPAT_SCHEMA,
                "statistical_rows_or_values_changed": False,
            },
            "frozen_inference_result": base,
            "q0_read": False,
            "oos_read": False,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    args.out.write_bytes(raw)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "out": str(args.out),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except V2InferenceAdapterError as exc:
        print(f"V2_INFERENCE_FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)


