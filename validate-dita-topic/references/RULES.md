# Validation Rules Reference

Full catalogue of rules applied by `scripts/validate_dita_topic.py`.
Derived from DITA 1.3 DTDs in `dtd/technicalContent/dtd/` and `dtd/base/dtd/`.

## All topic types

| Rule ID | Level | Trigger |
|---|---|---|
| `well-formed` | Error | XML parse failure |
| `root-element` | Error | Root tag does not match the requested `topic_type` |
| `unknown-type` | Error | Root element is not a known DITA topic type |
| `id-required` | Error | Root element missing `@id` attribute |
| `title-required` | Error | `<title>` is not the first child of the root |
| `shortdesc-recommended` | Warning | `<shortdesc>` absent |
| `shortdesc-no-blocks` | Warning | `<shortdesc>` contains a block element |
| `shortdesc-length` | Warning | `<shortdesc>` exceeds 50 words |
| `prolog-order` | Error | `<prolog>` appears after the body element |
| `related-links-order` | Error | `<related-links>` appears before the body element |
| `foreign-element` | Error | Element exclusive to another topic type used here |
| `unique-id` | Error | Duplicate `@id` value within document |
| `conref-format` | Error | `@conref` value missing `#` fragment separator |
| `keyref-unverified` | Warning | `@keyref` cannot be resolved without map context |

## Concept

| Rule ID | Level | Trigger |
|---|---|---|
| `body-required` | Error | `<conbody>` missing |
| `conbodydiv-section-mix` | Warning | `<section>` and `<conbodydiv>` mixed as siblings in `<conbody>` |

## Task

| Rule ID | Level | Trigger |
|---|---|---|
| `body-required` | Error | `<taskbody>` missing |
| `steps-recommended` | Warning | No steps element of any kind in `<taskbody>` |
| `step-required` | Error | `<steps>` or `<steps-unordered>` contains no `<step>` |
| `cmd-required` | Error | A `<step>` is missing `<cmd>` |
| `step-count` | Warning | More than 10 `<step>` elements in one `<steps>` block |
| `prereq-singleton` | Error | `<prereq>` appears more than once |
| `context-singleton` | Error | `<context>` appears more than once |
| `result-singleton` | Error | `<result>` appears more than once |
| `tasktroubleshooting-singleton` | Error | `<tasktroubleshooting>` appears more than once |
| `postreq-singleton` | Error | `<postreq>` appears more than once |

## Reference

| Rule ID | Level | Trigger |
|---|---|---|
| `body-required` | Error | `<refbody>` missing |
| `property-empty` | Warning | `<property>` row has no `<proptype>`, `<propvalue>`, or `<propdesc>` |

## Troubleshooting

| Rule ID | Level | Trigger |
|---|---|---|
| `body-required` | Error | `<troublebody>` missing |
| `condition-singleton` | Error | `<condition>` appears more than once |
| `troubleSolution-required` | Error | No `<troubleSolution>` in `<troublebody>` |
| `troubleSolution-empty` | Warning | A `<troubleSolution>` has neither `<cause>` nor `<remedy>` |

## Glossentry

| Rule ID | Level | Trigger |
|---|---|---|
| `glossterm-required` | Error | `<glossterm>` missing |
| `glossdef-required` | Error | `<glossdef>` missing |
