# Validation Rules — validate-bookmap

Full rule catalogue for `scripts/validate_bookmap.py`.

## Root

| Rule ID | Level | Trigger |
|---|---|---|
| `well-formed` | Error | XML parse failure |
| `root-element` | Error | Root is not `<bookmap>` |
| `id-recommended` | Warning | `<bookmap>` has no `@id` attribute |

## Element order (DTD content model)

DTD order: `(title|booktitle)?, bookmeta?, frontmatter?, chapter*, part*, (appendices?|appendix*), backmatter?, reltable*`

| Rule ID | Level | Trigger |
|---|---|---|
| `element-order` | Error | An element appears before a later-phase element has been seen |

Phase assignments:

| Phase | Elements |
|---|---|
| 0 | `title`, `booktitle` |
| 1 | `bookmeta` |
| 2 | `frontmatter` |
| 3 | `chapter` |
| 4 | `part` |
| 5 | `appendices`, `appendix` |
| 6 | `backmatter` |
| 7 | `reltable` |

## Singleton elements

| Rule ID | Level | Trigger |
|---|---|---|
| `booktitle-singleton` | Error | `<booktitle>` appears more than once |
| `title-singleton` | Error | `<title>` appears more than once |
| `bookmeta-singleton` | Error | `<bookmeta>` appears more than once |
| `frontmatter-singleton` | Error | `<frontmatter>` appears more than once |
| `backmatter-singleton` | Error | `<backmatter>` appears more than once |
| `appendices-singleton` | Error | `<appendices>` appears more than once |

## Content requirements

| Rule ID | Level | Trigger |
|---|---|---|
| `chapter-required` | Error | No `<chapter>` or `<part>` present |
| `mainbooktitle-required` | Error | `<booktitle>` missing `<mainbooktitle>` child |
| `appendices-appendix-mixed` | Error | Both `<appendices>` and bare `<appendix>` used |
| `href-or-keyref-required` | Error | `<chapter>`, `<part>`, or `<appendix>` has no `@href` or `@keyref` |
| `broken-href` | Warning | `@href` file does not exist on disk (file mode only) |
