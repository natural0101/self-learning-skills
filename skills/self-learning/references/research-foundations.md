# Research foundations and design mapping

Read this when changing the framework itself, evaluating whether a new learning
mechanism belongs here, or reviewing claims about "self-improvement."

Use primary sources. A paper can motivate a mechanism; it does not prove that
this implementation inherits the paper's benchmark results.

## Evidence-to-design map

| Primary work | Reusable finding | Adopted mechanism | Additional guardrail here |
|---|---|---|---|
| [Reflexion](https://arxiv.org/abs/2303.11366) | Verbal feedback and episodic memory can improve later trials without weight updates. | Concise outcome/failure lessons and later retrieval. | Observable evidence only; no private reasoning; memory is not automatically authoritative. |
| [Voyager](https://arxiv.org/abs/2305.16291) | Automatic curriculum, iterative feedback, and a growing executable skill library support continual capability acquisition. | Externally triggered bounded curriculum and reusable skills. | Mission linkage, one objective, budget/tool allowlist, no always-hot loop, review and probation. |
| [Agent Workflow Memory](https://arxiv.org/abs/2409.07429) | Reusable workflows can be induced from trajectories and transferred to future tasks. | Procedures rather than one-off answers; trace-to-candidate flow. | Evidence anchors, explicit boundaries, dedupe, and baseline/replay evaluation. |
| [MUSE-Autoskill](https://arxiv.org/abs/2605.27366) | Useful self-evolving skill systems need creation, memory, management, evaluation, and refinement rather than capture alone. | Five-part lifecycle, skill-local memory option, evaluation, merge/prune/refine. | Quarantine, exact artifact binding, triple review, owner activation, and rollback. |
| [From Memory to Skills: Cognition of Self-Evolving Agents](https://arxiv.org/abs/2607.16621) | Skills should crystallize from grounded traces into supported, stable, positive-gain policies and remain lifecycle-managed. | Trace ledger, bounded policy candidate, probationary/active/archived states, smoothed reliability. | Host authority remains external; contradictions narrow/revise rather than silently overwrite. |
| [SkillAlchemy](https://arxiv.org/abs/2608.23417) | Contrastive evidence and scope grounded in positive/negative examples improve skill construction. | Positive and negative applicability boundaries and eval cases. | Every semantic revision invalidates reviews/approval; global scope needs cross-project evidence. |
| [SkillForge](https://arxiv.org/abs/2604.08618) | Failure analysis, diagnosis, and optimization form a useful skill-refinement loop. | Named failure patterns, ruled-out dead-ends, revision and replay. | No inferred causality beyond observations; failures cannot directly become policy. |
| [A Self-Evolving Framework for Lifelong Learning](https://arxiv.org/abs/2508.19005) | Proactive intrinsic goal formation remains difficult for current agents. | Evidence-backed curriculum queue rather than pretending open-ended autonomy is solved. | Goals must support the owner's mission and pass cost/risk/evidence ranking. |
| [Practice Makes Unsafe](https://arxiv.org/abs/2608.12851) | Evolved skills can become unsafe and compound risk across reuse. | Write-time and reuse-time gates, protected domains, telemetry, retirement. | Signed external approval, artifact hashes, no self-modification of governance. |
| [Governing Evolving Memory](https://arxiv.org/abs/2603.11768) | Poisoning, semantic/procedural drift, conflicts, and staleness require provenance and governance. | Hash-chained ledger, receipts, scope, conflicts, versioning, archive. | Untrusted content is evidence only; host remains the real authority/state owner. |
| [Agent Skill Evaluation: A Survey](https://arxiv.org/abs/2606.11435) | Skill evaluation must cover utility, comparison, safety, and longitudinal evolution, not one snapshot pass. | Baseline/no-skill comparison, quality/cost/error metrics, probation, continued reliability. | Activation is reversible and ongoing failures can retire an active skill. |
| [Agent Skills specification](https://agentskills.io/specification) | Portable skills use a root `SKILL.md` with strict frontmatter and optional references/assets/scripts. | Compatible directory/frontmatter, progressive disclosure, bundled validator. | Lifecycle requirements remain content-level and do not invent incompatible schema fields. |

## Synthesis

The sources converge on a stronger architecture than "write down what worked":

1. **Ground experience.** Keep task outcome, evidence, failure signature, and
   source trust separate from the generated lesson.
2. **Crystallize a bounded policy.** Convert repeated or high-value evidence into
   a procedure with positive and negative applicability.
3. **Test causally modest benefit.** Compare with a baseline/prior version and
   use replay cases that can fail.
4. **Manage lifecycle.** Quarantine, probation, activation, revision, merge,
   archive, and rollback are first-class states.
5. **Preserve authority.** Improvement changes competence, never ownership,
   permissions, identity, mission, or policy priority.
6. **Evaluate longitudinally.** Later judged invocations update reliability and
   can disconfirm an earlier lesson.

## Deliberately not adopted

### Direct post-task activation

A successful task may have succeeded despite the proposed lesson. Immediate
activation creates false causality and instruction drift. Candidates are sealed,
reviewed, and tested first.

### Hidden chain-of-thought storage

Private reasoning is neither necessary nor safe provenance. Store observable
inputs/actions/results and concise conclusions.

### Unbounded intrinsic goals

Current agents remain weak at autonomous goal generation, and open-ended loops
can optimize activity, novelty, or self-preservation rather than owner value.
The curriculum queue ranks only evidence-backed, mission-linked gaps and does not
execute without an external trigger.

### Autonomous authority growth

A skill that learns to add tools or lower its own gate can recursively escape
its original safety boundary. Protected domains are never auto-activated, and
default approval is signed by a trusted host boundary.

### A second memory or agent runtime

Learning state should attach to existing checkpoint/notebook/memory/skill and
owner boundaries. The generic file implementation is a reference adapter, not a
mandate to duplicate a product's canonical state plane.

## Review rule for new research claims

Before citing a new result in this repository:

1. read the primary paper/specification, not a secondary summary;
2. distinguish measured result from author hypothesis;
3. identify task/domain/model limitations;
4. state whether this repository implements the same mechanism or only draws an
   analogy;
5. add a falsifiable repository test or design implication;
6. run architecture, evaluation, and safety reviews.
