# Changelog

## 2.0.0 — 2026-08-31

### Added

- Full governed lifecycle: experience, candidate quarantine, three reviews,
  probation, approval, activation, monitoring, revision, archive, and rollback.
- Standard-library lifecycle CLI with hash-chained event ledger.
- Exact artifact hashing, semantic subject hashing, symlink rejection, and strict
  candidate-ID validation.
- Host-signed approval receipts and explicit insecure local-manual mode.
- Conservative reliability scoring, activation thresholds, failure-burst archive,
  active-skill cap, and protected-domain policy.
- Recurring-gap ranking and lifecycle next-action queue.
- Skill structure/secret/evidence marker validation.
- Bounded autonomous curriculum, research synthesis, review protocol, security
  model, TeamON One integration profile, templates, and CI.
- Cross-platform unit coverage for lifecycle, tamper detection, artifact drift,
  review independence, approval binding, probation, activation, rollback, gaps,
  reports, and validators.

### Changed

- Self-learning is now a mandatory prepare → perform → judge → learn loop for
  substantial tasks, not only post-hoc golden-path capture.
- Durable promotion requires positive and negative applicability boundaries,
  baseline/replay evaluation, provenance, three independent reviews, probation,
  and external governance.
- README, AGENTS.md, Cursor rule, Agent Skill, skills registry, and Claude plugin
  metadata now describe the hardened fork.

### Security

- Secret-pattern rejection covers common API tokens, private keys, JWTs,
  authorization credentials, and credential-bearing URIs.
- Candidate bytes cannot change after review without a version reset.
- Protected identity/mission/authority/policy/credential/billing/production and
  learning-governance changes cannot auto-activate.

### Attribution

Fork additions build on the original MIT-licensed golden-path project by Kulaxyz.
