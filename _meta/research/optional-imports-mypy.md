# Optional Imports with Type Checking in Python

**Status:** Researched | **Date:** 2026-03-11 | **Scope:** Mypy type-safe optional imports

---

## The Problem

Assigning `None` to an imported module in try/except blocks causes mypy errors:

```python
try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # ERROR: Cannot assign to a type
```

**Error codes seen:**
- `error: Cannot assign to a type` (mypy strict mode)
- `error: Incompatible types in assignment` (alternate form)
- `error[assignment]` (specific error code)

---

## Recommended Solution: TYPE_CHECKING + try/except + cast()

**Pattern:** Use `typing.TYPE_CHECKING` to separate static analysis from runtime.

### Option A: TYPE_CHECKING with separate runtime block (RECOMMENDED)

```python
from typing import TYPE_CHECKING

# Type-checking block: loaded by mypy, ignored at runtime
if TYPE_CHECKING:
    from convergence.storage.convex import ConvexStorage
else:
    # Runtime block: executed by Python interpreter
    try:
        from convergence.storage.convex import ConvexStorage
        _CONVEX_AVAILABLE = True
    except ImportError:
        _CONVEX_AVAILABLE = False
        ConvexStorage = None  # type: ignore[assignment]
```

**Why this works:**
- Mypy evaluates `if TYPE_CHECKING:` as true, seeing the import type information
- Python interpreter sees `TYPE_CHECKING` as False at runtime, skips the if block
- Runtime try/except handles missing modules gracefully
- `type: ignore[assignment]` suppresses the specific error mypy still sees

**Minimal example (1 import block):**

```python
from typing import TYPE_CHECKING

try:
    from convergence.storage.convex import ConvexStorage
except ImportError:
    if not TYPE_CHECKING:
        ConvexStorage = None  # type: ignore[assignment]
```

### Option B: cast(Any, None) (Works reliably across environments)

```python
from typing import cast, Any

try:
    from convergence.storage.convex import ConvexStorage
except ImportError:
    ConvexStorage = cast(Any, None)
```

**Why this works:**
- Explicitly types the None assignment as `Any`, which mypy accepts
- No `type: ignore` needed
- More reliable when running in different environments (local vs CI)
- Used in real projects (Django, dotenv patterns)

### Option C: Boolean flag + type: ignore[misc, assignment]

```python
try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # type: ignore[misc, assignment]
```

**Why this works:**
- Same as current code, with explicit error codes ignored
- Least elegant but most pragmatic
- Works immediately without refactoring

---

## Real-World Examples

### pydantic (Type definitions with TYPE_CHECKING)

Pydantic uses TYPE_CHECKING for conditional imports of optional typing features:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optional_module import OptionalType
```

### httpx (Conditional imports in blocks)

```python
if TYPE_CHECKING:
    import ssl
else:
    try:
        import ssl
    except ImportError:
        ssl = None  # type: ignore
```

### Current codebase (convergence/storage/__init__.py, line 60)

Already uses the pattern correctly for PostgreSQL:

```python
try:
    from convergence.storage.postgresql import PostgreSQLRuntimeStorage
    _POSTGRESQL_AVAILABLE = True
except ImportError:
    _POSTGRESQL_AVAILABLE = False
    PostgreSQLRuntimeStorage = None  # type: ignore[misc, assignment]
