"""
03 - Claude Client with Confidence Tracking

What this demonstrates:
- ClaudeClient with automatic confidence extraction
- Gap detection (low-confidence responses flagged automatically)
- Recording outcomes for reinforcement learning

Suggested prompts to explore after running:
- Try questions where Claude is uncertain vs confident
- Change the gap_threshold and see how it affects gap_detected
- Connect to a runtime with configure_runtime to enable MAB selection

Requires: pip install anthropic
Requires: ANTHROPIC_API_KEY environment variable
"""

import asyncio
import os
import sys

from convergence.clients.claude import ClaudeClient


# --- Configuration ---
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not API_KEY:
    print("ERROR: Set ANTHROPIC_API_KEY environment variable to run this example.")
    print()
    print("  export ANTHROPIC_API_KEY=sk-ant-...")
    print()
    sys.exit(1)


# --- Execution ---
async def main() -> None:
    client = ClaudeClient(
        system="quickstart_chat",
        system_prompt="You are a helpful assistant. Always express your confidence level.",
        model="claude-sonnet-4-5",
        max_tokens=256,
        gap_threshold=0.6,
    )

    print("Sending message to Claude...")
    print()

    response = await client.chat(
        message="What is the capital of France?",
        user_id="demo_user",
    )

    print(f"Content:      {response.content[:200]}")
    print(f"Confidence:   {response.confidence}")
    print(f"Gap detected: {response.gap_detected}")
    print(f"Decision ID:  {response.decision_id}")
    print(f"Model:        {response.model}")
    print(f"Tokens used:  {response.tokens_used}")

    # Record outcome (reward signal for learning)
    if response.decision_id:
        await client.record_outcome(
            decision_id=response.decision_id,
            user_id="demo_user",
            reward=1.0,  # Good answer
        )
        print()
        print("Outcome recorded (reward=1.0)")


if __name__ == "__main__":
    asyncio.run(main())
