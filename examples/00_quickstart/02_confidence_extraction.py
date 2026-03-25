"""
02 - Confidence Extraction

What this demonstrates:
- Extracting confidence scores from natural language text
- Four extraction methods: explicit, hedging, certainty, auto
- How hedging language lowers confidence
- How certainty language raises confidence

Suggested prompts to explore after running:
- Feed in your own LLM response text and see what score it gets
- Try mixing hedging and certainty language in the same text
- Compare "auto" vs individual methods on the same input

No API keys required. Pure local.
"""

from convergence.evaluators.confidence import extract_confidence

# --- Test Inputs ---
SAMPLES = [
    # (label, text)
    ("Explicit marker", "The answer is 42. Confidence: 85%"),
    ("Explicit decimal", "Result: X. Confidence: 0.92"),
    ("High certainty", "I am absolutely certain the answer is 42."),
    ("Moderate hedging", "I think the answer might be 42."),
    ("Heavy hedging", "I'm not sure, but maybe possibly the answer could be 42."),
    ("No signal", "The answer is 42."),
    ("Mixed signals", "I definitely think maybe the answer is 42."),
    ("Empty text", ""),
]


# --- Execution ---
def main() -> None:
    print("Confidence Extraction Demo")
    print("=" * 65)
    print()

    # Auto mode (default) -- combines all methods
    print("--- Auto mode (default) ---")
    for label, text in SAMPLES:
        score = extract_confidence(text)
        display_text = text[:50] + "..." if len(text) > 50 else text
        print(f"  {label:20s} | {score:>6} | {display_text}")

    print()

    # Compare methods on a single input
    test_text = "I think the answer is probably 42, but I'm not entirely sure."
    print("--- Method comparison ---")
    print(f"  Text: \"{test_text}\"")
    print()

    for method in ["auto", "explicit", "hedging", "certainty"]:
        score = extract_confidence(test_text, method=method)
        print(f"  {method:12s}: {score}")


if __name__ == "__main__":
    main()
