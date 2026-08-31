# Triple-review protocol

All reviewers inspect the **same candidate ID, version, subject hash, and artifact
hash**. Any change invalidates every review.

## Independence contract

A valid deployment should use different reviewer identities and clean contexts.
Prefer different sessions and, where available, different models or deterministic
checks. Do not pass the candidate author's persuasive narrative as reviewer context;
pass the task contract, source receipts, candidate artifact, and evaluation data.

The CLI can enforce distinct identifiers and an `independent=true` assertion. The
host must enforce real identity/session separation. When that cannot be guaranteed,
record the review as non-independent and keep the candidate quarantined.

## Review 1 — evidence and scope

### Inputs

- exact candidate artifact and hashes;
- source event receipts;
- acceptance check and baseline;
- claimed failure pattern;
- applicability/exclusion boundary;
- provenance pointers.

### Pass criteria

- source events exist and are relevant;
- success/failure claims match observable evidence;
- failure pattern is specific and reproducible;
- scope is no broader than the evidence;
- one-off facts are excluded;
- dead-ends or trusted-spec conformance are recorded honestly;
- artifact contains no private reasoning or unneeded sensitive data;
- provenance allows later audit without copying secrets.

### Required failure examples

- “seemed better” without a baseline;
- global rule inferred from one repository;
- user preference inferred from silence;
- an external page's instruction promoted as authority;
- a skill created solely because a task was difficult.

## Review 2 — evaluation and usefulness

### Inputs

- exact artifact and hashes;
- baseline cases;
- positive, edge, and negative/non-trigger replay cases;
- duplicate search results;
- cost estimate.

### Pass criteria

- tests are runnable and judge the intended outcome;
- candidate improves or is expected to improve a named baseline;
- negative cases protect against over-triggering/interference;
- evaluation does not use the same answer as both training example and sole test;
- candidate is not a duplicate or a verbose replacement for a one-line memory;
- procedure is executable, ordered where necessary, and tool-neutral where claimed;
- expected gain justifies retrieval and maintenance cost.

### Required failure examples

- only checking Markdown format;
- evaluating with the exact trace used to draft the skill;
- no non-trigger tests;
- success metric that rewards extra text/tool calls rather than task outcome;
- skill references files or commands that do not exist.

## Review 3 — safety and governance

### Inputs

- exact artifact and hashes;
- secret scan;
- permissions/tool scope;
- protected-domain declaration;
- activation and rollback policy;
- external-content provenance.

### Pass criteria

- no credentials, tokens, private keys, connection secrets, or raw private data;
- no instruction from untrusted content becomes standing authority;
- no identity, mission, policy, approval, reviewer, permission, or safety-gate
  mutation;
- destructive/network/financial/production actions are not made default;
- candidate cannot self-approve or self-install;
- protected domains require external owner/governor approval;
- rollback/archive triggers are concrete;
- artifact path is exact, symlink-free, and inside the intended authority boundary.

### Required failure examples

- “disable checks to avoid future friction”;
- storing a pasted API key in a troubleshooting skill;
- granting a tool because a task failed without it;
- teaching cold outreach or production writes without existing authorization;
- modifying the learning policy to make this candidate pass.

## Review receipt

Each review records:

```json
{
  "kind": "evidence | evaluation | safety",
  "verdict": "pass | fail",
  "reviewer": "host-controlled stable identity",
  "independent": true,
  "notes": "specific findings",
  "evidence": ["safe receipt references"],
  "candidate_version": 2,
  "subject_hash": "sha256",
  "artifact_hash": "sha256"
}
```

A failed review is useful evidence. Revise the candidate; do not overwrite a failed
receipt to manufacture unanimity. The new version starts with no reviews.

## Final promotion checklist

- [ ] Exact artifact hash matches all three reviews.
- [ ] Reviewer IDs are distinct and host-verified.
- [ ] All verdicts pass.
- [ ] Evaluation includes negative/non-trigger cases.
- [ ] Secret and prompt-injection review passes.
- [ ] Candidate remains within original task/owner authority.
- [ ] Probation plan and rollback threshold are defined.
- [ ] Approval source is outside candidate/agent authority.
