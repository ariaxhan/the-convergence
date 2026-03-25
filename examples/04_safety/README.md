# Safety Examples

Patterns for input validation, confidence-based routing, budget tracking, and safe reward handling.

## Examples

| File | What It Shows |
|------|---------------|
| `input_validation.py` | Validate user inputs before passing to runtime (length, injection, empty) |
| `confidence_thresholds.py` | Extract confidence from text and route by threshold |
| `budget_tracking.py` | Track token usage against a budget with alerts |
| `reward_bounds.py` | Safe reward clamping and edge case handling |

## Key Concepts

- **Input Validation**: Defense-in-depth. Never trust user input. Check length, format, and content before processing.
- **Confidence Routing**: Use `extract_confidence()` and `detect_gap()` to decide whether to auto-respond, escalate to human, or ask for clarification.
- **Budget Tracking**: Token budgets prevent runaway costs. Track per-interaction and cumulative usage.
- **Reward Bounds**: Always clamp rewards to [0.0, 1.0]. Handle None, negative, and overflow values gracefully.

## Running

```bash
pip install -e .
python input_validation.py
python confidence_thresholds.py
python budget_tracking.py
python reward_bounds.py
```
