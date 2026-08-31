# self-learning-skills — governed autonomous learning

A hardened fork of `Kulaxyz/self-learning-skills` for AI agents that must improve
future task performance without turning every guess into permanent instructions.

The original project captured hard-won “golden paths.” This fork adds the missing
lifecycle around them:

```text
experience → candidate → exact artifact seal → 3 reviews → probation
           → external approval → activation → monitoring → revision/rollback
```

It works as an Agent Skill, Cursor rule, or portable `AGENTS.md` instruction set.
The included Python helper is standard-library only and runs on Windows, macOS, and
Linux.

## What “self-learning” means here

The agent can:

- retrieve relevant accepted lessons before similar work;
- capture observable outcomes, failures, corrections, and dead-ends;
- rank repeated uncovered capability gaps;
- draft or revise reusable procedures;
- bind reviews to exact artifact bytes;
- test candidates in probation;
- activate only through configured governance;
- monitor reliability and archive regressions.

It does **not** fine-tune model weights, invent authority, approve itself, or run an
unbounded background objective.

## Why the lifecycle matters

Saving every reflection creates noisy, contradictory, over-general rules. A useful
learning system must distinguish:

- unfinished work from durable knowledge;
- one-line facts from procedures;
- candidate hypotheses from accepted behavior;
- local evidence from global applicability;
- formatting checks from outcome evaluation;
- agent proposals from owner authority.

The architecture is documented in
[`skills/self-learning/references/architecture.md`](skills/self-learning/references/architecture.md).
Research sources and design synthesis are in
[`research-foundations.md`](skills/self-learning/references/research-foundations.md).

## Install

### Agent Skills CLI

```bash
npx skills add natural0101/self-learning-skills
```

Global install:

```bash
npx skills add natural0101/self-learning-skills -g
```

### Claude Code plugin

```text
/plugin marketplace add natural0101/self-learning-skills
/plugin install self-learning@self-learning-skills
```

### Manual

```bash
git clone https://github.com/natural0101/self-learning-skills.git

# Claude Code / Agent Skills clients
cp -R self-learning-skills/skills/self-learning .claude/skills/

# Cursor
mkdir -p .cursor/rules
cp self-learning-skills/.cursor/rules/self-learning.mdc .cursor/rules/

# Any agent that reads AGENTS.md
cat self-learning-skills/AGENTS.md >> AGENTS.md
```

Use your agent's actual skills directory when it differs.

## Quick start: auditable lifecycle

Initialize project-local state:

```bash
python skills/self-learning/scripts/learning_cycle.py init
```

Record an observable result:

```bash
python skills/self-learning/scripts/learning_cycle.py record \
  --task-id ci-184 \
  --outcome fail \
  --summary "stale build cache reproduced" \
  --evidence "ci:run-184" \
  --failure-pattern "stale build cache causes phantom type errors" \
  --dead-end "rerunning the same incremental build preserved the stale cache"
```

Rank recurring gaps:

```bash
python skills/self-learning/scripts/learning_cycle.py gaps
```

Create a quarantined candidate bound to exact bytes:

```bash
python skills/self-learning/scripts/learning_cycle.py candidate \
  --name clear-stale-build-cache \
  --source-event <event-id> \
  --failure-pattern "stale build cache causes phantom type errors" \
  --verification "clean build and targeted tests pass" \
  --boundary "Use only after the cache signature is observed; not as a default first step" \
  --expected-gain "skip one failed rebuild cycle" \
  --skill-path skills/clear-stale-build-cache
```

Submit three exact-version reviews:

```bash
python skills/self-learning/scripts/learning_cycle.py review \
  --candidate <candidate-id> --kind evidence --verdict pass \
  --reviewer evidence-reviewer --independent \
  --notes "source receipts, scope, and provenance pass"

python skills/self-learning/scripts/learning_cycle.py review \
  --candidate <candidate-id> --kind evaluation --verdict pass \
  --reviewer evaluation-reviewer --independent \
  --notes "baseline, held-out replay, and non-trigger cases pass"

python skills/self-learning/scripts/learning_cycle.py review \
  --candidate <candidate-id> --kind safety --verdict pass \
  --reviewer safety-reviewer --independent \
  --notes "secret, authority, injection, and rollback checks pass"
```

Promote to probation and record judged trials:

