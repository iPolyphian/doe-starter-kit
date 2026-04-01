Run the DOE methodology testing framework.

Arguments:
- No arguments: run all scenarios
- `--quick`: fast subset for CI
- `--verbose`: detailed output per scenario
- `--scenario <name>`: run specific scenario

Run: `python3 execution/test_methodology.py $ARGUMENTS`

Present results clearly. If any scenario is WARN or FAIL, summarise what needs attention.
