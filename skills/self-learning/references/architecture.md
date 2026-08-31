# Architecture: governed skill evolution

## Purpose

This repository implements **operational self-improvement**: an agent can preserve
verified experience as external skills and improve future task performance. It does
not update model weights and cannot manufacture judgment, authority, or evidence.

## Control loop

```text
authorized trigger
  → retrieve relevant accepted lessons
  → define outcome + baseline + acceptance check
  → perform bounded work
  → judge observable result
  → route one learning signal
  → draft exact candidate artifact
  → seal artifact hash + semantic subject hash
  → evidence review
  → evaluation review
  → safety review
  → probation on judged cases
  → external owner/governor approval
  → activate exact immutable version
  → monitor → keep | revise | archive | rollback
```

The lifecycle intentionally separates generation from judgment. A candidate may
propose content, but cannot make its own proposal authoritative.

## State machine

| State | Meaning | Allowed exits |
|---|---|---|
| `draft` | Incomplete, editable, not loadable | quarantined, archived |
| `quarantined` | Exact bytes sealed; awaiting three reviews | probationary, revised, archived |
| `probationary` | Reviews passed; evaluated only in bounded judged trials | active, revised, archived |
| `active` | Approved exact version may be retrieved/used | revised, archived |
| `archived` | Retained for provenance, excluded from use | revised as a new version |

Every byte or semantic change creates a new version and clears reviews, approval,
trials, and reliability. This prevents “review one file, activate another.”

## Data model

### Experience event

An event stores observable task metadata:

- task ID and scope;
- `pass | partial | fail`;
- short result summary;
- safe evidence references;
- named failure pattern;
- ruled-out dead-ends;
- bounded metrics;
- source-trust classification.

It must not contain private chain-of-thought, credentials, raw private payloads, or
claims unsupported by a check.

### Candidate subject

The subject hash binds:

- candidate ID and version;
- name, risk, and scope;
- source event IDs;
- failure pattern and verification;
- applicability/exclusion boundary;
- expected gain;
- artifact path and deterministic artifact hash;
- protected-domain declarations.

Reviews and approval receipts repeat this hash. A mismatch blocks transition.

### Artifact hash

Files are hashed deterministically by relative path, byte size, and SHA-256.
Symlinks are rejected to prevent a sealed path from resolving to changing or
out-of-scope content. Paths are normalized; candidate IDs use a strict format to
block path traversal.

### Ledger

The JSONL event ledger is a local SHA-256 hash chain. Atomic rewrites prevent a
partial append from silently becoming valid. This is **tamper-evident only**: an
actor with unrestricted write access can replace the script, state, and complete
chain. Put the state under host-controlled permissions and export/anchor receipts
when stronger assurance is required.

## Review gates

Three different concerns must pass independently:

1. evidence/scope;
2. evaluation/usefulness;
3. safety/governance.

The reference CLI verifies distinct reviewer IDs and an independence assertion. A
host is responsible for actual identity, model/session, and context separation.
No local JSON field can prove organizational independence.

## Probation and reliability

The default estimate is a Beta(1,1) posterior mean:

```text
reliability = (passes + 1) / (trials + 2)
```

It avoids treating one lucky pass as certainty. Default activation requires at
least three trials and reliability ≥ 0.80. The policy also archives on a configured
failure burst or sustained reliability below the archive threshold.

Evaluation must include negative/non-trigger cases. A skill that solves its target
but triggers everywhere is a regression.

## Approval boundary

Default mode is `host-receipt`:

1. the agent emits an approval request bound to exact hashes;
2. a host/owner-controlled process signs it outside agent authority;
3. the CLI verifies the signature during approval recording;
4. activation uses only the bound receipt.

The included HMAC mechanism is appropriate only when the signing key is injected
for the approval operation and is never visible to the agent. A deployment with
stronger isolation should replace it with a host API or public-key signature and
make the learning directory host-owned/read-only to the agent.

`local-manual` exists for single-user experimentation. It is an explicit weakening,
not a secure approval channel.

## Retrieval and pruning

Active knowledge is useful only when selectively retrieved. Index descriptions and
boundaries, not entire histories. Prefer one strong skill over many overlapping
rules. Periodically:

- merge duplicates;
- archive stale versions;
- remove low-value one-line skills;
- narrow over-triggering descriptions;
- update changed tool/API assumptions;
- keep archived receipts outside normal retrieval.

## Trust boundaries

| Boundary | Owner |
|---|---|
| Task authorization | user/host |
| Identity, mission, policy, permissions | user/host; never learned autonomously |
| Candidate generation | agent |
| Objective/domain judgment | test, evaluator, or owner |
| Review identity/context separation | host |
| Approval | owner/governor host |
| Skill installation/composition | host/product |
| Secrets | secret manager / approved connector |
| Learning ledger retention | host/project |

## Explicit non-goals

- hidden model fine-tuning;
- autonomous permission growth;
- self-modifying safety gates;
- replacing canonical documentation with memories;
- treating every conversation as training data;
- permanent background activity;
- using user silence as reward;
- allowing an agent to sign its own approval.
