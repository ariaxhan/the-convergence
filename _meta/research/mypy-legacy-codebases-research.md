# Mypy Best Practices for Legacy Python Codebases

**Date:** 2026-03-11  
**Context:** The Convergence has 196 type errors in legacy modules; new code must be strictly typed  
**Status:** RECOMMENDED SOLUTION IDENTIFIED

---

## TL;DR: The ONE Clean Solution

**Replace `ignore_errors = true` with per-module `disallow_untyped_defs = false`:**

```toml
[tool.mypy]
python_version = "3.11"
warn_unused_configs = true
exclude = ["convergence/generator/templates/"]

# ✅ Global: Require types in new code
disallow_untyped_defs = true
check_untyped_defs = true
warn_unused_ignores = true

# Ignore third-party stubs
[[tool.mypy.overrides]]
module = ["yaml", "aiofiles", "aiofiles.*"]
ignore_missing_imports = true

# ✅ Legacy modules: Only disable untyped defs
# Everything else (imports, unused ignores) still checked
[[tool.mypy.overrides]]
module = [
    "convergence.optimization.*",
    "convergence.legacy.*",
    "convergence.storage.sqlite",
    # ... (your list)
]
disallow_untyped_defs = false
```

**Why this works:** Allows unannotated functions in legacy code while catching import errors, enforcing new code quality, and preventing silent failures.

---

## Question 1: Per-Module Config Syntax

### Correct Syntax (pyproject.toml)

```toml
[tool.mypy]
# Global settings
python_version = "3.11"
strict = true  # or pick individual flags

# Multiple modules in one override block
[[tool.mypy.overrides]]
module = [
    "convergence.optimization.*",
    "convergence.legacy.*",
]
disallow_untyped_defs = false

# Single module with specific settings
[[tool.mypy.overrides]]
module = "convergence.storage.sqlite"
ignore_missing_imports = true

# Wildcard patterns (all match):
# - "foo.bar" → exact module
# - "foo.bar.*" → foo.bar and submodules
# - "site.*.migrations.*" → unstructured (stars = zero+ components)
```

### Precedence (Highest to Lowest)
1. Inline `# type: ignore` comments
2. Concrete module names (`foo.bar`)
3. Unstructured wildcards (`site.*.migrations.*`)
4. Structured wildcards (`foo.bar.*`)
5. Command line
6. Global `[tool.mypy]` section

---

## Question 2: Optional Imports Pattern (ConvexStorage = None)

### ❌ DON'T DO THIS
```python
# Causes: "Incompatible types in assignment (expression has type 'None', variable has type 'Module')"
try:
    import convex
    ConvexStorage = convex.ConvexStorage
except ImportError:
    ConvexStorage = None  # ← Type error!
```

### ✅ DO THIS (Recommended)
```python
from typing import TYPE_CHECKING

# Boolean sentinel (Mypy accepts this without errors)
try:
    import convex
    HAVE_CONVEX = True
except ImportError:
    HAVE_CONVEX = False

# For type hints, use TYPE_CHECKING guard
if TYPE_CHECKING:
    from convex import ConvexStorage
else:
    ConvexStorage = None

# Usage
def get_storage():
    if HAVE_CONVEX:
        return convex.ConvexStorage()
    else:
        return None
```

### ✅ ALTERNATIVE (Also Works)
```python
# Use # type: ignore (but less explicit)
try:
    import convex
    ConvexStorage = convex.ConvexStorage
except ImportError:
    ConvexStorage = None  # type: ignore[assignment]
```

**Why the boolean sentinel works:** Mypy infers `True` and `False` correctly in both branches. No type conflict.

---

## Question 3: ignore_errors vs Specific Error Codes

### Comparison

| Strategy | Use Case | Pros | Cons |
|----------|----------|------|------|
| `ignore_errors = true` | Entire module too broken | Quick win | Hides import errors, unused ignores, all checks |
| `disallow_untyped_defs = false` | Legacy code, new code should be strict | Selective relaxation | Still catches imports, unused ignores |
| `disable_error_code = [...]` | Specific errors only | Surgical control | More maintenance |
| `# type: ignore[code]` | Single lines | Precise | Requires enumeration |

### RECOMMENDATION FOR YOUR CASE

**Use `disallow_untyped_defs = false` per-module** because:
1. Allows unannotated functions (fixes 196 errors)
2. Still enforces imports exist (`import-not-found` not ignored)
3. Still warns about unused `# type: ignore` comments
4. New code typed at module boundary gets checked

```toml
# ✅ Better approach
[[tool.mypy.overrides]]
module = ["convergence.legacy.*"]
disallow_untyped_defs = false  # Allow untyped funcs
check_untyped_defs = true      # But check bodies if they exist

# ❌ Avoid this
[[tool.mypy.overrides]]
module = ["convergence.legacy.*"]
ignore_errors = true  # Silences EVERYTHING
```

### Error Codes (if you need selective disabling)

