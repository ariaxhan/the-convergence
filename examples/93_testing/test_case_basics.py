"""
Test Case Basics

What this demonstrates:
- Creating TestCase objects with the SDK
- Normalizing test cases from dicts into TestCase instances
- Inspecting test case structure (input, expected, meta)

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Add more test cases with different difficulty levels
- Try passing a generator function to normalize_test_cases
- Add metadata fields and see how they flow through
"""

# --- Configuration ---
from armature.sdk import TestCase, normalize_test_cases

# --- Setup ---
# Test cases can be created as objects or from dicts
test_case_objects = [
    TestCase(
        input={"prompt": "What is 2+2?"},
        expected={"contains": ["4"]},
        meta={"category": "math", "difficulty": "easy"},
    ),
    TestCase(
        input={"prompt": "Explain photosynthesis in one sentence."},
        expected={"contains": ["light", "energy"], "min_length": 20},
        meta={"category": "science", "difficulty": "medium"},
    ),
]

# Dicts also work -- normalize_test_cases handles both
test_case_dicts = [
    {
        "input": {"prompt": "What is the capital of Japan?"},
        "expected": {"contains": ["Tokyo"]},
        "meta": {"category": "geography", "difficulty": "easy"},
    },
    {
        "input": {"prompt": "Write a haiku about programming."},
        "expected": {"min_length": 10},
        "meta": {"category": "creative", "difficulty": "medium"},
    },
]


# --- Execution ---
if __name__ == "__main__":
    # Normalize from objects
    print("=== From TestCase objects ===")
    for tc in normalize_test_cases(test_case_objects):
        print(f"  Input:    {tc.input}")
        print(f"  Expected: {tc.expected}")
        print(f"  Meta:     {tc.meta}")
        print()

    # Normalize from dicts
    print("=== From dicts ===")
    for tc in normalize_test_cases(test_case_dicts):
        print(f"  Input:    {tc.input}")
        print(f"  Expected: {tc.expected}")
        print(f"  Meta:     {tc.meta}")
        print()

    # Convert back to dict for serialization
    print("=== Round-trip to dict ===")
    tc = test_case_objects[0]
    as_dict = tc.to_dict()
    print(f"  Dict: {as_dict}")
    print(f"  Type: {type(as_dict)}")
