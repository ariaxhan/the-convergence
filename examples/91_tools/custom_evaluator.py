"""
Custom Evaluator for run_optimization

What this demonstrates:
- Building a custom evaluator function
- The evaluator interface: receives prediction + expected, returns scores
- Simple text quality scoring based on length and keyword presence

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Add more keywords to the expected dict and watch scores change
- Adjust the weights between completeness and length scoring
- Add a new metric like "readability" to the scores dict
"""

# --- Configuration ---
from typing import Any, Dict, Optional


# --- Setup ---
def text_quality_evaluator(
    prediction: Dict[str, Any],
    expected: Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    Score API responses on completeness and length appropriateness.

    Args:
        prediction: API response dict with 'result' key containing text
        expected: Dict with 'keywords' list and optional 'min_length'/'max_length'
        context: Optional context with 'params' used for the request

    Returns:
        Dict with 'score' (0.0-1.0) and individual metric breakdowns
    """
    text = str(prediction.get("result", ""))
    if not text.strip():
        return {"score": 0.0, "completeness": 0.0, "length": 0.0}

    # Score keyword completeness
    keywords = expected.get("keywords", [])
    if keywords:
        text_lower = text.lower()
        found = sum(1 for kw in keywords if kw.lower() in text_lower)
        completeness = found / len(keywords)
    else:
        completeness = 1.0

    # Score length appropriateness
    min_len = expected.get("min_length", 10)
    max_len = expected.get("max_length", 500)
    if min_len <= len(text) <= max_len:
        length_score = 1.0
    elif len(text) < min_len:
        length_score = max(0.2, len(text) / min_len)
    else:
        overage = (len(text) - max_len) / max_len
        length_score = max(0.5, 1.0 - overage * 0.3)

    # Weighted combination
    score = completeness * 0.7 + length_score * 0.3

    return {
        "score": round(score, 3),
        "completeness": round(completeness, 3),
        "length": round(length_score, 3),
    }


# --- Execution ---
if __name__ == "__main__":
    # Demo: score a few sample predictions
    test_cases = [
        {
            "prediction": {"result": "Paris is the capital of France, known for the Eiffel Tower."},
            "expected": {"keywords": ["Paris", "France", "capital"], "min_length": 20},
        },
        {
            "prediction": {"result": "Yes."},
            "expected": {"keywords": ["Paris", "France"], "min_length": 20},
        },
        {
            "prediction": {"result": "The capital city of France is Paris."},
            "expected": {"keywords": ["capital", "France", "Paris", "Europe"], "min_length": 10},
        },
    ]

    for i, tc in enumerate(test_cases):
        scores = text_quality_evaluator(tc["prediction"], tc["expected"])
        print(f"Test {i + 1}: score={scores['score']:.3f}  "
              f"completeness={scores['completeness']:.3f}  "
              f"length={scores['length']:.3f}")
        print(f"  Text: {tc['prediction']['result'][:60]}...")
        print()
