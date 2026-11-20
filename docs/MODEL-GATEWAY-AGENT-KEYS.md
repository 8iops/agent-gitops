# Model Gateway access for in-cluster agents

In-cluster agents reach Anthropic, OpenAI and xAI only through the LiteLLM
gateway in `llm-gateway`. Vendor API keys live only in the
`litellm-provider-credentials` Secret. Agents hold one LiteLLM virtual key
each. Personal subscription credentials (Claude Pro/Max OAuth tokens, ChatGPT
`auth.json`, Cursor user keys) must never be placed in a cluster workload.

## Upstreams

| Gateway model name | Upstream | Secret key |
| --- | --- | --- |
| `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` | Anthropic | `ANTHROPIC_API_KEY` |
| `anthropic/*` | Anthropic, any model | `ANTHROPIC_API_KEY` |
| `openai/*` | OpenAI, any model | `OPENAI_API_KEY` |
| `xai/*` | xAI, any model | `XAI_API_KEY` |

The new Secret keys are `optional`, so the gateway starts and DeepSeek/Kimi keep
working before a vendor key exists. A call to a vendor without a key fails at
request time only.

## Per-agent virtual key

Wildcard routes make every vendor model reachable, so every agent key must set
`models`. Use one key per agent, with a budget, rate limits and an expiry:

```json
{
  "key_alias": "agent-<name>",
  "team_id": "<business-domain team>",
  "models": ["deepseek-v4-flash", "claude-sonnet-5-5"],
  "max_budget": 5,
  "budget_duration": "7d",
  "rpm_limit": 30,
  "tpm_limit": 200000,
  "duration": "30d",
  "metadata": {"agent": "<name>", "owner": "<GitAccount>", "purpose": "<one line>"}
}
```

`POST /key/generate` with an admin credential creates it. Store the returned key
only in the agent's own Secret. The credential broker will issue these keys
automatically later.

## Client settings

| Client | Settings |
| --- | --- |
| Claude Code (`claude -p`) / Claude Agent SDK | `ANTHROPIC_BASE_URL=http://litellm.llm-gateway.svc.cluster.local:4000`, `ANTHROPIC_AUTH_TOKEN=<virtual key>` |
| Codex CLI (`codex exec`) | Use `model_providers.litellm` as in service-backend `codex-app-server-litellm.yaml`, `env_key` holds the virtual key |
| OpenAI SDK / Agents SDK, xAI | `OPENAI_BASE_URL=http://litellm.llm-gateway.svc.cluster.local:4000/v1`, `OPENAI_API_KEY=<virtual key>` |

## Activation check

After a vendor key is added to the Secret and the gateway restarts:

1. One bounded completion per vendor with a test key succeeds.
2. A model outside the key's `models` is denied.
3. A key with a spent `max_budget` is denied.
4. An expired key is denied.
5. `claude -p "say ok"` through `ANTHROPIC_BASE_URL` succeeds (this proves the
   installed image serves the Anthropic `/v1/messages` route).
