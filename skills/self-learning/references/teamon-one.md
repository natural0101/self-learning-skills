# TeamON One integration profile

This profile maps the generic lifecycle onto TeamON One without adding a second
agent runtime, memory plane, store, service, or authority owner.

## Fixed ownership

- One person-owned capsule contains one permanent agent.
- TeamON Lite remains the only provider/session engine.
- Context MCP remains the only generic lazy retrieval plane.
- Person-scoped accepted Memory is retrieved through Context MCP.
- Narrow accepted lessons are projected only into the exact selected World.
- The owner is the only authority who accepts, edits, rejects, supersedes, or
  forgets durable Memory.
- Skills and blueprints remain exact, immutable, and checksum-verified parts of
  composition.
- Identity, Mission, credentials, modules, permissions, and host authority cannot
  be modified by a learning proposal.

## Mapping

| Generic lifecycle | TeamON One owner/path |
|---|---|
| task evidence | current Thread/WorkRun receipts and domain checks |
| tentative observation | append-only Notebook when useful |
| one-line durable lesson | `memory_propose` into private pending |
| owner review | existing owner Memory review action |
| accepted person lesson | governed Memory, retrieved via Context MCP |
| accepted narrow lesson | exact selected-World context only |
| skill candidate | project/repository artifact outside active composition |
| probation | owner-created Task → isolated WorkRun or explicit foreground eval |
| activation | owner/product build selects exact checksum-verified package |
| rollback | composition rollback + archived/superseded receipt |

Pending proposals stay outside Context and cannot affect subsequent turns until the
owner accepts them. A successful `context.read` proves retrieval only, not useful
application; improvement still requires a judged result.

## Turn behavior

Before substantial similar work:

1. use bounded Context search only when accepted person Memory exists and the task
   warrants it;
2. apply exact selected-World narrow lessons already projected by the server;
3. avoid loading sibling World state, private Threads, credentials, or unrelated
   Memory;
4. state no readiness claim from a stale receipt;
5. judge the new result through owner feedback or an objective domain gate.

After significant work, route once:

- unfinished → Checkpoint;
- unverified useful observation → Notebook;
- verified reusable owner lesson → one `memory_propose` after duplicate/conflict
  search;
- canonical fact → Knowledge owner path;
- reusable procedural package → quarantined skill candidate in its repository;
- otherwise → nothing.

## Proactivity

There is no always-hot learning process. Bounded practice uses the existing
owner-created Tasks ledger and isolated WorkRun. A schedule receipt proves only that
a trigger was recorded. It does not prove a connector is ready or a result exists.

A WorkRun may propose a lesson, but owner acceptance occurs only through the existing
owner Web surface. It may not broaden the task, contact external parties, access
sibling capsules, or alter composition.

## Approval

For one-line Memory, TeamON's governed owner acceptance is authoritative; do not
replace it with the reference CLI's local approval file.

For repository skill packages:

1. candidate bytes are committed on a feature branch;
2. three review receipts bind the exact commit/artifact hash;
3. CI/evaluation supplies probation evidence;
4. owner/product governance approves the exact version;
5. composition pins its checksum;
6. activation occurs only through the normal build/release boundary.

The reference HMAC receipt is useful for standalone deployments, but TeamON should
use its host authority and repository/release receipts instead of exposing a signing
secret to the tenant agent.

## Forbidden integrations

- a second “learning memory” indexed beside Context MCP;
- direct agent writes to accepted Memory;
- automatic edits to generated `AGENTS.md`;
- dynamic skill installation outside exact composition;
- a new agent engine or general MCP runtime;
- always-running self-training;
- activation from self-reported confidence;
- using Notebook as an authoritative intermediate store;
- treating a local receipt as Bitrix, production, readiness, or owner evidence.
