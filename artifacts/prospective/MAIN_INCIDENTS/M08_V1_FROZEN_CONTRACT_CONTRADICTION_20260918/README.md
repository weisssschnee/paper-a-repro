# Paper V1 Main Frozen-Contract Contradiction

## Decision

Paper V1 main is **not valid for the originally planned confirmatory fixed-budget arm inference**. Do not run an M08 restart3, do not pad the missing epochs, do not relax the closure gate, and do not compute the planned V1 arm ranking/contrast table.

The decision is based on a mechanical contradiction in the frozen experiment contract, not on comparative economic outcomes. Q0/OOS remain unread.

## Frozen contracts that conflict

At scientific execution head `8635324e37d9afef54e6ee8ebe454cb99f564bd9`:

- `protocol/PAPER_V1_MAIN_EXECUTION_BINDING.json` freezes **16 decision epochs per arm**, **64 search calls per epoch**, and **1,024 fixed search calls per arm**.
  - Git blob: `ea25f71cef49e0bed66065e24a7696b2920cf77b`
- `scripts/formulation_payload_generator.py` implements `CHANGE_MECHANISM/ABANDON_BASIN` by choosing the next unused frozen mechanism family; when none exists it emits `terminal_trajectory=true`.
  - Git blob: `1259c765c70d4937f150049919121fc5a3f587ce`
- `protocol/PAPER_V1_FORMULATION_MUTATION_BANK.json` binds `ABANDON_BASIN` to closing the current lineage and advancing to the next unused frozen seed family.
  - Git blob: `2d1b41fb00143007718b8cce5449b9bac1681167`
- `scripts/close_paper_v1_main_replicate_77o.py` requires all E01–E16 result files and requires final `search_calls_after == 1024`.
  - Git blob: `b50612d18f707676690e6f58c1613c87168a171f`

No predeclared rule specifies what should happen when the finite unused-family set is exhausted **before** epoch 16.

## Reproduction

The contradiction reproduced twice in M08 without reading Q0/OOS:

1. M08 restart1, L0: `ABANDON_BASIN` at E15 produced a terminal trajectory at **960/1024** fixed search calls.
2. M08 restart2, L0: `ABANDON_BASIN` at E10 produced a terminal trajectory at **640/1024** fixed search calls.

The second reproduction rules out treating the first event as an isolated runner accident.

## Why no restart3

Repeatedly restarting M08 until the L0 policy happens not to exhaust the family set would condition replicate validity on the realized controller trajectory. That is selection on a post-launch policy outcome and would bias the matched comparison.

Likewise, inventing dummy epochs, relaxing the 1,024-call closure requirement, or adding a post-hoc absorbing state would change the experiment after observing the failure mode.

## Status of existing V1 evidence

M01–M07, M09, and M10 remain durable, hash-checked execution evidence and are useful for descriptive/process analysis. They are **not sufficient to restore the originally predeclared V1 confirmatory fixed-budget estimand**, because the state machine is not total over the allowed policy trajectories.

The V1 final matrix must therefore remain fail-closed.

## Required reformulation

Before any new confirmatory economic calls, freeze a corrected V2 contract in which the state machine is total for all 16 decision epochs. The correction must be mechanical and outcome-independent. It must not alter:

- evaluator/cost/funding semantics;
- PIT or available-time semantics;
- SCREEN8 / EXTENDED24 / FULLTRAIN gates;
- formal specialist court;
- novelty comparator/reference;
- 64-search-call decision clock;
- primary KPI/endpoints;
- Q0/OOS firewall.

A V2 experiment must run under one coherent contract; V1 outcomes are retained as diagnostic evidence rather than mixed into V2 confirmatory inference.
