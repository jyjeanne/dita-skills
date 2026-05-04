# Best Practices Rules — dita-best-practices

Full catalogue of checks applied by `scripts/best_practices.py`.

## shortdesc

| Rule ID | Severity | Trigger |
|---|---|---|
| `shortdesc` | warning | `<shortdesc>` is absent |
| `shortdesc` | warning | `<shortdesc>` is empty |
| `shortdesc` | warning | `<shortdesc>` exceeds 50 words |
| `shortdesc` | warning | `<shortdesc>` contains a block-level element |

## topic-size

| Rule ID | Severity | Trigger |
|---|---|---|
| `topic-size` | warning | Body contains more than 300 words |
| `topic-size` | warning | Body contains more than 50 block elements |

## empty

| Rule ID | Severity | Trigger |
|---|---|---|
| `empty` | warning | Empty `<cmd>`, `<title>`, `<shortdesc>`, or `<p>` element |

## ids

| Rule ID | Severity | Trigger |
|---|---|---|
| `ids` | info | `<section>`, `<fig>`, `<table>`, `<note>`, or `<example>` has no `@id` |

## steps (task only)

| Rule ID | Severity | Trigger |
|---|---|---|
| `steps` | warning | `<steps>` or `<steps-unordered>` has more than 10 `<step>` elements |

## nesting

| Rule ID | Severity | Trigger |
|---|---|---|
| `nesting` | warning | `<section>`, `<topicref>`, or `<step>` nested more than 3 levels deep |

## reuse

| Rule ID | Severity | Trigger |
|---|---|---|
| `reuse` | info | Near-duplicate `<p>` (Jaccard similarity ≥ 0.85, minimum 5 words) |
| `reuse` | info | `<topicref href="...">` in a map has no `@keys` attribute |

## conref

| Rule ID | Severity | Trigger |
|---|---|---|
| `conref` | error | `@conref` target element also carries `@conref` (chained conref) |

## Severity levels

- **error** — affects exit code (exit 1); must be fixed
- **warning** — quality issue; strongly recommended to fix
- **info** — informational suggestion; safe to ignore
