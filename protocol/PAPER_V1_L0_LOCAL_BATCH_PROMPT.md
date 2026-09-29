# Paper V1 L0 local-candidate prompt v1

You are the **within-formulation candidate proposer** for arm L0 only. You are not the high-level reformulation controller in this call.

Input contains:

- one frozen current formulation;
- its exact parameter dictionary;
- the frozen legal domain for every parameter;
- the most recent standardized evidence packet/local-search history available at the current 64-call epoch.

Your task is to emit exactly **7 distinct parameter-only candidate dictionaries**. Together with the unchanged current formulation anchor, these 7 candidates form the 8 candidates evaluated on the same 8 frozen screen blocks, for exactly 64 economic evaluator calls.

Hard constraints:

- Do not change mechanism family.
- Do not change representation features or transforms.
- Do not change context features or context logic. You may change only a numeric context threshold through its bound parameter.
- Do not change state/action family. You may change only numeric/categorical knobs already legal inside that family.
- Do not change mapping family. `tail_fraction` may change only within its frozen parameter domain. `gross_target` is fixed.
- Use only parameter keys already present in the current formulation.
- Every emitted value must belong to its supplied frozen domain/range.
- If `parameter_domains.aliases` is present, each alias is a redundant evaluator-facing mirror of its named canonical parameter, not an independent knob. Every candidate must set the alias exactly equal to its canonical parameter.
- The 7 full parameter dictionaries must be mutually distinct and distinct from the current anchor.
- Do not perform a grid, random sweep, CEM/BO/Risk-PG, or formula generation. Choose the candidates semantically from the evidence and current formulation.
- Canonical scientific output is the JSON object required by `PAPER_V1_L0_LOCAL_BATCH_SCHEMA.json`.
- A provider adapter may use a lossless compact wire encoding when the request explicitly supplies `parameter_order` and `provider_wire_format`: each candidate then returns `candidate_index` plus a numeric `values` array aligned exactly to `parameter_order`. The local runtime MUST reconstruct the full canonical parameter dictionaries and pass the unchanged canonical validator before any candidate can be evaluated.

This call is part of the L0 ablation: L0 has the same high-level LLM reformulation controller as L, but no conventional local optimizer. Its local candidate revisions must therefore be explicitly authored by the LLM and pay normal evaluator calls.
