# Contributing

Changes to a self-learning framework affect durable agent behavior. Use a pull
request and treat framework edits as protected-domain changes.

## Required workflow

1. Link the failure/capability gap and observable evidence.
2. State the applicability and non-applicability boundaries.
3. Preserve upstream attribution and Agent Skills compatibility.
4. Add or update tests for every behavior change.
5. Run local validation.
6. Perform the three repository review lenses below.
7. Document rollback and migration impact.

## Local checks

```bash
python -m compileall -q skills/self-learning/scripts scripts
python -m unittest discover -s tests -v
python skills/self-learning/scripts/learning_cycle.py validate-skill \
  skills/self-learning
python scripts/validate_repository.py
python -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('.').rglob('*.json')]"
```

## Repository triple review

### Architecture/evidence

- Does the change solve a named failure rather than add aspirational prose?
- Are claims supported by primary specifications, research, or repository
  evidence?
- Does it integrate with existing owners instead of creating duplicate runtime,
  memory, authority, or retrieval layers?
- Are scope, lifecycle, and migration explicit?

### Implementation/evaluation

- Are positive, negative, regression, tamper, and failure paths tested?
- Does behavior beat or safely extend the previous version?
- Are clean-context evaluation and objective checks possible?
- Are file writes atomic, errors explicit, and generated state auditable?

### Safety/compatibility/governance

- Are secrets, untrusted content, permissions, destructive actions, dependencies,
  and rollback covered?
- Can the change approve itself or weaken its own gate?
- Does it remain compatible with Agent Skills, Cursor, `AGENTS.md`, and the
  supported Python versions?
- Are upstream license/attribution and fork-specific install paths correct?

Any required fix means the review fails. Update the change and rerun all three
lenses on the new commit.

## Pull request contents

Include:

- problem and evidence;
- design and boundaries;
- changed files;
- tests/checks and exact results;
- three review results;
- security impact;
- rollback;
- known limitations.

Do not include private traces, secret values, or hidden chain-of-thought.
