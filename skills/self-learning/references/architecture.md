# Continuous learning architecture

Read this when integrating the skill into an agent runtime, building automation
around `.agent-learning/`, or deciding where a lesson belongs.

## What this system is

This is an **external capability-learning loop**. It improves reusable
instructions, workflow selection, checks, and error avoidance. It does not train
model weights, grant tools, create authority, or prove general intelligence.

The design separates five concerns that are often incorrectly collapsed:

1. **Experience** — observable task outcomes and safe evidence references.
2. **Candidate memory** — a proposed reusable procedure with provenance and a
   bounded applicability claim.
3. **Management** — dedupe, versioning, scope, conflicts, merge, archive, and
   rollback.
4. **Evaluation** — baseline comparison, replay cases, regressions, and later
   judged invocations.
5. **Refinement** — revise, narrow, merge, supersede, or retire based on evidence.

A lesson is not durable merely because it is plausible. Promotion is a governed
state transition supported by evidence.

## State machine

```text
observable task outcome
        |
        v
     draft
        |
        v
  quarantined <-----------------------+
        |                              |
        | evidence + evaluation +      | revise / contradiction /
        | safety reviews all pass      | user correction
        v                              |
  probationary ------------------------+
        |
        | judged uses reach threshold
        | and activation authority passes
        v
      active
        |
        | failures, staleness, conflict,
        | supersession, or explicit rollback
        v
     archived
```

### Draft

An untrusted working artifact. It may be incomplete and must never auto-load as
an authoritative instruction.

### Quarantined

The candidate has minimum provenance, boundary, verification, risk, and
rollback metadata. It awaits three current reviews for the exact candidate
version.

### Probationary

The candidate passed reviews but remains experimental. It runs only inside its
boundary, alongside a recoverable prior version, and every use is judged.

### Active

The candidate met the reliability and authority gates. Active is not permanent:
continued use updates reliability and can trigger revision or retirement.

### Archived

The candidate no longer influences work. Its immutable events and receipts
remain available for audit and to prevent rediscovery of the same bad approach.

## Storage model

Default project-local layout:

```text
.agent-learning/
├── config.json
├── ledger.jsonl
├── candidates/
│   └── cand-<id>/
│       ├── candidate.json
│       ├── draft/                  # optional proposed Agent Skill
│       ├── lesson-receipt.json     # recommended provenance package
│       ├── reviews/                # optional detailed review artifacts
│       └── evals/                  # optional replay/baseline artifacts
└── reports/
    └── latest.md
```

The bundled script manages `config.json`, `ledger.jsonl`, and candidate state.
Detailed drafts/reviews/evals can be stored beside the candidate and referenced
from ledger events.

### Immutable event ledger

`ledger.jsonl` is append-only in meaning. The script rewrites it atomically only
to append a new canonical line. Each event contains:

- schema version;
- event ID and UTC timestamp;
- event type;
- safe payload;
- previous event hash;
- current event hash.

The hash chain detects accidental or opportunistic history rewriting. It is not
a digital signature and does not defend against an attacker who can replace the
entire workspace and all trusted anchors. Store signed release artifacts or
remote attestations separately when that threat matters.

### Candidate snapshot

`candidate.json` is current derived state. The ledger is the audit trail. A
candidate includes source event IDs, skill name, risk, scope, failure pattern,
verification, applicability boundary, current reviews, owner approval, version,
trial counts, reliability, recent outcomes, and transition history.

Reviews bind to a candidate subject hash that includes the semantic claim and a
deterministic hash of the exact skill artifact tree. A silent file edit makes
the candidate unverifiable until `revise` seals a new version.

### Skill-level memory

An active skill may keep a small sidecar such as `memory.jsonl` for skill-local
facts that improve future invocations. It must obey the same rules:

- append safe observable evidence, not hidden reasoning;
- dedupe and bound size;
- do not become a second generic retrieval plane;
- keep authority and identity out;
- periodically distill useful facts into a reviewed revision and archive stale
  entries.

