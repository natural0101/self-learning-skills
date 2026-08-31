# Owner/governor approval protocol

Read this when a probationary candidate is ready for durable activation.

The lifecycle script cannot prove that a caller is the owner merely because the
caller writes `--reviewer owner`. Default configuration therefore uses a
host-signed approval receipt.

## Default mode: `host-receipt`

The trusted host, not the autonomous agent process, holds the HMAC key named by
`config.json` (`SELF_LEARNING_APPROVAL_KEY` by default).

### 1. Generate the exact request

```bash
python <self-learning-root>/scripts/learning_cycle.py approval-request \
  --root .agent-learning \
  --candidate <candidate-id> > approval-request.json
```

The request binds:

- candidate ID;
- candidate version;
- exact subject hash, including the sealed skill artifact hash;
- one-time approval nonce;
- decision type.

### 2. Review through the real owner surface

The host presents the exact candidate, receipt, evaluations, reviews, boundary,
risk, and rollback to the authenticated owner/governor. The agent cannot accept
its own request.

### 3. Create the receipt

The trusted host adds:

```json
{
  "approver": "authenticated-owner-id",
  "authority_ref": "stable-host-review-receipt",
  "approved_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

It computes HMAC-SHA256 over canonical JSON of every receipt field except
`signature`:

```text
UTF-8 JSON, sorted keys, separators ',' and ':', ensure_ascii=false
```

Then it adds the lowercase hex `signature`. Use
`assets/approval-receipt.template.json` as the shape.

The key must never be written to a candidate, receipt, command argument,
repository, trace, or agent-visible environment.

### 4. Record the verified receipt

A trusted host process exposes the key only for this operation:

```bash
SELF_LEARNING_APPROVAL_KEY='<host-secret>' \
python <self-learning-root>/scripts/learning_cycle.py approve \
  --root .agent-learning \
  --candidate <candidate-id> \
  --receipt approval-receipt.json
```

The script checks signature, candidate ID, version, subject hash, nonce,
decision, approver, and authority reference. It anchors the accepted receipt in
the hash-chained ledger. Activation later requires the candidate snapshot and
ledger event to agree.

Do not run the trusted approval process inside the same unrestricted tool
boundary as the autonomous agent. Host access control is the real authority;
HMAC only carries its attestation into the local lifecycle.

## Local-manual mode

For a single-user local experiment, an operator may explicitly edit
`.agent-learning/config.json`:

```json
{
  "approval_mode": "local-manual"
}
```

Then run from an owner-controlled terminal that the autonomous agent cannot
invoke:

```bash
python <self-learning-root>/scripts/learning_cycle.py approve \
  --root .agent-learning \
  --candidate <candidate-id> \
  --reviewer <owner-id> \
  --authority-ref <terminal/session/change-ticket> \
  --notes "<bounded approval>"
```

`local-manual` records provenance but does not authenticate the human. Do not
use it where the agent shares the same shell/filesystem authority.

## TeamON One

TeamON One should use its existing authenticated owner Memory review or normal
repository/product release authority instead of exposing this local approval
command to the tenant agent. The local lifecycle receipt can support that
review, but it does not replace it.

## Revision and replay protection

Every semantic revision creates a new version, artifact hash, subject hash, and
approval nonce. Old receipts, reviews, and approval cannot activate the new
version. Archiving and rollback preserve the old evidence rather than deleting
it.
