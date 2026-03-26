"""
Self-Improving Classifier -- Armature end-to-end example.

What this demonstrates:
  - Thompson Sampling (Runtime MAB) with 4 classification strategy arms
  - Confidence extraction to measure classification certainty
  - Accuracy tracking and ASCII armature chart

Suggested prompts to explore after reading:
  - Swap the accuracy profiles so "zero_shot" wins and watch armature shift
  - Add noise to labels and see how the bandit adapts
  - Increase dataset to 100 samples and observe tighter armature
"""
from __future__ import annotations

import asyncio
import random
from typing import Dict, List, Tuple

from armature import (
    RuntimeArmTemplate,
    RuntimeConfig,
    configure_runtime,
    runtime_select,
    runtime_update,
)
from armature.evaluators.confidence import extract_confidence
from armature.storage.memory import MemoryRuntimeStorage

SYSTEM, USER_ID, LABELS = "classifier", "eval_user", ["positive", "negative", "neutral"]
DATASET: List[Tuple[str, str]] = [
    ("This product is amazing, I love it!", "positive"),
    ("Terrible experience, never buying again.", "negative"),
    ("The package arrived on time.", "neutral"),
    ("Best purchase I have ever made!", "positive"),
    ("Broke after one day. Total waste.", "negative"),
    ("It works as described.", "neutral"),
    ("Incredible quality, exceeded expectations!", "positive"),
    ("Customer support was unhelpful and rude.", "negative"),
    ("Standard delivery, nothing special.", "neutral"),
    ("Definitely recommending this to friends.", "positive"),
    ("Would not buy again. Very disappointing.", "negative"),
    ("The color matches the listing.", "neutral"),
    ("Five stars, truly outstanding!", "positive"),
    ("Maybe the worst product I have tried.", "negative"),
    ("Arrived in original packaging.", "neutral"),
    ("So happy with this purchase!", "positive"),
    ("Not sure this was worth the price. Perhaps not.", "negative"),
    ("Meets basic expectations.", "neutral"),
    ("Absolutely love it, 100% satisfied.", "positive"),
    ("Garbage quality, clearly a scam.", "negative"),
    ("Looks like the photo.", "neutral"),
    ("Perfect for my needs, certainly worth it.", "positive"),
    ("Disappointing build quality overall.", "negative"),
    ("Functions correctly.", "neutral"),
    ("Amazing value for the price!", "positive"),
    ("I regret this purchase completely.", "negative"),
    ("Shipping was standard.", "neutral"),
    ("Exceeded all my expectations!", "positive"),
    ("Poorly made, falling apart already.", "negative"),
    ("It is what it is.", "neutral"),
    ("Wonderful product, highly recommend!", "positive"),
    ("Not worth even half the price.", "negative"),
    ("Average quality for the price.", "neutral"),
    ("Couldn't be happier with this!", "positive"),
    ("Feels cheap and poorly constructed.", "negative"),
    ("Does the job.", "neutral"),
    ("Outstanding craftsmanship!", "positive"),
    ("Total letdown.", "negative"),
    ("Nothing remarkable.", "neutral"),
    ("Love everything about this!", "positive"),
]
# P(correct) per strategy -- "hybrid" is intentionally best
STRATEGY_ACC: Dict[str, float] = {"keyword": 0.55, "semantic": 0.65, "hybrid": 0.82, "zero_shot": 0.70}
CONF_TEXT: Dict[str, str] = {
    "keyword": "Classification based on keyword matching. I think the label is correct.",
    "semantic": "Semantic similarity suggests this label. Confidence: 70%",
    "hybrid": "Hybrid analysis clearly indicates this category. Confidence: 88%",
    "zero_shot": "Zero-shot prediction. The answer is probably correct.",
}

async def main() -> None:
    storage = MemoryRuntimeStorage()
    config = RuntimeConfig(system=SYSTEM, default_arms=[
        RuntimeArmTemplate(arm_id=s, name=s.replace("_", " ").title(), params={"strategy": s})
        for s in STRATEGY_ACC
    ])
    await configure_runtime(SYSTEM, config=config, storage=storage)

    correct_per: Dict[str, int] = {s: 0 for s in STRATEGY_ACC}
    total_per: Dict[str, int] = {s: 0 for s in STRATEGY_ACC}
    running_acc: List[float] = []
    running_ok = 0

    print(f"{'='*60}\n  Self-Improving Classifier -- MAB + Confidence\n{'='*60}\n")
    for i, (text, true_label) in enumerate(DATASET):
        sel = await runtime_select(SYSTEM, user_id=USER_ID)
        strategy = sel.arm_id
        ok = random.random() < STRATEGY_ACC[strategy]
        pred = true_label if ok else random.choice([l for l in LABELS if l != true_label])
        conf = extract_confidence(CONF_TEXT[strategy]) or 0.5
        reward = max(0.0, min(1.0, (1.0 if ok else 0.0) * 0.7 + conf * 0.3))
        if sel.decision_id:
            await runtime_update(SYSTEM, user_id=USER_ID, decision_id=sel.decision_id, reward=reward)
        total_per[strategy] += 1
        if ok:
            correct_per[strategy] += 1
            running_ok += 1
        running_acc.append(running_ok / (i + 1))
        mark = "ok" if ok else "XX"
        print(f"  [{i+1:02d}] {strategy:10s} | {mark} | conf={conf:.2f} | pred={pred:8s} | true={true_label:8s}")

    # -- Per-strategy accuracy
    print(f"\n{'='*60}\n  Per-Strategy Accuracy\n{'='*60}")
    for s in STRATEGY_ACC:
        t, c = total_per[s], correct_per[s]
        a = c / t if t else 0
        print(f"    {s:12s} | {c:2d}/{t:2d} = {a:.0%}  {'#' * int(a * 30)}")

    # -- ASCII armature chart
    print(f"\n{'='*60}\n  Running Accuracy\n{'='*60}")
    step = max(1, len(running_acc) // 40)
    sampled = [running_acc[j] for j in range(0, len(running_acc), step)]
    for row in range(10, 0, -1):
        thr = row / 10
        print(f"  {thr:4.1f} |" + "".join("#" if v >= thr else " " for v in sampled))
    print(f"       +{'-' * len(sampled)}\n        iteration -->")

    # -- Arm armature
    arms = await storage.get_arms(user_id=USER_ID, agent_type="default")
    print("\n  Arm estimates:")
    for arm in arms:
        m, p = arm.get("mean_estimate") or 0, arm.get("total_pulls", 0)
        print(f"    {arm.get('name', arm['arm_id']):12s} | pulls={p:3d} | mean={m:.3f} | {'#' * int(m * 30)}")
    print(f"\n  Overall: {running_ok}/{len(DATASET)} = {running_ok/len(DATASET):.0%}")
    print("  The bandit should converge toward 'Hybrid' (highest accuracy profile).\n")

if __name__ == "__main__":
    asyncio.run(main())
