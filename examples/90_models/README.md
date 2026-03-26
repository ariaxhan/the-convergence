# Provider Integration Guide

Armature works with any LLM provider. The framework is provider-agnostic
by design -- it optimizes *how* you call models, not *which* models you call.

## Built-in: Claude

The `ClaudeClient` handles Claude natively with confidence extraction
and gap detection out of the box.

```python
from armature.clients import ClaudeClient

client = ClaudeClient(system="my_app", model="claude-sonnet-4-5")
response = await client.chat(message="Hello", user_id="user_1")
print(response.confidence, response.gap_detected)
```

See `claude/` for full examples.

## Any Other Provider: Runtime Pattern

For OpenAI, Groq, Azure, Ollama, or any other provider, use the
Armature runtime directly. The pattern is always the same:

1. **Select** -- runtime picks optimal parameters via Thompson Sampling
2. **Call** -- you call the provider API with those parameters
3. **Evaluate** -- score the response quality
4. **Update** -- feed the reward back so the runtime learns

```python
from armature import configure_runtime, runtime_select, runtime_update

selection = await runtime_select("my_system", user_id="user_1")
response = call_any_provider(**selection.params)
await runtime_update("my_system", decision_id=selection.decision_id, reward=score)
```

See `openai/`, `groq/`, `azure/`, and `local/` for provider-specific examples.

## Examples

| Directory | Provider | Key Concept |
|-----------|----------|-------------|
| `claude/basic.py` | Claude | ClaudeClient with confidence + gap detection |
| `claude/with_runtime.py` | Claude | ClaudeClient + runtime MAB selection |
| `openai/basic.py` | OpenAI | Runtime pattern with OpenAI API |
| `groq/basic.py` | Groq | Runtime pattern with fast inference |
| `local/ollama.py` | Ollama | Runtime pattern with local models |
| `azure/basic.py` | Azure OpenAI | Runtime pattern with Azure endpoints |

## Prerequisites

```bash
pip install -e .

# Provider-specific:
pip install anthropic   # Claude
pip install openai      # OpenAI / Azure
pip install groq        # Groq
# Ollama: just run `ollama serve` locally
```
