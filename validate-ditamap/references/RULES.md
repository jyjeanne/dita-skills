# Validation Rules — validate-ditamap

Full rule catalogue for `scripts/validate_ditamap.py`.

## Map root

| Rule ID | Level | Trigger |
|---|---|---|
| `well-formed` | Error | XML parse failure |
| `root-element` | Error | Root is not `<map>` |
| `id-recommended` | Warning | `<map>` has no `@id` attribute |
| `title-recommended` | Warning | No `<title>` child and no `@title` attribute |

## topicref

| Rule ID | Level | Trigger |
|---|---|---|
| `href-or-keyref-required` | Error | `<topicref>` has neither `@href` nor `@keyref` nor `@keys` |
| `href-or-keyref-recommended` | Warning | `<topicref>` has `@keys` but no `@href` (pure key definition on topicref) |
| `broken-href` | Warning | `@href` file does not exist on disk (file mode only) |
| `collection-type-invalid` | Error | `@collection-type` is not `unordered`, `sequence`, `choice`, or `family` |
| `nesting-depth` | Warning | topicref depth exceeds 5 levels |

## Keys

| Rule ID | Level | Trigger |
|---|---|---|
| `duplicate-key` | Error | Same `@keys` value defined more than once |

## Reltable

| Rule ID | Level | Trigger |
|---|---|---|
| `reltable-column-mismatch` | Error | `<relrow>` cell count differs from `<relcolspec>` count |
