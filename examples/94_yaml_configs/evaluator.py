"""Custom evaluator referenced by custom_evaluator.yaml.

Scores API responses on keyword match, length, and format.
"""

from __future__ import annotations


def evaluate_response(
    config: dict,
    response: str,
    test_case: dict,
) -> dict[str, float]:
    """Score a response against a test case.

    Args:
        config: The parameter config used to generate this response.
        response: The raw text response from the API.
        test_case: The test case dict with 'input' and 'expected' keys.

    Returns:
        Dict of metric name to score (0.0 - 1.0).
    """
    expected = test_case.get("expected", {})
    keyword = expected.get("contains", "")
    fmt = expected.get("format", "sentence")

    # Keyword match: 1.0 if keyword found, 0.0 otherwise
    keyword_match = 1.0 if keyword.lower() in response.lower() else 0.0

    # Length score: reward responses between 50-300 chars
    length = len(response)
    length_score = min(length, 300) / 300 if length >= 50 else length / 50 * 0.5

    # Format score: check basic formatting expectations
    format_score = 0.0
    if fmt == "sentence" and response.endswith((".", "!", "?")):
        format_score = 1.0
    elif fmt == "paragraph" and len(response.split(". ")) >= 2:
        format_score = 1.0
    elif response.strip():
        format_score = 0.5

    return {
        "keyword_match": keyword_match,
        "length_score": round(length_score, 3),
        "format_score": format_score,
    }


if __name__ == "__main__":
    sample_config = {"temperature": 0.7, "max_tokens": 200}
    sample_response = "Hello! Recursion is when a function calls itself."
    sample_test = {"input": {"prompt": "Write a greeting"}, "expected": {"contains": "hello", "format": "sentence"}}

    scores = evaluate_response(sample_config, sample_response, sample_test)
    print("Sample evaluation:")
    for metric, score in scores.items():
        print(f"  {metric}: {score}")
