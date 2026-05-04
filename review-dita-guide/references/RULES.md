# review-dita-guide — Rule Catalogue

Rules are grouped by scope: **per-file** rules delegate to existing
skill validators; **cross-guide** rules are unique to this skill.

---

## Cross-guide rules (RG-*)

### RG-001 — href-target-missing
**Severity:** Error  
**Element:** `topicref`, `chapter`, `mapref`, etc.

An `@href` attribute in a map references a file path that does not exist
on the file system relative to that map's location.

**DTD reference:** All map referencing elements carry `@href CDATA #IMPLIED`
(map.mod); DITA processors are required to resolve the reference before
processing.

**Example (bad):**
```xml
<topicref href="install/setup.dita"/>
<!-- setup.dita does not exist -->
```

---

### RG-002 — circular-reference
**Severity:** Error  
**Element:** `mapref`, `topicref` (pointing to a `.ditamap`)

A map includes itself, directly or through a chain of child maps,
creating an infinite traversal loop.

**Example (bad):**
```
root.ditamap
  └── chapter1.ditamap
        └── root.ditamap   ← circular
```

---

### RG-003 — duplicate-guide-id
**Severity:** Warning  
**Element:** root element of topic files

Two or more topic files within the same guide carry the same root `@id`
value. While the DITA 1.3 spec requires `@id` to be unique within a
single document, best practice requires uniqueness across the whole guide
to prevent ambiguous cross-references and search-engine collisions.

**DTD reference:** `topic.dtd` — `@id ID #REQUIRED` on the root element.

**Example (bad):**
```xml
<!-- install.dita -->
<task id="setup">…</task>

<!-- upgrade.dita -->
<task id="setup">…</task>   <!-- duplicate guide-level ID -->
```

---

## Per-file rules (delegated)

Each file discovered during traversal is validated by the appropriate
existing validator. See those skills for their full rule catalogues.

| File type | Validator skill | Rule catalogue |
|-----------|----------------|----------------|
| `.dita` topic | `validate-dita-topic` | `validate-dita-topic/references/RULES.md` |
| `.ditamap` | `validate-ditamap` | `validate-ditamap/references/RULES.md` |
| `.bookmap` | `validate-bookmap` | `validate-bookmap/references/RULES.md` |

---

## Best-practice findings (opt-in, `--best-practices`)

When `--best-practices` is passed, each topic file is additionally
analysed by the `dita-best-practices` skill.  
See `dita-best-practices/references/RULES.md` for the full catalogue.

Findings are reported under `"best_practices"` in each file's result
object and do **not** affect the `is_valid` flag or exit code.

---

## Severity and exit-code mapping

| Rule | Severity | Affects `is_valid` | Affects exit code |
|------|----------|--------------------|-------------------|
| `href-target-missing` | Error | Yes (missing file = invalid) | `1` |
| `circular-reference` | Error | No (not per-file) | `1` |
| `duplicate-guide-id` | Warning | No | `0` |
| Per-file validator errors | Error | Yes | `1` |
| Per-file validator warnings | Warning | No | `0` |
| Best-practice findings | Info | No | `0` |
