# Custom Tools

How to build custom tools for Convergence agents.

## Custom Evaluators

The `run_optimization` function accepts a custom evaluator that scores
API responses. This is how you teach Convergence what "good" looks like
for your specific use case.

### Evaluator Interface

```python
def my_evaluator(prediction: dict, expected: dict, *, context: dict = None) -> dict:
    """
    Score a single API response.

    Args:
        prediction: The API response (contains 'result' key)
        expected: Expected values from the test case
        context: Optional context with 'params' used for the request

    Returns:
        Dict with 'score' key (0.0 to 1.0) and optional metric breakdowns
    """
    score = evaluate_quality(prediction["result"], expected)
    return {"score": score}
```

### Usage with run_optimization

```python
from convergence.sdk import run_optimization

result = await run_optimization(
    config=my_config,
    evaluator=my_evaluator,
    test_cases=my_test_cases,
)
```

## Examples

| File | What It Shows |
|------|---------------|
| `custom_evaluator.py` | Build a custom evaluator for text quality scoring |

## See Also

- `examples/ai/openai/openai_responses.py` -- OpenAI-specific evaluator
- `examples/ai/groq/groq_responses.py` -- Groq-specific evaluator
- `examples/ai/azure/azure_multi_model_evaluator.py` -- Azure multi-model evaluator
