# Body file templates

## Learning (URL) — body file

Outgoing links stay **Intra-KS** (same Knowledge System). Do **not** link across KS roots.

```markdown
# Message Queue System Design

One-sentence description for the index.

See also:

* [Related Learning](related-learning.md)

## Overview

…

## Citations

* [Source title](https://example.com/…)
```

Frontmatter is written by the script: `resource` = URL, `id` = minted UUID, `tags` includes `web-ingestion`.

## Learning (conversation) — body file

Same edge rule: **See also** only other concepts in the same KS.

```markdown
# Git Workflow Notes

Summarizes git practices discussed in conversation.

See also:

* [Related Learning](related-learning.md)

## Practices

…

## Citations

* Curated from agent conversation, 2026-07-06.
```

## Document / Reference — Intra-KS See also; Cross-KS via associate

Body links stay in the same KS. For foundations in another KS, use `okf associate` after ingest — do not write `../personal/...` into the body.

```markdown
# Deploy and Debug the Payments Service

Practical deploy/debug notes for the payments stack.

See also:

* [Configure The Event Relay](configure-event-relay.md)

## Steps

…
```
