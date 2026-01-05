# Pre-Commit Hook Refinements

## Changes Made

### 1. POLICY-001 Precision Improvements

**Problem:** Too many false positives - flagging any line containing "PolicyContext" and observational keywords.

**Solution:** Ultra-precise matching that only flags actual keyword arguments:

```python
# ❌ Previously flagged (FALSE POSITIVES):
from dbl_policy import PolicyContext  # "PolicyContext" contains substring
get_type_hints(PolicyContext)          # Type introspection
"PolicyContext.tenant_id"              # String literal

# ✅ Now only flags (TRUE POSITIVES):
PolicyContext(trace=execution_trace)   # Actual observational key passed
PolicyContext(execution=result)        # Actual observational key passed
```

**Implementation:**
- Only scans lines containing `PolicyContext(` constructor
- Uses word boundary regex: `\b{obs_key}\s*=(?!=)` to match keyword arguments
- Excludes `==` comparisons
- Ignores imports, type hints, string literals, method calls

### 2. BOUNDARY-003 Fix Hint Clarity

**Before:** "Import from dbl_core"  
**After:** "Use dbl_core.canonical.digest_bytes; never reimplement digest computation"

**Why:** The original hint was ambiguous - could be interpreted as "import dbl_core to implement digests", which violates the boundary. New hint explicitly states to use the existing function, not implement your own.

### 3. Rule Registry Consistency

**Verified:** All 6 rules appear in `DBL_HOOK_LIST_RULES` output:
- BOUNDARY-001 [ERROR]
- BOUNDARY-002 [ERROR]
- BOUNDARY-003 [ERROR]
- EVENT-001 [ERROR]
- POLICY-001 [ERROR]
- INVARIANT-001 [WARNING]

**Implementation:** 
- `decision_before_execution_matcher` function added
- INVARIANT-001 registered in RULES array
- Appears in list output

### 4. Unicode Encoding Fix

**Problem:** `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`

**Solution:** Added `encoding="utf-8", errors="ignore"` to subprocess calls reading staged files.

## Testing

### Before Refinement
```powershell
python .git\hooks\pre-commit
# 6 false positive violations in policy_adapter_dbl_policy.py
```

### After Refinement
```powershell
python .git\hooks\pre-commit
# ✓ Boundary validation passed
```

### Rule Listing
```powershell
$env:DBL_HOOK_LIST_RULES = "1"
python .git\hooks\pre-commit
# Shows all 6 rules with correct severity and hints
```

## Validation Accuracy

### POLICY-001 Test Cases

| Code Pattern | Flagged? | Correct? |
|--------------|----------|----------|
| `from dbl_policy import PolicyContext` | ❌ No | ✅ Yes (import) |
| `get_type_hints(PolicyContext)` | ❌ No | ✅ Yes (introspection) |
| `PolicyContext(tenant_id=x, inputs=y)` | ❌ No | ✅ Yes (valid keys) |
| `PolicyContext(trace=execution_trace)` | ✅ Yes | ✅ Yes (violation!) |
| `PolicyContext(execution=result)` | ✅ Yes | ✅ Yes (violation!) |
| `"PolicyContext.field"` | ❌ No | ✅ Yes (string literal) |

### Other Rules
- BOUNDARY-001/002/003: No changes, working as expected
- EVENT-001: No changes, working as expected
- INVARIANT-001: Now properly registered and listed

## Backwards Compatibility

- ✅ Windows PowerShell 5/7 compatible
- ✅ Git for Windows compatible
- ✅ Staged-only scanning (uses `git show :path`)
- ✅ No new dependencies
- ✅ Fail-safe: errors in hook allow commit (exit 0 on exception)

## Performance

No performance impact from precision improvements:
- Before: ~0.3s for 5 files
- After: ~0.3s for 5 files

Regex changes are minimal and don't add computational complexity.

---

**Date:** 2026-01-04  
**Hook Version:** Enhanced Python pre-commit (Windows-optimized)  
**File:** `.git\hooks\pre-commit` (160 lines)
