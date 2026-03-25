# Cookbook Style Guide

Every example in this cookbook follows this template for consistency and discoverability.

## File Template

```python
"""
<Title>

What this demonstrates:
- Concept 1: brief explanation
- Concept 2: brief explanation

Prerequisites:
- pip install -e .
- (list any optional deps)

Suggested prompts / test inputs:
- "Try running with X"
- "Modify Y to see Z"
"""

# --- Configuration ---
import os
from convergence import ...

# --- Setup ---
# (Initialize objects, configure runtime)

# --- Execution ---
if __name__ == "__main__":
    # Demo code that produces visible output
    ...
```

## Rules

1. **Docstring first** - IDE-discoverable, explains *what* and *why* before code
2. **Three sections** - Configuration, Setup, Execution (comment-separated)
3. **`if __name__ == "__main__":` always** - importable without side effects
4. **Under 80 lines** of code (excluding docstring)
5. **Environment variable defaults** - never hardcode API keys
6. **Visible output** - `print()` something useful so the user sees it work
7. **Self-contained** - runs independently, no cross-example imports
8. **Suggested inputs** - tell users what to try in the docstring

## Naming

- Files: `snake_case.py`
- Directories: `NN_topic_name/` (numbered for ordering)
- Each directory has its own `README.md`

## What NOT to Do

- No incomplete code (every example must run)
- No hardcoded API keys or secrets
- No imports from other examples
- No multi-file examples in quickstart (save those for `01_apps/`)
