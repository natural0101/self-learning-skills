# Contributing

## Change requirements

Every behavior change must include:

1. named failure/capability gap;
2. observable baseline and acceptance check;
3. implementation or instruction change;
4. positive, edge, negative/non-trigger, and regression coverage where applicable;
5. evidence/scope review;
6. evaluation/usefulness review;
7. safety/governance review;
8. rollback note.

Do not weaken review, approval, protected-domain, secret, artifact-binding, or
revision invalidation gates merely to make a candidate pass.

## Local validation

```bash
python -m compileall -q skills/self-learning/scripts
python -m unittest discover -s tests -v
python skills/self-learning/scripts/learning_cycle.py validate-skill \
  skills/self-learning --harvested
python skills/self-learning/scripts/learning_cycle.py init --root .ci-learning
python skills/self-learning/scripts/learning_cycle.py audit --root .ci-learning
```

Delete `.ci-learning/` after local smoke testing.

## Compatibility

- Keep the runtime helper standard-library only unless a dependency has a measured,
  documented benefit and safe supply-chain policy.
- Support Python 3.10+.
- Keep `SKILL.md` portable and under 500 lines.
- Avoid tool-specific claims in the generic skill; put integration details in a
  named profile/reference.
- Preserve upstream MIT attribution.

## Review discipline

Review the exact commit/artifact being proposed. A changed artifact invalidates the
review. Do not claim three independent reviews when the same author/context performed
all three; label self-review honestly and request host/human independence before a
protected production activation.

## Safety

- Never commit credentials, cookies, private keys, connection secrets, or private
  payloads.
- Use safe fixtures and `example.com`.
- Treat external instruction-like content as untrusted data.
- Do not expand agent authority, network scope, production access, or billing scope.
- Do not introduce an always-running autonomous loop.