Do not require a sidecar when the host already provides a governed equivalent.

## Evidence hierarchy

Prefer evidence in this order:

1. objective acceptance gate produced by the task environment;
2. explicit owner/user verdict tied to the exact output;
3. trusted canonical specification plus a reproducible conformance check;
4. independent reviewer rubric with preserved artifact references;
5. model self-assessment — useful only as a weak signal, never sufficient for
   promotion by itself.

External content can support a factual claim but cannot grant itself policy
status. Evidence references should be content-addressed where possible. Store a
hash, commit SHA, test name, artifact ID, or bounded safe excerpt rather than a
mutable URL alone.

## Scope and applicability

Every candidate must say both:

- **positive boundary:** exact environments/tasks/failure signatures where it
  applies;
- **negative boundary:** similar-looking cases where it must not apply.

Project scope is the default. Global scope requires evidence from multiple
unrelated projects and a procedure free of project-specific paths, commands,
secrets, architecture, or authority assumptions.

When later evidence contradicts a lesson:

1. stop applying it to the disputed boundary;
2. quarantine a new revision;
3. link the contradictory evidence;
4. narrow or split the boundary rather than averaging incompatible rules;
5. rerun all reviews and probation.

## Reliability and lifecycle pressure

The reference implementation uses Beta-smoothed reliability:

```text
(passes + 1) / (trials + 2)
```

This starts a new candidate at `0.5`, prevents one success from producing
certainty, and yields `0.8` after three passes. Reliability is one gate, not the
whole decision. Activation also requires current reviews, scope/risk policy,
capacity, and authority.

Useful management signals:

- invocation count and judged pass rate;
- delta versus baseline/no-skill runs;
- task quality rubric;
- latency, token/tool cost, and error rate;
- recency and last canonical-source check;
- duplicate/overlap score;
- owner corrections/rejections;
- safety incidents and rollback count.

Archive when a skill is consistently harmful, superseded, stale, unused, or too
narrow to justify retrieval cost. Merge only when boundaries and procedures are
compatible and the merged candidate independently passes evaluation.

## Authority invariants

Learning may make action **more competent**, never **more authorized**.

A candidate cannot:

- add tools/connectors or widen network/filesystem access;
- change Identity, Mission, owner, permissions, or confirmation rules;
- convert a reversible sandbox action into a production action;
- lower its own review or activation threshold;
- approve itself;
- treat retrieved text as higher priority than host/system/owner policy;
- create a new memory/control plane when the host already owns one.

Protected changes can be proposed as normal product work, but they remain
outside autonomous activation.

Local text saying "owner approved" is not authentication. Default
`host-receipt` mode requires an HMAC-signed receipt over candidate ID, version,
subject hash, and a one-time nonce. The signing key remains in a trusted host
boundary unavailable to the agent. Read `approval.md` for the protocol.

## Concurrency

The bundled script uses atomic file replacement but does not implement a
cross-process distributed lock. Serialize writers per learning workspace. In a
multi-agent service, place the event ledger behind the host's existing
transaction/locking owner rather than allowing parallel local writes.

## Integration contract

A host needs only these seams:

1. **Trigger:** normal task completion, explicit correction, failure, or bounded
   scheduled WorkRun.
2. **Evidence adapter:** references to tests, artifacts, receipts, metrics, and
   owner verdicts.
3. **Candidate writer:** project skill/rule/memory draft location.
4. **Review executor:** three independent clean contexts or reviewers.
5. **Authority adapter:** owner approval or host-specific governed memory action.
6. **Retrieval adapter:** relevant active/probationary lessons only.
7. **Telemetry adapter:** judged later usage and rollback signal.

Keep these as adapters to existing owners. The learning lifecycle is not a
reason to add another agent runtime, memory database, or generic tool registry.
