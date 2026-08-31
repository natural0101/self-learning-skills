# TeamON One integration profile

Read this when installing or invoking the skill inside TeamON One.

This profile maps continuous learning onto TeamON One's existing owners. It does
not introduce a second runtime, memory store, retrieval plane, capability
registry, or always-hot autonomy service.

## Invariants

- One person-owned capsule contains one permanent agent.
- TeamON Lite remains the only provider/session engine.
- Context MCP remains the only generic lazy retrieval plane.
- Assigned skills and blueprints remain exact, immutable, and
  checksum-verified.
- Learning is a governed transition from feedback/evidence to a proposal and a
  later judged result; it is not a bindable module or independent store.
- The owner alone accepts, edits, rejects, supersedes, or forgets durable Memory.
- Narrow accepted lessons enter only the exact matching selected-World context.
- Owner-created Tasks and isolated WorkRuns are the bounded proactive trigger.

## Mapping

| Self-learning concept | TeamON One owner/path |
|---|---|
| unfinished work | existing Checkpoint |
| unverified observation | append-only Notebook |
| reusable verified lesson | existing `memory_propose` path after dedupe/conflict check |
| pending candidate | private pending Memory review; outside Context |
| accepted person lesson | owner-approved Memory retrieved through Context MCP |
| accepted narrow lesson | exact selected-World immutable context projection |
| skill-package revision | normal product/repository release governance with checksum update |
| scheduled curriculum | owner-created Task → isolated WorkRun |
| later evaluation | explicit owner verdict or objective domain acceptance gate |
| rollback | owner forget/supersede for Memory; normal package rollback for skills |

One thought belongs to one layer. Do not copy the same lesson into Notebook,
Memory, World context, and a skill.

## Per-turn behavior

Before substantial work:

1. Respect the generated `AGENTS.md` instruction floor and exact selected World.
2. When the capsule indicates accepted person Memory exists, perform one bounded
   Context search for relevant lessons.
3. Apply only exact relevant accepted lessons; retrieval success alone is not
   useful application evidence.
4. Do not search or expose sibling private Threads, credentials, browser state,
   or unrelated Worlds.

After substantial work or explicit correction:

1. Judge the result through an objective gate or explicit owner feedback.
2. If unfinished, update Checkpoint only.
3. If useful but unverified, append one Notebook observation.
4. If stable and reusable, dedupe against accepted Memory and contradictions.
5. Draft one short `memory_propose` conclusion with safe evidence references and
   an optional exact context boundary.
6. Pending remains outside Context until owner acceptance.
7. Later judged work may keep, supersede, narrow, or forget the lesson.

## Durable skill changes

The generic lifecycle can draft and evaluate an Agent Skill package, but a
TeamON tenant agent must not write it directly into active immutable composition.
Instead:

1. create a quarantined candidate and receipt in an owner/repository work area;
2. run evidence, evaluation, and safety reviews;
3. test in an isolated project/repository branch or approved sandbox;
4. submit the exact package through normal repository/product governance;
5. update composition/checksum only through the existing owner/release path;
6. preserve the old package for rollback.

A local file that is not included in the exact composition is not an active
TeamON capability. Conversely, an installed package must not silently expand
Capability Spine.

## Curriculum WorkRun

A TeamON learning run must originate from an owner-created Task with:

- exact Space/World/project scope;
- bounded budget;
- explicit available modules/tools;
- no production write, outreach, purchase, publish, or deploy authority unless
  the Task independently grants normal authority for that action;
- one requested gap or permission to choose one from observed evidence;
- terminal receipt delivered through the normal Task/WorkRun path.

The WorkRun may research, reproduce, test, evaluate, and propose. It cannot
accept its own Memory, install its own skill, alter generated instructions, or
create a recurring scheduler.

## Recommended configuration

Keep the default conservative settings:

```json
{
  "require_independent_reviews": true,
  "auto_activate_low_risk": false,
  "require_owner_approval_for_activation": true,
  "approval_mode": "host-receipt",
  "approval_hmac_env": "SELF_LEARNING_APPROVAL_KEY",
  "probation_min_trials": 3,
  "activation_reliability": 0.8
}
```

For TeamON Memory proposals, the host's owner review is the activation authority.
For immutable skill packages, repository/product review is the activation
authority. The local lifecycle state is supporting evidence, not a replacement
for either authority.

## Prohibited shortcuts

- Directly append agent-authored content to accepted Memory.
- Treat Notebook as accepted Memory.
- Put pending generic lessons into Context MCP.
- Make narrow World lessons generically searchable.
- Modify Identity, Mission, composition, permissions, or Capability Spine from a
  learning candidate.
- Add a new learning database/service when existing owners can hold the state.
- Claim improvement from `context.read`, tool success, or no owner complaint.
- Run a perpetual autonomous loop outside owner-created Tasks.