```

This is the model to follow for Convex.

---

## Pitfalls & Solutions

### Pitfall 1: Mypy sees None assignment before module type
**Symptom:** `error: Cannot assign to a type` on the `= None` line
**Why:** Mypy infers the module's type from import, can't reassign None to it
**Fix:** Use `# type: ignore[assignment]` on that line OR use `cast(Any, None)`
**Source:** [mypy issue #1393 - Import errors in try/except](https://github.com/python/mypy/issues/1393)

### Pitfall 2: TYPE_CHECKING block imports aren't available at runtime
**Symptom:** `NameError: name 'ConvexStorage' is not defined` in except block
**Why:** `if TYPE_CHECKING:` is False at runtime, import is skipped
**Fix:** Keep the try/except in runtime execution path, use TYPE_CHECKING only for type analysis
**Prevention:** Always pair TYPE_CHECKING with a runtime try/except or explicit None assignment
**Source:** [mypy common_issues documentation](https://mypy.readthedocs.io/en/stable/common_issues.html)

### Pitfall 3: TYPE_CHECKING branch evaluated differently local vs CI
**Symptom:** Type errors locally but not in CI (or vice versa)
**Why:** Different mypy configurations, different import availability
**Fix:** Use `cast(Any, None)` for consistency OR ensure both paths have identical type guards
**Source:** [mypy issue #10512 - module = None optional import](https://github.com/python/mypy/issues/10512)

### Pitfall 4: Forgetting to check availability before use
**Symptom:** `AttributeError: 'NoneType' object has no attribute 'method'`
**Why:** Code assumes optional module is available without checking flag
**Fix:** Always guard usage with `if _MODULE_AVAILABLE:` or `if module is not None:`
**Prevention:** Type narrowing with `if ConvexStorage is not None:` helps mypy verify safety
**Source:** [technetexperts guide on optional imports](https://www.technetexperts.com/mypy-optional-module-import-error/)

### Pitfall 5: Using only type: ignore without understanding why
**Symptom:** Suppresses errors but leaves code fragile
**Why:** `# type: ignore` is a band-aid that masks the real problem
**Fix:** Use `# type: ignore[specific_code]` (e.g., `[assignment]`) to be explicit about what's ignored
**Prevention:** Always comment why the ignore is needed
**Source:** [mypy config documentation - type ignore codes](https://mypy.readthedocs.io/en/stable/config_file.html)

---

## Recommended Implementation for Convergence

### For convergence/storage/__init__.py (line 47-52):

**Current code has the error:**
```python
try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # ERROR HERE
```

**Solution 1 (Match existing PostgreSQL pattern):**
```python
try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # type: ignore[misc, assignment]
```

**Solution 2 (Most type-safe with TYPE_CHECKING):**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from convergence.storage.convex import ConvexStorage

try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # type: ignore[assignment]
```

**Solution 3 (Most robust with cast):**
```python
from typing import cast, Any

try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = cast(Any, None)
```

**Recommendation:** Use Solution 1 (matching line 60 pattern already in codebase) for consistency. Add `# type: ignore[misc, assignment]` to line 52.

---

## Alternatives Evaluated

| Approach | Lines | Dependencies | Pros | Cons | Complexity |
|----------|-------|--------------|------|------|------------|
| `# type: ignore[misc, assignment]` | 1 | None | Immediate fix, matches existing code | Suppresses error rather than solving | Trivial |
| `cast(Any, None)` | 3 | `typing.cast` | Type-safe, reliable across environments | Slightly more verbose | Low |
| `TYPE_CHECKING` + runtime block | 6-8 | `TYPE_CHECKING` constant | Most type-correct, clear intent | Requires duplication of import | Low |
| `.pyi` stub file | 10+ | Separate file | Most explicit, completely solves typing | Requires maintenance, added files | Moderate |

**Selected:** Solution 1 (`type: ignore[misc, assignment]`) because:
1. Already used in codebase (line 60) for PostgreSQL
2. Consistency matters for team patterns
3. Zero additional complexity
4. Pragmatic, proven approach in mypy ecosystem

---

## References

- [Adam Johnson - Python Type Hints Optional Imports](https://adamj.eu/tech/2021/12/29/python-type-hints-optional-imports/)
- [MyPy Common Issues - TYPE_CHECKING](https://mypy.readthedocs.io/en/stable/common_issues.html)
- [MyPy Issue #1393 - ImportError blocks in try/except](https://github.com/python/mypy/issues/1393)
- [MyPy Issue #10512 - module = None assignment](https://github.com/python/mypy/issues/10512)
- [TechNetExperts - MyPy Optional Module Import Error Fix](https://www.technetexperts.com/mypy-optional-module-import-error/)
- [Real Python - ImportError exceptions](https://realpython.com/ref/builtin-exceptions/importerror/)
- [MyPy Configuration - Error codes](https://mypy.readthedocs.io/en/stable/error_code_list2.html)

---

## Action Items

1. **Fix convergence/storage/__init__.py:52** - Add `# type: ignore[misc, assignment]` comment
2. **Verify mypy passes** - Run `mypy --strict convergence/storage/` to confirm
3. **Document pattern** - Add note to `_meta/reference/` about optional imports in project
4. **Review consistency** - Check if other optional imports in codebase follow same pattern

