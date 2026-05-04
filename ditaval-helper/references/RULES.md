# DITAVAL Validation Rules — ditaval-helper

Full rule catalogue for `scripts/ditaval_helper.py validate`.

## Root

| Rule ID | Level | Trigger |
|---|---|---|
| `well-formed` | Error | XML parse failure |
| `root-element` | Error | Root is not `<val>` |
| `unknown-element` | Warning | Unrecognised element inside `<val>` |

## `<prop>`

| Rule ID | Level | Trigger |
|---|---|---|
| `att-required` | Error | `<prop>` missing `@att` |
| `action-required` | Error | `<prop>` missing `@action` |
| `action-invalid` | Error | `@action` is not `include`, `exclude`, `flag`, or `passthrough` |
| `duplicate-prop` | Error | Same `@att`+`@val` combination appears more than once |
| `flag-no-feedback` | Warning | `action="flag"` with no visual attributes and no `<startflag>`/`<endflag>` |
| `style-invalid` | Error | `@style` is not one of `underline`, `double-underline`, `italics`, `overline`, `line-through` |
| `imageref-missing` | Warning | `<startflag>` or `<endflag>` `imageref` path does not exist on disk |

## `<revprop>`

| Rule ID | Level | Trigger |
|---|---|---|
| `action-required` | Error | `<revprop>` missing `@action` |
| `action-invalid` | Error | `@action` value is invalid |
| `flag-no-feedback` | Warning | `action="flag"` with no visual attributes or `<startflag>` |
| `imageref-missing` | Warning | `imageref` does not exist on disk |

## `<style-conflict>`

| Rule ID | Level | Trigger |
|---|---|---|
| `style-conflict-singleton` | Error | `<style-conflict>` appears more than once in `<val>` |
