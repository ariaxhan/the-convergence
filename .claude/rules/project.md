# Project Rules

## Tech Stack

- **Python 3.11+** - Use modern syntax (match statements, type unions, etc.)
- **Async by default** - All I/O is async. No blocking calls in hot paths.
- **Pydantic** - All data models. No raw dicts for structured data.
- **Type hints everywhere** - mypy --strict compatible
- **LiteLLM** - For all LLM provider abstraction

## File Organization

- `convergence/` - Main package, all source code
- `examples/` - Working examples (runnable, tested)
- `_meta/` - KERNEL artifacts (agentdb, context, plans)
- Tests in `tests/` following `test_{module}_{function}_{scenario}.py`

## Code Style

- Line length: 100 characters
- Ruff for linting (`ruff check`)
- Mypy strict mode (`mypy --strict`)
- Imports sorted: stdlib → third-party → local

## RL Terminology (MANDATORY)

Use correct RL terms in code and docs:
- "arm" not "option" (for MAB)
- "reward" not "score" (for feedback signals)
- "policy" not "strategy" (for decision rules)
- "episode" not "run" (for learning iterations)

## Architecture Invariants

- **Optimization loop is sacred**: MAB → Evolution → RL Meta → Storage → Repeat
- **Plugins extend, don't replace**: Core loop is fixed. New features = new plugins.
- **Async throughout**: No blocking in hot paths

## Testing

- Unit tests for all new components
- Property-based tests for evolutionary operators (Hypothesis)
- Integration tests for optimization loop changes
- All tests pass before merge

## Known Technical Debt

- **Regex patterns scattered** - ~20 regex patterns across 8 files (confidence.py, code_quality.py, text_quality.py, natural_language_processor.py). Should centralize into `convergence/patterns/` module.
- **Pydantic V1 config syntax** - Using deprecated `class Config` instead of `ConfigDict`. See rl_models.py, runtime.py.

## Never Do

- Never commit secrets or .env files
- Never delete _meta/ folder
- Never break the optimization loop invariant
- Never use "API optimization" as primary framing in docs
- Never block the async event loop with sync I/O
- Never use `asyncio.get_event_loop()` inside async functions - use `get_running_loop()`
