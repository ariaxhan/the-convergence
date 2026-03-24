"""
Claude Integration -- Basic

What this demonstrates:
- Using the built-in ClaudeClient
- Confidence extraction from Claude responses
- Gap detection for low-confidence answers

Prerequisites:
- pip install the-convergence anthropic
- Set ANTHROPIC_API_KEY environment variable

Suggested prompts / test inputs:
- Change the question to something obscure and watch confidence drop
- Lower gap_threshold to 0.8 to trigger gap detection more often
- Try model="claude-haiku-4-5-20250514" for faster, cheaper responses
"""

# --- Configuration ---
import asyncio
import os
import sys

from convergence.clients import ClaudeClient


# --- Setup ---
def check_api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)


# --- Execution ---
async def main():
    check_api_key()

    client = ClaudeClient(
        system="demo",
        system_prompt="You are a helpful assistant.",
        model="claude-sonnet-4-5",
    )

    response = await client.chat(
        message="What is the capital of France?",
        user_id="demo_user",
    )

    print(f"Content:      {response.content[:200]}")
    print(f"Confidence:   {response.confidence}")
    print(f"Gap detected: {response.gap_detected}")
    print(f"Model:        {response.model}")
    print(f"Tokens used:  {response.tokens_used}")


if __name__ == "__main__":
    asyncio.run(main())
