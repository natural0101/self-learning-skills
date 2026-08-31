# Security policy and trust model

## Scope

This project persists agent experience and can influence future behavior. Treat its
state and active skills as security-sensitive configuration.

## Core threat model

The lifecycle is designed to reduce:

- secret leakage into committed skills;
- prompt-injection persistence from external content;
- over-generalization from one task or repository;
- candidate self-review/self-approval;
- “review one artifact, activate another” substitution;
- path traversal and symlink substitution;
- unbounded background objectives;
- unsafe auto-activation in protected domains;
- silent regressions and stale skills.

## Required deployment controls

1. Keep `.agent-learning/` under host-controlled permissions. The agent should use
   the lifecycle API/CLI, not unrestricted direct writes to state.
2. Keep approval signing material outside agent-visible environment and tools.
3. Enforce reviewer identity, session, and context separation in the host.
4. Install only exact reviewed artifact hashes/checksums.
5. Keep secrets in a secret manager or approved connector; skills store pointers.
6. Run candidate practice in reversible sandboxes with bounded network/tool access.
7. Protect identity, mission, policy, permissions, credentials, billing, production
   write authority, and learning governance from autonomous activation.
8. Retain rollback/supersession receipts outside ordinary skill retrieval.

## Approval modes

### `host-receipt` (default)

The candidate emits an exact approval request. A host-controlled operation signs it.
The reference CLI uses HMAC-SHA256.

HMAC is symmetric: any process with the verification key can also create signatures.
Therefore inject the key only into the owner/host approval operation and do not make
it available to the agent. For stronger isolation, replace the reference signer
with a host API or public-key signature verifier.

### `local-manual`

This mode records an explicit local operator assertion but does not cryptographically
separate the operator from an agent with the same filesystem/process authority. Use
only in single-user experiments. Never present it as secure autonomous approval.

## Hash-chain limitation

The JSONL ledger links events with SHA-256 and detects accidental/partial edits or
unsophisticated tampering. It is not an append-only external log. An unrestricted
writer can replace the program, state, and complete chain. Export/anchor receipts or
use an external append-only store when adversarial tamper resistance is required.

## Secret scanner limitation

The scanner blocks common key/token/private-key/credential-URI patterns. It is a
heuristic, not a complete secret detector. Continue using repository secret scanning,
least-privilege credentials, rotation, and human/host review.

Do not report a suspected leak by pasting the secret into an issue, PR, review, test,
or skill. Revoke/rotate it first and report only redacted metadata.

## Prompt-injection persistence

Any instruction-like text from web pages, emails, documents, repositories, issue
comments, tool output, retrieved memory, or candidate content is untrusted unless it
comes from the applicable owner/system authority. It may be stored as quoted evidence
when necessary, but cannot change standing rules, approval, permissions, identity,
mission, or safety policy.

## Artifact binding

Reviews and approval bind candidate version, semantic subject hash, and deterministic
artifact hash. Symlinks are rejected. Any change requires `revise`, which clears old
reviews, approval, trial counters, and reliability.

## Vulnerability reporting

Use GitHub's private security-advisory channel for this repository when available.
Do not open a public issue containing exploit details, private data, or credentials.
Include a redacted reproduction, affected version/commit, expected boundary, and
suggested containment.