```bash
python skills/self-learning/scripts/learning_cycle.py promote --candidate <candidate-id>
python skills/self-learning/scripts/learning_cycle.py usage \
  --candidate <candidate-id> --outcome pass --evidence "eval:case-1"
```

Every artifact or semantic change must go through `revise`; old reviews and approval
are invalidated automatically.

## External approval

Default configuration uses `host-receipt` mode. The agent creates a request:

```bash
python skills/self-learning/scripts/learning_cycle.py approval-request \
  --candidate <candidate-id> --output approval-request.json
```

A host/owner-controlled process signs it with a secret unavailable to the agent:

```bash
SELF_LEARNING_APPROVAL_KEY='host-only-value' \
python skills/self-learning/scripts/learning_cycle.py sign-approval \
  --request approval-request.json \
  --approver owner-42 \
  --authority-ref owner-ui:approval-17 \
  --output approval-receipt.json
```

The receipt is then recorded:

```bash
SELF_LEARNING_APPROVAL_KEY='host-only-value' \
python skills/self-learning/scripts/learning_cycle.py approve \
  --candidate <candidate-id> --receipt approval-receipt.json
```

Do not expose the HMAC key to the agent. Strong deployments should replace the
reference receipt with a host API or public-key approval and make learning state
host-owned. `local-manual` mode is available only for explicitly configured
single-user experiments and is not a secure agent approval boundary.

## Lifecycle commands

| Command | Purpose |
|---|---|
| `init` | create state and default policy |
| `configure` | explicit operator config update with ledger receipt |
| `record` | append observable task experience |
| `gaps` | rank recurring uncovered failure patterns |
| `candidate` | create exact-artifact quarantined candidate |
| `review` | submit evidence/evaluation/safety review |
| `promote` | start probation after all reviews pass |
| `usage` | record judged probation/active use and reliability |
| `approval-request` | emit exact hashes for external approval |
| `sign-approval` | operator-only reference signer |
| `approve` | record signed or explicit local-manual approval |
| `revise` | seal new version and invalidate all old gates |
| `archive` | remove candidate from use, preserve history |
| `next-actions` | show exact lifecycle work currently needed |
| `verify-ledger` | verify local event hash chain |
| `audit` | audit artifacts, gates, probation, and activation |
| `validate-skill` | validate Agent Skill structure/safety markers |
| `report` | generate a human-readable lifecycle report |

State defaults to `.agent-learning/`, which is ignored by git. Commit only reviewed
skill artifacts and safe receipts intended for team sharing.

## Safety defaults

- three distinct independent review identities;
- exact artifact and semantic hashes on reviews/approval;
- symlink and candidate-ID path traversal rejection;
- secret-pattern blocking;
- probation before activation;
- owner/governor approval by default;
- protected domains never auto-activate;
- conservative smoothed reliability;
- failure-burst and low-reliability archive;
- revision invalidates every old gate;
- no private reasoning persistence;
- no always-running curriculum.

See [`SECURITY.md`](SECURITY.md) for the trust model and limitations.

## TeamON One

The TeamON profile preserves One's existing ownership model:

- Learning is a governed transition, not a new runtime/store/service.
- Context MCP remains the only generic lazy retrieval plane.
- Pending lessons stay outside Context until owner acceptance.
- Narrow lessons apply only to the exact selected World.
- Practice runs through owner-created Tasks and isolated WorkRuns.
- Active skills enter exact immutable checksum-verified composition.

Read [`skills/self-learning/references/teamon-one.md`](skills/self-learning/references/teamon-one.md).

## Validation

```bash
python -m compileall -q skills/self-learning/scripts
python -m unittest discover -s tests -v
python skills/self-learning/scripts/learning_cycle.py validate-skill \
  skills/self-learning --harvested
```

CI runs the suite on Ubuntu and Windows with supported Python versions.

## Repository layout

```text
.
├── AGENTS.md
├── .cursor/rules/self-learning.mdc
├── skills/self-learning/
│   ├── SKILL.md
│   ├── scripts/learning_cycle.py
│   ├── references/
│   └── assets/
├── tests/test_learning_cycle.py
├── docs/reviews/
└── .github/workflows/validate.yml
```

## Attribution

Forked from [`Kulaxyz/self-learning-skills`](https://github.com/Kulaxyz/self-learning-skills)
and released under the existing MIT license. The original golden-path concept and
upstream authorship remain credited; the governed lifecycle, evaluation, artifact
binding, approval, curriculum, tests, and TeamON profile are fork additions.
