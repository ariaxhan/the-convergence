"""
Confidence Thresholds and Routing

What this demonstrates:
- Extracting confidence from LLM response text
- Threshold-based routing: auto-respond, escalate, or clarify
- Gap detection with detect_gap()
- How hedging and certainty language affect confidence scores

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Try "I am absolutely 100% certain" to see max confidence
- Try "maybe possibly perhaps" to see minimum confidence from hedging
"""

# --- Configuration ---
from armature.evaluators.confidence import extract_confidence
from armature.types.response import LLMResponse, detect_gap

HIGH_THRESHOLD = 0.8
LOW_THRESHOLD = 0.5

# --- Setup ---

RESPONSES = [
    "The answer is 42. Confidence: 95%",
    "I'm fairly sure the capital of France is Paris.",
    "I think maybe it could possibly be related to quantum effects.",
    "The result is definitely correct. Absolutely guaranteed.",
    "I'm not entirely sure, but I believe it might be option B.",
    "Python was created by Guido van Rossum.",
    "Perhaps the error is in the configuration, but I'm uncertain.",
    "Confidence: 0.72",
    "",
]


def route_response(text: str, confidence: float) -> str:
    """Route based on confidence threshold."""
    if confidence >= HIGH_THRESHOLD:
        return "AUTO-RESPOND"
    elif confidence >= LOW_THRESHOLD:
        return "REVIEW"
    else:
        return "ESCALATE"


# --- Execution ---
if __name__ == "__main__":
    print("Confidence Extraction and Routing")
    print(f"Thresholds: auto >= {HIGH_THRESHOLD}, review >= {LOW_THRESHOLD}, else escalate\n")

    header = f"{'Response (truncated)':<45} | {'Conf':>5} | {'Route':<12} | {'Gap?'}"
    print(header)
    print("-" * 80)

    for text in RESPONSES:
        confidence = extract_confidence(text)
        conf_val = confidence if confidence is not None else 0.3

        # Create LLMResponse for gap detection
        llm_response = LLMResponse(content=text, confidence=conf_val)
        gap_result = detect_gap(llm_response, threshold=HIGH_THRESHOLD)

        route = route_response(text, conf_val)
        display = text[:42] + "..." if len(text) > 45 else text
        if not display:
            display = "(empty)"
        gap_str = "YES" if gap_result.gap_detected else "no"

        print(f"{display:<45} | {conf_val:>5.2f} | {route:<12} | {gap_str}")

    # Show method comparison
    print("\nMethod comparison for: 'I think the answer is probably correct.'")
    sample = "I think the answer is probably correct."
    for method in ["auto", "explicit", "hedging", "certainty"]:
        score = extract_confidence(sample, method=method)
        score_str = f"{score:.2f}" if score is not None else "None"
        print(f"  {method:>10}: {score_str}")
