Read the user's CLAUDE.md to understand the project structure, then execute the appropriate trace mode below.

## Mode detection

If ARGUMENTS contains a file name or module name → **Single module mode**
If ARGUMENTS contains `--integration` → **Integration mode**
If ARGUMENTS contains `--all` → **Full sweep mode** (runs single module on every JS file, then integration)
If ARGUMENTS is empty → ask the user which module to trace

ARGUMENTS: $ARGUMENTS

---

## Single module mode

Trace one module deeply. This is the probabilistic layer — you're reading code and reasoning about correctness, not running a compiler.

1. **Read the full module file.** No selective reading — logic bugs often live in the parts you'd skip.
2. **Identify all exported/public functions.** Map the surface area that other modules depend on.
3. **For each function, trace the logic path:**
   - Inputs → transforms → outputs
   - Follow every branch (if/else, switch, ternary)
   - Check: what happens with null/undefined inputs?
   - Check: what happens with empty arrays/objects?
   - Check: any division that could produce NaN or Infinity?
   - Check: any array access that could be out of bounds?
   - Check: any property access on potentially undefined objects?
4. **Check against the spec.** If a plan file or contract exists for this module, compare the implementation to the intended behaviour. Flag deviations.
5. **Check for common problems:**
   - Dead code (unreachable after return/throw/break)
   - Hardcoded magic numbers without explanation
   - Silent failures (catches error but returns default without logging)
   - Functions that always return the same value regardless of input
   - Off-by-one errors in loops or slicing
   - String comparison where numeric comparison was intended (or vice versa)
   - Mutation of input parameters that callers might not expect

6. **Output findings** as a numbered list with severity tags:
   - **BUG** — incorrect behaviour that will produce wrong results
   - **WARN** — risky pattern that could cause problems under certain conditions
   - **INFO** — style, clarity, or minor improvement suggestion

Format each finding as:
```
N. [BUG/WARN/INFO] function_name() — description of the issue
   Location: filename:line_number (approximate)
   Impact: what goes wrong and when
   Fix: suggested correction
```

If zero findings: report "Code trace clean — no issues found in [module]."

---

## Integration mode

Trace data flow across module boundaries. Catches "works alone, broken together" bugs.

1. **Map the module dependency graph.** Which modules produce data that other modules consume? Focus on:
   - Functions called across files (global scope)
   - Data objects built in one file and read in another
   - Shared state variables modified by multiple files
   - Settings/config values read in multiple places

2. **For each producer-consumer pair, check shape compatibility:**
   - Does the producer's return type/shape match what the consumer expects?
   - Are property names consistent? (e.g., `majority` vs `margin` vs `majPct`)
   - Are null/undefined values handled at the boundary?
   - If the producer can return an empty array, does the consumer handle that?

3. **Check settings consistency:**
   - Are user settings (role, party, constituency, region) read the same way across all modules?
   - Do all modules handle the "no settings yet" case?
   - Are there modules that cache a setting value and don't update when settings change?

4. **Check initialization order:**
   - Are there modules that assume another module has already initialized?
   - Are there circular dependencies?
   - What happens if a module's init function is called twice?

5. **Output findings** using the same BUG/WARN/INFO format as single module mode.

---

## After the trace

- Present all findings to the user
- For BUG-level findings: offer to fix immediately
- For WARN-level findings: explain the risk and let the user decide
- For INFO-level findings: mention briefly, don't action unless asked

If this was triggered automatically after a data-layer step, prefix the output with:
"Code trace for [module] — N findings:" or "Code trace clean — no issues found."
