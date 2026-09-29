# Paper V1 LLM Backend Guide

The Paper V1 scientific contract is provider-neutral. Backends only transport a frozen controller request to an LLM and return JSON for canonical local validation.

## 1. ChatGPT / web UI — no paid API required

1. Generate an immutable request:

```text
py scripts/paper_v1_llm_bridge.py prepare \
  --mode high \
  --packet <evidence_packet.json> \
  --decision-epoch <N> \
  --run-id <matched_run_id> \
  --transport-class FILE_HANDOFF \
  --backend-identity "ChatGPT web" \
  --model-identity "<UI model name if exposed>" \
  --fresh-context --tools-disabled \
  --request-out <request.json>
```

2. Open a fresh isolated ChatGPT conversation. Do not provide repository/raw-market/OOS files and do not enable external tools for the controller call. Give the request and ask for only the JSON object required by the embedded schema.
3. Save the returned JSON as `response.json`.
4. Consume and validate:

```text
py scripts/paper_v1_llm_bridge.py consume \
  --request <request.json> \
  --response <response.json> \
  --result-out <validated_result.json> \
  --receipt-out <controller_receipt.json>
```

The action is executable only after this local validation succeeds.

## 2. Codex / OpenCode / other CLI

Use a thin controller-only wrapper whose external contract is:

```text
stdin:  one Paper V1 request JSON object
stdout: one canonical controller response JSON object
stderr: diagnostics only
```

Freeze a backend manifest before the matched run:

```json
{
  "schema": "paper-v1-command-backend-manifest-v1",
  "backend_identity": "Codex controller-only wrapper",
  "model_identity": "model/version if exposed",
  "fresh_context": true,
  "tools_disabled": true,
  "argv": ["<wrapper executable>", "<fixed args>"]
}
```

Then invoke:

```text
py scripts/paper_v1_llm_bridge.py command \
  --request <request.json> \
  --backend-manifest <backend_manifest.json> \
  --receipt-out <controller_receipt.json>
```

The wrapper may use Codex/OpenCode internally, but for this controller call it must not expose shell, repository search, web, OOS, or raw-market tools. If the product cannot provide a controller-only isolated invocation, use FILE_HANDOFF instead.

## 3. HTTP/API backend

An API adapter is optional. It may use OpenAI or any other provider, but must reconstruct exactly the same canonical response and pass the same local validator. API billing, provider-specific seed semantics, and endpoint availability are not part of the scientific intervention.

## 4. Run-level freeze

Before the first LLM decision of a matched run, record:

- transport class;
- backend/product identity;
- model/version identity if the runtime exposes it;
- bridge/interface/prompt/schema/validator hashes;
- wrapper command/config hash if applicable;
- `fresh_context=true` and `tools_disabled=true` attestation.

Do not switch backend after observing economic outcomes. If a backend becomes unavailable, use the predeclared failure policy or restart the affected matched run.
