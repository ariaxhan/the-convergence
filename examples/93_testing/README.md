# Testing Patterns

Testing patterns for Armature optimization workflows.

## Test Case Format

All test cases follow this JSON structure:

```json
{
  "test_cases": [
    {
      "id": "unique_id",
      "description": "What this test validates",
      "input": { ... },
      "expected": { ... },
      "metadata": {
        "category": "qa",
        "difficulty": "easy",
        "weight": 1.0
      }
    }
  ]
}
```

## SDK TestCase Objects

The SDK provides `TestCase` and `normalize_test_cases` for working
with test cases programmatically:

```python
from armature.sdk import TestCase, normalize_test_cases

tc = TestCase(
    input={"prompt": "What is 2+2?"},
    expected={"contains": ["4"]},
    meta={"difficulty": "easy"},
)
```

See `test_case_basics.py` for a complete walkthrough.

## Existing Test Case Files

See `examples/test_cases/` for JSON test case files:

| File | Domain |
|------|--------|
| `test_cases.json` | Code generation |
| `reasoning_tests.json` | Logical reasoning |
| `search_tests.json` | Search queries |
| `vector_search_tests.json` | Vector/semantic search |
| `web_scraping_tests.json` | Web scraping |

## Test Case Best Practices

1. **Start with 3-5 high-quality tests** -- use augmentation to generate more
2. **Cover the distribution** -- match your production workload
3. **Be specific in expected** -- use `contains`, `min_length`, not vague booleans
4. **Test edge cases** -- empty input, long input, special characters
5. **Use weights** -- prioritize important tests with higher weight values

For the full guide, see `examples/test_cases/README.md`.