Common codes for legacy code:
- `arg-type` - Function argument type mismatch
- `return-value` - Return type mismatch
- `name-defined` - Name not defined
- `union-attr` - Union doesn't have attribute
- `import-not-found` - Module not found
- `unused-ignore` - Unnecessary `# type: ignore`

**Best practice:** Use `warn_unused_ignores = true` to catch stale ignores as code is fixed.

---

## Question 4: Antipatterns to Avoid

### Antipattern 1: `ignore_errors = true` Globally

```toml
[tool.mypy]
ignore_errors = true  # ❌ Silences EVERYTHING
```

**Why it fails:** Import errors, unused ignores, all checks disappear. New code quality degrades.

**Fix:** Use global `disallow_untyped_defs = true`, override selectively.

---

### Antipattern 2: Inverting with `ignore_errors = true` Globally

```toml
[tool.mypy]
ignore_errors = true  # Global default

[[tool.mypy.overrides]]
module = "mycode.core"
ignore_errors = false  # Try to re-enable
```

**Why it fails:** Mypy doesn't cleanly "re-enable" types. Complex precedence. Hard to maintain.

**Fix:** Start strict, selectively relax:

```toml
[tool.mypy]
disallow_untyped_defs = true  # Strict by default

[[tool.mypy.overrides]]
module = "mycode.legacy"
disallow_untyped_defs = false  # Relax only legacy
```

---

### Antipattern 3: Missing `warn_unused_ignores`

```toml
[tool.mypy]
disallow_untyped_defs = true
# Missing: warn_unused_ignores
```

**Why it fails:** As code is fixed, old `# type: ignore` comments accumulate. Lint noise.

**Fix:**

```toml
[tool.mypy]
disallow_untyped_defs = true
warn_unused_ignores = true  # ← Clean up as you go
show_error_codes = true     # ← Required for this to work
```

---

### Antipattern 4: No Per-Module Strategy

```toml
[tool.mypy]
# Global strict mode applied to EVERYTHING
strict = true
```

**Why it fails:** 196 errors in legacy code all reported at once. Team overwhelmed. No clear path.

**Fix:** Establish layers:

```toml
[tool.mypy]
# Layer 1: High-priority (core, types, plugins)
disallow_untyped_defs = true
check_untyped_defs = true

# Layer 2: Medium-priority (evaluators, storage)
[[tool.mypy.overrides]]
module = ["convergence.evaluators.*", "convergence.storage.*"]
disallow_untyped_defs = false

# Layer 3: Low-priority (legacy, generator)
[[tool.mypy.overrides]]
module = ["convergence.legacy.*", "convergence.generator.*"]
disallow_untyped_defs = false
```

Then migrate modules FROM Layer 3 → Layer 2 → Layer 1 as they're touched.

---

### Antipattern 5: Not Using TYPE_CHECKING for Optional Imports

```python
# Without TYPE_CHECKING guard
try:
    from optional_lib import Foo
except ImportError:
    Foo = None  # Type error
```

**Why it fails:** Mypy rejects `None` assignment to `ModuleType`. Runtime works, type checking fails.

**Fix:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optional_lib import Foo
else:
    try:
        from optional_lib import Foo
    except ImportError:
        Foo = None
```

---

## Validation Protocol (Before Merging)

```bash
# 1. Check mypy passes
mypy convergence --show-error-codes

# 2. Verify no unused ignores exist
grep -r "type: ignore" convergence/ | wc -l

# 3. Ensure legacy modules still build
python -c "import convergence; print('OK')"

# 4. Run tests
pytest tests/
```

---

## Implementation Path (Recommended)

1. **Phase 1: Replace `ignore_errors = true` with `disallow_untyped_defs = false`**
   - Keeps same behavior (196 errors still allowed)
   - Adds import checking back
   - Adds unused ignore warnings

2. **Phase 2: Add global flags**
   - `warn_unused_ignores = true`
   - `show_error_codes = true`
   - `check_untyped_defs = true`

3. **Phase 3: Module-by-module migration**
   - Pick one module, set `disallow_untyped_defs = true`
   - Fix 5-10 errors
   - Move to next module

4. **Phase 4: Remove per-module override**
   - Delete from override list when done
   - Module is now strictly typed

---

## Sources

- [Mypy Configuration File - Official Docs](https://mypy.readthedocs.io/en/stable/config_file.html)
- [Using Mypy with Existing Codebases](https://mypy.readthedocs.io/en/stable/existing_code.html)
- [Common Issues and Solutions](https://mypy.readthedocs.io/en/stable/common_issues.html)
- [Error Codes Documentation](https://mypy.readthedocs.io/en/stable/error_codes.html)
- [Python Type Hints: Optional Imports - Adam Johnson](https://adamj.eu/tech/2021/12/29/python-type-hints-optional-imports/)
- [Professional-Grade Mypy Configuration - Wolt Careers](https://careers.wolt.com/en/blog/tech/professional-grade-mypy-configuration)
