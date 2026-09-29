# Paper A partial reproducibility package

Companion data for "When Should Search Reformulate?" (Paper A).

This is a partial, whitelist-based release. It contains what is needed to
recompute the frozen confirmatory matrix, the paired inference, and the
submission figures from the hash-bound per-arm ledgers and result files.
Controller request/response bodies, novelty-resolution state, search-space
definitions, and operational incident logs are withheld; MANIFEST.json lists
withheld prospective/protocol files and V1_PROTOCOL.md by path, size, and
SHA-256 so their existence and identity are auditable.

## Layout

- `scripts/` pipeline: base matrix builder, V2 matrix builder, frozen paired
  analyzer, V2 inference adapter, figure generator.
- `protocol/` selected frozen bindings, controller interface/prompt/schema,
  parity and comparator policies. The full `V1_PROTOCOL.md` is not included.
- `artifacts/prospective/Mxx/runs/<ARM>/` per-arm `ledger.jsonl`, the result
  files referenced by each replicate closure, and controller backend /
  formatting-repair / transport-retry attestations.
- `artifacts/prospective/Mxx/PAPER_V1_Mxx_MAIN_CLOSURE_V2.json` replicate closures.
- `figures/` frozen submission figures with extracts and receipts.

## Byte identity

Files marked `verbatim` in MANIFEST.json are the exact bytes whose SHA-256
values are bound in the protocol and closure receipts (several are CRLF; this
repository sets `* -text` so git does not rewrite them). Files marked
`path_stripped` had local absolute paths replaced by logical paths
(`<run_root>/...`, `<tempdir>/...`, or repository-relative); MANIFEST.json
records both the original and the public SHA-256. Rebuilding therefore
reproduces every numeric field exactly, while fields that hash the stripped
closures (closure receipt hashes, `fresh_m08_closure_sha256`, derived matrix
hashes) take new values.

One file is marked `vendor_redacted`:
`protocol/PAPER_V1_MAIN_V2_EXECUTION_BINDING.json`, where the name of the
third-party relay that served the controller model is replaced by
`<redacted_relay_vendor>`. No other byte changed, and MANIFEST.json records both
the original and the public SHA-256. A rebuilt matrix therefore records the
public hash in `execution_binding_sha256`. The committed matrix and inference
result keep the original hash.

## Reproduce

Python 3.11 with scipy (tested with 3.11.9 / scipy 1.17.1):

    python scripts/build_paper_v1_main_v2_final_matrix.py --out /tmp/matrix.json
    python scripts/analyze_paper_v1_main_v2_inference.py --matrix /tmp/matrix.json --out /tmp/inference.json

Compare against `artifacts/prospective/PAPER_V1_MAIN_V2_FINAL_MATCHED_MATRIX.json`
and `PAPER_V1_MAIN_V2_INFERENCE_RESULT.json` ignoring `path` fields and the
closure-derived hashes listed above. `scripts/generate_submission_figures.py`
regenerates `figures/` in place (byte-identical on Windows; on other platforms
line endings differ).

No Q0 or out-of-sample data were read by any artifact here (`q0_read` and
`oos_read` are false throughout).

See LICENSE.md for the code and research-material license scopes. No underlying
market data, upstream datasets, or withheld artifacts are licensed here.
