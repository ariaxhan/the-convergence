"""
Input Validation

What this demonstrates:
- Validating user inputs before passing to runtime
- Checking for empty strings, injection patterns, and length limits
- Returning structured validation results

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Add a regex-based email validation check
- Add a check for Unicode control characters
"""

# --- Configuration ---
import re
from typing import List, Tuple

MAX_INPUT_LENGTH = 500
MIN_INPUT_LENGTH = 1
INJECTION_PATTERNS = [
    r"<script\b",
    r"javascript:",
    r"\b(DROP|DELETE|INSERT|UPDATE)\s+(TABLE|FROM|INTO)\b",
    r"\{\{.*\}\}",  # Template injection
    r"\$\{.*\}",    # Expression injection
]

COMPILED_PATTERNS = [(p, re.compile(p, re.IGNORECASE)) for p in INJECTION_PATTERNS]

# --- Setup ---


def validate_input(text: str) -> Tuple[bool, List[str]]:
    """
    Validate user input text.

    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []

    # Check for None/empty
    if not text or not text.strip():
        errors.append("Input is empty or whitespace-only")
        return False, errors

    stripped = text.strip()

    # Length checks
    if len(stripped) < MIN_INPUT_LENGTH:
        errors.append(f"Input too short (min {MIN_INPUT_LENGTH} chars)")
    if len(stripped) > MAX_INPUT_LENGTH:
        errors.append(f"Input too long ({len(stripped)} > {MAX_INPUT_LENGTH} chars)")

    # Injection pattern checks
    for pattern_str, pattern in COMPILED_PATTERNS:
        if pattern.search(stripped):
            errors.append(f"Injection pattern detected: {pattern_str}")

    # Control character check (except newlines/tabs)
    control_chars = sum(1 for c in stripped if ord(c) < 32 and c not in "\n\r\t")
    if control_chars > 0:
        errors.append(f"Contains {control_chars} control characters")

    return len(errors) == 0, errors


TEST_INPUTS = [
    ("Hello, how are you?", "Normal input"),
    ("", "Empty string"),
    ("   ", "Whitespace only"),
    ("<script>alert('xss')</script>", "XSS attempt"),
    ("DROP TABLE users; --", "SQL injection"),
    ("{{constructor.constructor('return this')()}}", "Template injection"),
    ("x" * 600, "Exceeds length limit"),
    ("What is the meaning of life?", "Valid question"),
    ("Tell me about ${process.env.SECRET}", "Expression injection"),
]

# --- Execution ---
if __name__ == "__main__":
    print(f"Input Validation (max {MAX_INPUT_LENGTH} chars, {len(INJECTION_PATTERNS)} patterns)\n")

    header = f"{'Label':<25} | {'Valid':>5} | {'Errors'}"
    print(header)
    print("-" * 70)

    passed = 0
    for text, label in TEST_INPUTS:
        valid, errors = validate_input(text)
        if valid:
            passed += 1
        status = "PASS" if valid else "FAIL"
        error_str = "; ".join(errors) if errors else "-"
        print(f"{label:<25} | {status:>5} | {error_str}")

    print(f"\n{passed}/{len(TEST_INPUTS)} inputs passed validation")
