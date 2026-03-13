"""
Basic Agent Example

Demonstrates the core runtime API: configure, select, update.
The agent learns which model performs best over time.

Run:
    python examples/basic_agent.py
"""

import asyncio
import random

from convergence.runtime.online import configure, select, update
from convergence.storage.sqlite import SQLiteStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig


async def simulate_llm_call(model: str, prompt: str) -> tuple[str, float]:
    """
    Simulate calling an LLM and getting a response.
    In reality, you'd call OpenAI, Anthropic, etc.

    Returns:
        tuple: (response_text, quality_score)
    """
    # Simulate different model performance
    # In reality, you'd evaluate actual response quality
    base_quality = {
        "gpt-4": 0.9,
        "gpt-3.5": 0.7,
        "claude-3": 0.85,
    }

    quality = base_quality.get(model, 0.5) + random.uniform(-0.1, 0.1)
    quality = max(0.0, min(1.0, quality))

    response = f"Response from {model}: [simulated response to '{prompt[:30]}...']"
    return response, quality


async def main():
    # 1. Initialize storage
    storage = SQLiteStorage(db_path="./basic_agent.db")
    await storage.initialize()

    # 2. Configure the runtime with available models
    config = RuntimeConfig(
        system="basic-agent",
        default_arms=[
            RuntimeArmTemplate(
                arm_id="gpt-4",
                name="GPT-4",
                params={"model": "gpt-4", "temperature": 0.7},
            ),
            RuntimeArmTemplate(
                arm_id="gpt-3.5",
                name="GPT-3.5 Turbo",
                params={"model": "gpt-3.5-turbo", "temperature": 0.7},
            ),
            RuntimeArmTemplate(
                arm_id="claude-3",
                name="Claude 3 Sonnet",
                params={"model": "claude-3-sonnet", "temperature": 0.7},
            ),
        ],
    )
    await configure("basic-agent", config=config, storage=storage)

    # 3. Run some interactions
    print("Running 20 interactions to demonstrate learning...\n")

    for i in range(20):
        # Select best arm (Thompson Sampling)
        selection = await select("basic-agent", user_id="demo-user")

        # Use the selected model
        model = selection.arm_id
        prompt = f"Explain concept {i + 1}"

        response, quality = await simulate_llm_call(model, prompt)

        # Update with the quality score (reward)
        await update(
            "basic-agent",
            user_id="demo-user",
            decision_id=selection.decision_id,
            reward=quality,
        )

        print(f"[{i + 1:2d}] Selected: {model:8s} | Quality: {quality:.2f}")

    # 4. Show final arm statistics
    print("\n--- Final Arm Statistics ---")
    final_selection = await select("basic-agent", user_id="demo-user")

    for arm in final_selection.arms_state:
        mean = arm.alpha / (arm.alpha + arm.beta)
        print(f"{arm.arm_id:8s}: alpha={arm.alpha:.1f}, beta={arm.beta:.1f}, mean={mean:.3f}")

    print("\nThe agent has learned which model performs best!")
    print("Run again to see it continue learning from the stored state.")


if __name__ == "__main__":
    asyncio.run(main())
