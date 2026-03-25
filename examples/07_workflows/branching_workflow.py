"""
Branching Workflow with Confidence Routing

What this demonstrates:
- Confidence-based routing: high -> auto-respond, medium -> enhance, low -> escalate
- extract_confidence scores simulated LLM outputs
- detect_gap flags responses that fall below threshold
- Routing statistics per branch

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Adjust HIGH/LOW thresholds and see how routing shifts
- Add more diverse response texts with varying hedging
- Change the gap threshold and observe detection changes

No API keys required. Pure local.
"""

import random

from convergence.evaluators.confidence import extract_confidence
from convergence.types.response import LLMResponse, detect_gap

# --- Configuration ---
HIGH_THRESHOLD = 0.7
LOW_THRESHOLD = 0.4
ROUNDS = 30

RESPONSE_TEMPLATES = [
    "The answer is {v}. Confidence: 92%",
    "I am certain the result is {v}.",
    "I believe the answer is {v}, but I'm not entirely sure.",
    "I think maybe it could be {v}.",
    "Perhaps {v}, though I'm quite uncertain about this.",
    "The result is definitely {v}. Absolutely.",
    "It might possibly be {v}, I'm not confident.",
    "{v}.",
    "I'm fairly sure it's {v}.",
    "Possibly {v}, but there could be other explanations.",
]


# --- Execution ---
def main() -> None:
    branches = {"auto": [], "enhance": [], "escalate": []}

    for i in range(ROUNDS):
        template = random.choice(RESPONSE_TEMPLATES)
        text = template.format(v=random.randint(1, 100))

        confidence = extract_confidence(text)
        conf_val = confidence if confidence is not None else 0.3

        llm_resp = LLMResponse(content=text, confidence=conf_val)
        gap = detect_gap(llm_resp, threshold=HIGH_THRESHOLD)

        if conf_val >= HIGH_THRESHOLD:
            branch = "auto"
        elif conf_val >= LOW_THRESHOLD:
            branch = "enhance"
        else:
            branch = "escalate"

        branches[branch].append({
            "round": i + 1, "conf": conf_val,
            "gap": gap.gap_detected, "text": text[:50],
        })

    # --- Output ---
    print("Branching Workflow - Confidence Routing")
    print(f"Thresholds: auto >= {HIGH_THRESHOLD}, "
          f"enhance >= {LOW_THRESHOLD}, else escalate")
    print("=" * 55)

    for branch, items in branches.items():
        print(f"\n  {branch.upper()} ({len(items)} queries):")
        for item in items[:5]:
            gap_flag = " [GAP]" if item["gap"] else ""
            print(f"    R{item['round']:2d} conf={item['conf']:.2f}"
                  f"{gap_flag} {item['text']}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")

    print(f"\nRouting summary: auto={len(branches['auto'])}, "
          f"enhance={len(branches['enhance'])}, "
          f"escalate={len(branches['escalate'])}")


if __name__ == "__main__":
    main()
