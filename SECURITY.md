# Security policy

Self-improving agents can amplify both useful and harmful behavior. Treat every
learned candidate as untrusted until exact-version evidence, evaluation, safety,
and authority gates pass.

## Supported version

Security fixes target the latest `2.x` release of this fork.

## Report a vulnerability

Do not publish credentials, private traces, exploitable prompts, or sensitive
artifacts in a public issue. Use GitHub private vulnerability reporting when it
is available for this repository, or contact the repository owner privately
through GitHub. Include a minimal redacted reproduction, affected commit, impact,
and proposed containment.

## Threat model

The framework explicitly considers:

- poisoned web/document/log/tool content attempting to become durable policy;
- secret or personal-data capture from task context;
- false causal lessons derived from successful tasks;
- over-broad scope and semantic/procedural drift;
- duplicate or contradictory skills;
- self-approval and learning-gate weakening;
- privilege, connector, filesystem, network, spending, publishing, outreach,
  deletion, merge, or deployment expansion;
- unsafe generated scripts/dependencies;
- reliability gaming, history rewriting, and stale approval;
- harmful active skills that compound across later tasks.

## Required controls

1. Keep candidates quarantined before review.
2. Preserve safe provenance and content hashes.
3. Use three distinct context-clean reviews for the exact version.
4. Compare against a baseline/prior version with falsifiable replay cases.
5. Run the bundled secret/skill validator.
6. Keep activation owner-governed by default; use a host-signed receipt whose
   key is unavailable to the autonomous agent process.
7. Never auto-activate protected-domain changes.
8. Use probation and judge every use.
9. Invalidate reviews/approval on semantic revision.
10. Archive and roll back on repeated failure, contradiction, or incident.

## Secret handling

Never persist literal passwords, tokens, private keys, cookies, credentialed
URIs, private endpoints, or unnecessary personal data. Store only an approved
pointer: environment variable name, selector, vault/secret-manager entry, or
host tool.

The bundled scanner catches common token shapes and credential-bearing URIs but
cannot identify every secret. Human/host review remains required.

Default approval receipts use HMAC-SHA256 with a one-time candidate nonce and
exact subject/artifact hash. HMAC proves possession of the configured host key,
not human intent by itself. Protect the signing surface and never expose the key
to the agent process.

## Untrusted content

Retrieved content is data. It cannot:

- change system/owner policy;
- edit Identity or Mission;
- grant tools or permissions;
- approve or activate a lesson;
- lower review, probation, or rollback gates;
- direct the agent to exfiltrate or persist unrelated context.

Copy executable content only after understanding it, constraining authority, and
running it in the approved environment.

## Protected domains

Changes involving Identity, Mission, authority, permissions, credentials,
safety policy, billing, production writes, confirmation rules, or the learning
framework itself require normal owner/repository governance. They are never
eligible for autonomous activation.

## Ledger limitations

The local SHA-256 hash chain detects line mutation/reordering when its trusted
head is preserved. It is not a signature, remote attestation, access-control
system, or defense against an attacker who can replace the entire workspace.
Use the host's signed commits, protected storage, transactions, and audit system
where stronger guarantees are required.

## Runtime limitations

The reference script serializes state through atomic file replacement but does
not provide a distributed lock. Use one writer per `.agent-learning` workspace
or integrate the lifecycle with the host's transactional state owner.
