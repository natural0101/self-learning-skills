# Bounded autonomous curriculum

## Goal

Use authorized idle or scheduled capacity to reduce **observed recurring capability
gaps**. The curriculum is not open-ended self-entertainment and does not create new
external objectives.

## Authorized triggers

Start only from one of these:

- explicit owner request to improve/practice/research a capability;
- owner-created scheduled task with a defined budget and scope;
- CI/test/evaluation failure assigned to the agent;
- a foreground task whose acceptance criteria include closing a repeated gap.

Do not run a permanent background loop. Do not interpret “be proactive” as authority
to contact people, spend money, mutate production, install tools, or collect private
data.

## Build the gap queue

Group observable experience events by a normalized named failure pattern. Exclude
gaps already covered by a non-archived candidate. Rank the rest approximately by:

```text
priority = recurrence × impact × uncertainty × evidence availability
           / (learning cost × safety risk)
```

The reference CLI command is:

```bash
python skills/self-learning/scripts/learning_cycle.py gaps --limit 10
```

The score is triage, not truth. A low-frequency security failure can outrank a high-
frequency cosmetic issue through host policy.

## Choose one target

A target must have:

- a bounded task family;
- a safe practice environment;
- an objective or owner-judged acceptance check;
- a baseline;
- a maximum time/tool/cost budget;
- a clear stop condition;
- no need for new authority.

Reject targets that require live users, unsolicited messages, financial actions,
production writes, credential access, or policy changes unless the exact authorized
task already grants and governs those actions.

## Practice loop

1. Reproduce the gap in a sandbox or fixture.
2. Record baseline outcome and evidence.
3. Form one procedural hypothesis.
4. Run a bounded trial.
5. Judge against the same acceptance check.
6. Keep the result only if it generalizes to held-out and negative cases.
7. Route it through candidate quarantine and triple review.
8. Stop; do not immediately create a chain of speculative skills.

## Diversity and overfitting controls

- Hold out at least one case not used to author the candidate.
- Include a negative case where the skill must not trigger.
- Vary inputs, environment state, and task phrasing when possible.
- Measure interference with an unrelated task.
- Prefer reproducible fixtures over repeatedly querying live systems.
- Do not reward longer traces, more tools, or self-reported confidence.

## Stop conditions

Stop when any is true:

- acceptance passes on the bounded test set;
- budget is exhausted;
- evidence is insufficient;
- the target requires broader authority;
- a safety review fails;
- live conditions differ from the sandbox materially;
- a higher-priority owner task arrives;
- repeated trials show no meaningful gain;
- the gap is already covered by a better candidate.

## Output

An authorized curriculum run returns:

- selected gap and score inputs;
- baseline;
- trials and evidence;
- result classification;
- candidate ID/version if created;
- review/probation status;
- exact stop reason.

It must not claim durable learning until activation gates pass.
