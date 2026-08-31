# self-learning-skills v2

**A governed continuous-learning lifecycle for AI agents.**

Most "self-learning" prompts save a successful answer and call it a skill. That
creates durable guesses, duplicate rules, scope drift, and unsafe instructions.
This fork turns learning into an auditable lifecycle:

```text
retrieve relevant lessons
→ perform a real task
→ judge observable evidence
→ create a quarantined candidate
→ evidence review
→ evaluation review
→ safety/governance review
→ probation on real/replay tasks
→ owner-governed activation
→ measured reuse
→ refine / merge / narrow / archive / rollback
```

It works as an Agent Skill, a Cursor rule, or portable `AGENTS.md` instructions.
A standard-library Python helper provides hash-chained provenance, lifecycle
state, review gates, reliability tracking, validation, reporting, and rollback
signals.

## What changed from upstream

The original project captures hard-won "golden paths." This fork keeps that
useful behavior and adds the missing parts needed for actual continuous
improvement:

- a mandatory prepare → perform → judge → learn loop for substantive tasks;
- relevant-skill retrieval before work and a single learning decision afterward;
- immutable hash-chained experience/provenance events;
- quarantined candidates instead of immediate authoritative writes;
- three distinct reviews: evidence/scope, evaluation/usefulness, and
  safety/governance;
- clean-context replay and baseline/prior-version comparisons;
- probation, conservative reliability, owner approval, version invalidation,
  automatic retirement, and rollback;
- bounded externally triggered curriculum runs for high-value capability gaps;
- prompt-injection, secret, privilege-growth, production, and self-approval
  defenses;
- a TeamON One profile that uses existing Context, Memory proposal, exact World,
  immutable skill, Task, and WorkRun boundaries rather than creating a second
  runtime or memory plane;
- tests and CI.

This does **not** update model weights or grant autonomy. It improves the
agent's reusable procedures and decision support under existing owner authority.

## Install

### `npx skills`

```bash
npx skills add natural0101/self-learning-skills
npx skills add natural0101/self-learning-skills -g
npx skills add natural0101/self-learning-skills -a claude-code
```

### Claude Code plugin

```text
/plugin marketplace add natural0101/self-learning-skills
/plugin install self-learning@self-learning-skills
```

### Manual

```bash
git clone https://github.com/natural0101/self-learning-skills

# Project-local Agent Skills client
mkdir -p .agents/skills
cp -R self-learning-skills/skills/self-learning .agents/skills/

# Claude Code alternative
mkdir -p .claude/skills
cp -R self-learning-skills/skills/self-learning .claude/skills/

# Cursor
mkdir -p .cursor/rules
cp self-learning-skills/.cursor/rules/self-learning.mdc .cursor/rules/

# Codex / Zed / Aider / Gemini CLI / other AGENTS.md readers
cat self-learning-skills/AGENTS.md >> AGENTS.md
```

Use the location your agent actually discovers. Do not install duplicate copies
into multiple active directories unless the host deduplicates them.

## Quick start

Initialize local lifecycle state:

```bash
python skills/self-learning/scripts/learning_cycle.py init --root .agent-learning
```

Record a verified task outcome:

```bash
python skills/self-learning/scripts/learning_cycle.py record \
  --root .agent-learning \
  --task-id cache-fix-001 \
  --outcome pass \
  --summary "Targeted cache regression is fixed" \
  --evidence "pytest tests/test_cache.py::test_refresh -> 1 passed" \
  --failure-pattern "stale cache produced phantom results" \
  --dead-end "Restarting the caller did not invalidate the server cache"
```

Create a quarantined candidate from the returned event ID:

```bash
python skills/self-learning/scripts/learning_cycle.py candidate \
  --root .agent-learning \
  --name refresh-cache-safely \
  --source-event <event-id> \
  --failure-pattern "stale cache produced phantom results" \
  --verification "targeted regression passed from a clean process" \
  --boundary "this project's development cache only" \
  --risk low \
  --scope project
```

