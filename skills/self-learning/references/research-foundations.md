# Research foundations and design synthesis

This file records the primary sources used to harden the fork. The repository does
not copy paper text; it translates recurring architectural findings into an
auditable external-skill lifecycle.

## Primary sources

### Reflexion — verbal feedback as external learning state

Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning*.
https://arxiv.org/abs/2303.11366

Useful idea: task feedback can be stored as language and reused without updating
model weights. Repository consequence: experience is explicit and reviewable, and
success still requires a task judge rather than self-reported confidence.

### Voyager — curriculum, executable skills, and iterative feedback

Wang et al., *Voyager: An Open-Ended Embodied Agent with Large Language Models*.
https://arxiv.org/abs/2305.16291

Useful idea: a skill library plus an automatic curriculum can extend capability.
Repository consequence: curriculum is bounded by authorization, sandbox, budget,
and objective checks; skills remain quarantined until evaluated.

### ExpeL — learning reusable lessons across tasks

Zhao et al., *ExpeL: LLM Agents Are Experiential Learners*.
https://arxiv.org/abs/2308.10144

Useful idea: success/failure trajectories can yield reusable insights that improve
future tasks. Repository consequence: named failure patterns, dead-ends, selective
retrieval, and held-out replay cases are first-class.

### Generative Agents — observation, reflection, planning

Park et al., *Generative Agents: Interactive Simulacra of Human Behavior*.
https://arxiv.org/abs/2304.03442

Useful idea: reflection can compress observations into higher-level memories.
Repository consequence: reflection is not automatically truth; durable promotion
requires evidence, scope, review, and authority.

### Self-Refine — iterative improvement with feedback

Madaan et al., *Self-Refine: Iterative Refinement with Self-Feedback*.
https://arxiv.org/abs/2303.17651

Useful idea: generation, feedback, and revision can improve an output. Repository
consequence: candidate revision is an explicit version transition; it invalidates
old reviews instead of silently editing the reviewed artifact.

### MemGPT — explicit memory hierarchy and management

Packer et al., *MemGPT: Towards LLMs as Operating Systems*.
https://arxiv.org/abs/2310.08560

Useful idea: bounded context benefits from explicit memory tiers and movement.
Repository consequence: checkpoint, notebook, governed memory, skill, and canonical
knowledge have different owners; one thought is routed once rather than copied into
every layer.

### Agent Skills open specification

Agent Skills specification.
https://agentskills.io/specification

Repository consequence: harvested procedures remain portable `SKILL.md` packages
with trigger-focused frontmatter and progressive disclosure.

### Supply-chain provenance and risk management

SLSA specification: https://slsa.dev/spec/v1.1/

NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework

Repository consequence: exact artifact identity, provenance, separated approval,
rollback, and host-owned trust boundaries are treated as product requirements, not
optional documentation.

## Synthesis

Across these sources, “reflection” alone is insufficient. A reliable self-improving
agent needs:

1. observable task outcomes;
2. selective capture rather than saving everything;
3. separation between tentative experience and durable behavior;
4. exact applicability boundaries;
5. evaluation against a baseline and held-out/negative cases;
6. provenance and immutable artifact identity;
7. independent safety/usefulness review;
8. probation, continued monitoring, and rollback;
9. external authority for protected durable changes;
10. bounded curriculum instead of an ungoverned always-running loop.

## Rejected shortcuts

- “After every task, append a rule” — causes noise and contradictory instructions.
- “The agent said the fix worked” — lacks a task judge.
- “Three prompts from the same context are independent review” — preserves shared
  blind spots and persuasion.
- “Review Markdown, then edit before activation” — breaks artifact identity.
- “Let the agent approve its own safe changes” — collapses governance.
- “Run learning forever in the background” — creates an unbounded objective and
  cost/authority drift.
- “Store full reasoning traces” — unnecessary, privacy-invasive, and not reliable
  provenance of causal correctness.

## Known limitations

- External skills improve behavior only when the runtime retrieves and applies them.
- Evaluation quality limits learning quality.
- The local hash chain cannot resist a fully privileged writer.
- HMAC approval requires host isolation of the symmetric key; public-key or host API
  approval is stronger.
- Reviewer IDs are metadata unless the host enforces identity/session separation.
- No design can guarantee monotonic improvement across all tasks; regression checks
  and rollback remain mandatory.
