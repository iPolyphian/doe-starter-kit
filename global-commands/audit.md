Run a full claim audit: `python3 execution/audit_claims.py`

Show the complete script output, then print a bordered result box summarising the outcome. **Generate the box programmatically** — collect all content lines into a list, find the max length, then use `.ljust(max_len)` to pad every line to the same width before adding Unicode box-drawing borders (`┌─┐`, `└─┘`, `│`). Never hand-pad the box. Content inside borders must be ASCII-only (no emojis).

Pick the matching status:

**All clear:**
```
✅ AUDIT PASSED
┌──────────────────────────────────────────────────────┐
│  AUDIT RESULT                                        │
├──────────────────────────────────────────────────────┤
│  [X] PASS, 0 WARN, 0 FAIL -- all clear              │
│  App: vX.Y.Z | Governed docs: N | Tasks: N           │
└──────────────────────────────────────────────────────┘
```

**Issues found:**
```
⚠️  AUDIT ISSUES
┌──────────────────────────────────────────────────────┐
│  AUDIT RESULT                                        │
├──────────────────────────────────────────────────────┤
│  [X] PASS, [Y] WARN, [Z] FAIL                       │
│  [1 line per FAIL/WARN — plain English explanation]  │
│  App: vX.Y.Z                                         │
└──────────────────────────────────────────────────────┘
```

If there are FAIL items, explain each in plain English inside the box and suggest how to fix. WARN items can be noted for next session.

After showing results, save findings to `.tmp/last-audit.txt` (the script does this automatically).