Run three **distinct** reviews and record each result:

```bash
python skills/self-learning/scripts/learning_cycle.py review \
  --root .agent-learning --candidate <candidate-id> \
  --kind evidence --verdict pass --reviewer evidence-reviewer \
  --notes "Claims map to hashed task evidence; project scope is justified" \
  --evidence reviews/evidence.json --independent

python skills/self-learning/scripts/learning_cycle.py review \
  --root .agent-learning --candidate <candidate-id> \
  --kind evaluation --verdict pass --reviewer evaluation-reviewer \
  --notes "Candidate beats prior workflow on positive and regression cases" \
  --evidence reviews/evaluation.json --independent

python skills/self-learning/scripts/learning_cycle.py review \
  --root .agent-learning --candidate <candidate-id> \
  --kind safety --verdict pass --reviewer safety-reviewer \
  --notes "No secrets, injection, authority expansion, or production writes" \
  --evidence reviews/safety.json --independent
```

Start probation and record judged uses:

```bash
python skills/self-learning/scripts/learning_cycle.py promote \
  --root .agent-learning --candidate <candidate-id>

python skills/self-learning/scripts/learning_cycle.py usage \
  --root .agent-learning --candidate <candidate-id> \
  --outcome pass --evidence evals/probation-1.json
```

After probation meets the threshold, generate the exact approval request. The
authenticated host signs it with a key unavailable to the agent process, then
records the receipt:

```bash
python skills/self-learning/scripts/learning_cycle.py approval-request \
  --root .agent-learning --candidate <candidate-id> > approval-request.json

python skills/self-learning/scripts/learning_cycle.py approve \
  --root .agent-learning --candidate <candidate-id> \
  --receipt approval-receipt.json
```

See
[the approval protocol](skills/self-learning/references/approval.md). A
single-user `local-manual` mode exists only as an explicit config opt-in and
must run outside the autonomous agent's authority.

Default activation requires at least three probation trials, reliability
`>= 0.80`, current triple reviews, and owner approval. Low-risk project-local
auto-activation exists only as an explicit config opt-in. Protected domains
never bypass approval.

Audit and report:

```bash
python skills/self-learning/scripts/learning_cycle.py audit --root .agent-learning
python skills/self-learning/scripts/learning_cycle.py report --root .agent-learning
python skills/self-learning/scripts/learning_cycle.py verify-ledger --root .agent-learning
python skills/self-learning/scripts/learning_cycle.py next --root .agent-learning
python skills/self-learning/scripts/learning_cycle.py queue --root .agent-learning
```

## Lifecycle CLI

| Command | Purpose |
|---|---|
| `init` | Create config, ledger, candidate, and report directories. |
| `record` | Append a safe observable task outcome to the hash chain. |
| `candidate` | Create a quarantined candidate linked to source events. |
| `review` | Record evidence, evaluation, or safety review. |
| `approval-request` | Emit exact version/hash/nonce data for host approval. |
| `approve` | Verify and anchor a host-signed receipt or explicit local-manual approval. |
| `promote` | Move a fully reviewed candidate into probation. |
| `usage` | Record judged use, update reliability, activate or retire. |
| `revise` | Create a new quarantined version and invalidate old gates. |
| `archive` | Retire a candidate while preserving history. |
| `validate-skill` | Check Agent Skills structure, lifecycle sections, and secrets. |
| `verify-ledger` | Verify event hashes and chain order. |
| `audit` | Check ledger, states, reviews, approval, and policy consistency. |
| `report` | Produce a readable lifecycle report. |
| `queue` | Rank repeated evidence-backed capability gaps without executing them. |
| `next` | Show each candidate's next gate and top bounded curriculum opportunities. |

No third-party Python package is required.

## Directory layout

