# Copilot Instructions

## Project Purpose

This repository defines **AI-powered skills for DITA XML authoring**, targeting DITA writers and XSLT developers. The primary artifact is `specification.md`, which is the authoritative source for all skill definitions, validation rules, and templates.

## Scripts

`validate-dita-topic/scripts/validate_dita_topic.py` — Python 3.9+, stdlib only (`xml.etree.ElementTree`).

```bash
python validate-dita-topic/scripts/validate_dita_topic.py <file.dita> [topic_type]
# topic_type: topic | concept | task | reference | troubleshooting | glossentry
# Exit 0 = valid, 1 = invalid. Output: JSON { is_valid, errors[], warnings[] }
```

Full rule catalogue: `validate-dita-topic/references/RULES.md`

The project is a **specification-driven skill library** built around DITA 1.3. Each skill maps to a discrete capability:

| Skill | Type |
|---|---|
| `validate-dita-topic` | Validation |
| `validate-ditamap` | Validation |
| `validate-bookmap` | Validation |
| `generate-dita-topic` | Generation |
| `generate-ditamap` | Generation |
| `generate-bookmap` | Generation |
| `dita-best-practices` | Analysis |
| `refactor-dita-content` | Refactoring |
| `xslt-dita-helper` | Transformation |

Skills follow a consistent **Input → Parse → Validate/Generate → Structured Output** workflow (see §6 of specification.md).

## DITA 1.3 Conventions

- **Topic types and required body elements**: `concept` → `<conbody>`, `task` → `<taskbody>`, `reference` → `<refbody>`, generic `topic` → `<body>`
- **Every topic must have** `<title>` and the correct body element; `<shortdesc>` is recommended
- **Maps**: `<topicref>` must always carry either `href` or `keyref`
- **Bookmap hierarchy** (in order): `booktitle?`, `bookmeta?`, `frontmatter?`, `chapter+`, `appendix*`, `backmatter?` — at least one `<chapter>` is required
- **IDs** must be unique within a document; validate `conref` and `keyref` targets are resolvable
- **Reuse-first**: prefer `conref`/`keyref` over duplicating content; flag redundant content in best-practices checks

## Skill Output Schema

Validation skills return:
```json
{ "is_valid": true|false, "errors": [], "warnings": [] }
```

Generation skills return well-formed XML using the canonical templates defined in §3 of specification.md. Template placeholders use `{{double_braces}}` (e.g., `{{title}}`).

## System Prompt Baseline

All skills operate under this system prompt context (§4):
> You are a DITA XML expert based on DITA 1.3 specification. Enforce strict XML validity, follow DITA specialization rules, suggest improvements, and promote reusable structured content.

## Extensibility

Planned future skills (do not implement without spec entry): Schematron rule generator, DITA specialization assistant, translation readiness checker, content reuse analyzer.
