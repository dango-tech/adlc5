# ADLC5 consumer dogfood

Start with the [portable inventory consumer](consumer/README.md). It runs on the
Python standard library, has existing regression checks, and supplies six frozen
acceptance tasks with disposable preparation and result collection.

```bash
python3 dogfood/consumer/regression.py
python3 scripts/evaluation/demo-consumer.py --directory /tmp/adlc5-contract-demo
python3 scripts/tests/test-evaluation-pilot.py
```

The demo checks real init, check evidence, transition and process restoration. It
is scripted contract evidence, not a live host-agent quality/cost comparison.
For real delivery use a fresh host session with the prepared `HANDOFF.md` and
record the independent review, accounting and observation window honestly.

For an existing consumer project, initialize with:

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/consumer
/path/to/adlc5/scripts/init-feature.sh --feature demo-feature \
  --workspace /path/to/consumer
```

Select and copy the appropriate tiny, standard or high-risk policy, record risk,
and use `scripts/adlc5 transition` rather than editing progression fields.
`pilot` and the local navigator suggest host work; without a host executor they
return `needs_executor` rather than pretending to code. Reopen a fresh session
from feature files and `state get`/`pilot` output to test resume without history.

The [evaluation contract](../docs/evaluation.md) describes quality gates, frozen
comparisons and unknown accounting. High-risk approval is a genuine human step.