```text
self-learning-skills/
├── AGENTS.md
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── skills.sh.json
├── .claude-plugin/marketplace.json
├── .cursor/rules/self-learning.mdc
├── .github/workflows/validate.yml
├── scripts/validate_repository.py
├── tests/test_learning_cycle.py
└── skills/self-learning/
    ├── SKILL.md
    ├── scripts/learning_cycle.py
    ├── assets/
    │   ├── SKILL.template.md
    │   ├── approval-receipt.template.json
    │   ├── curriculum-trigger.template.json
    │   ├── lesson-receipt.template.json
    │   ├── eval-case.template.json
    │   ├── review-prompts.md
    │   └── learning-config.example.json
    └── references/
        ├── approval.md
        ├── architecture.md
        ├── autonomous-curriculum.md
        ├── research-foundations.md
        ├── review-protocol.md
        ├── skill-authoring.md
        └── teamon-one.md
```

Generated `.agent-learning/` state is local by default. Commit only intentionally
reviewed, redacted receipts/evals or promoted skill packages according to the
host repository's policy.

## Safety model

Auto-learning can compound mistakes. This repository therefore assumes that
candidate content may be wrong or adversarial.

- Untrusted web/document/tool text is evidence, never policy.
- Candidate skills remain quarantined until exact-version triple review.
- Reviewers must be distinct and context-clean by default.
- Literal secret-shaped values and credential-bearing URIs are rejected.
- Learning never adds tools, permissions, network/filesystem scope, spending,
  publishing, outreach, deletion, merge, or deployment authority.
- Identity, Mission, owner authority, permissions, protected safety policy, and
  the promotion gate cannot be auto-modified.
- Revision invalidates review, approval, and probation statistics.
- Repeated failure archives a skill; audit history remains intact.
- The hash chain detects ledger mutation but is not a cryptographic identity or
  remote attestation system.

See [SECURITY.md](SECURITY.md) and
[references/review-protocol.md](skills/self-learning/references/review-protocol.md).

## TeamON One

Use [the TeamON One profile](skills/self-learning/references/teamon-one.md).
It maps the lifecycle to existing governed boundaries:

```text
explicit feedback / objective evidence
→ agent dedupe + bounded proposal
→ private pending Memory
→ exact owner review and content hash acceptance
→ relevant Context or exact selected-World projection
→ later judged result
→ keep / supersede / narrow / forget
```

Owner-created Tasks/WorkRuns may trigger bounded curriculum work. The tenant
agent does not accept its own Memory, mutate immutable composition, or create a
second runtime/retrieval plane.

## Design foundations

The design is informed by primary work on verbal reflection and episodic memory,
automatic curricula and skill libraries, workflow induction, testable skill
lifecycles, evidence-grounded policy crystallization, contrastive skill
construction, and evolving-memory safety:

- [Reflexion](https://arxiv.org/abs/2303.11366)
- [Voyager](https://arxiv.org/abs/2305.16291)
- [Agent Workflow Memory](https://arxiv.org/abs/2409.07429)
- [MUSE-Autoskill](https://arxiv.org/abs/2605.27366)
- [From Memory to Skills: Cognition of Self-Evolving Agents](https://arxiv.org/abs/2607.16621)
- [SkillAlchemy](https://arxiv.org/abs/2608.23417)
- [SkillForge](https://arxiv.org/abs/2604.08618)
- [Practice Makes Unsafe: Skill Misevolution in Self-Improving Agents](https://arxiv.org/abs/2608.12851)
- [Governing Evolving Memory in Agentic AI Systems](https://arxiv.org/abs/2603.11768)
- [Agent Skill Evaluation: A Survey](https://arxiv.org/abs/2606.11435)
- [Agent Skills specification](https://agentskills.io/specification)

The implementation deliberately combines the productive patterns with stronger
provenance, replay, lifecycle, and governance gates.

## Upstream and license

Forked from [Kulaxyz/self-learning-skills](https://github.com/Kulaxyz/self-learning-skills).
The original golden-path capture concept and MIT attribution are preserved.
See [LICENSE](LICENSE).
