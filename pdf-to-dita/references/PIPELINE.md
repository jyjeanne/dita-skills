# PDF → DITA Pipeline Reference

## Stage 1 — PDF extraction heuristics

### Heading level algorithm

```
body_size     = modal font size across all words in the document
size_map      = {font_size: level} for each distinct size > body_size × 1.14
                ordered largest→smallest, assigned level 1, 2, 3, 4

word is heading if:
    avg_size_of_line / body_size  ≥  1.15
    AND  avg_size_of_line  is in  size_map
```

### List detection (text-based)

| Pattern | Type |
|---------|------|
| `^\s*\d+[.\)]\s+` | Ordered list item |
| `^\s*[•·\-\*]\s+` | Unordered list item |
| Anything else | Paragraph |

Consecutive items of the same type are merged into a single `list` block.

### Table extraction

Tables are extracted using pdfplumber's `page.extract_tables()`. Each table is converted to a `{"type": "table", "headers": [...], "rows": [[...]]}` block attached to the section currently open when the page is processed.

---

## Stage 2 — Topic-type classification

### Decision rules (evaluated in order)

1. `_REFERENCE_TITLE_RE` matches → `reference`
2. `_TASK_TITLE_RE` matches → `task`
3. Ordered-list items ≥ 3 → `task`
4. Table headers contain `name`, `parameter`, `property`, `attribute`, or `command` → `reference`
5. Default → `concept`

### DITA body mapping

| Topic type | Root element | Body element | Steps |
|------------|-------------|--------------|-------|
| `concept`  | `<concept>` | `<conbody>`  | — |
| `task`     | `<task>`    | `<taskbody>` | `<steps>` / `<step>` / `<cmd>` |
| `reference`| `<reference>`| `<refbody>` | — |

### Ordered-list → `<steps>` conversion (task only)

Each ordered-list item becomes a `<step>` with a `<cmd>` child. Non-ordered content before or after the list is written as plain `<p>` elements in `<taskbody>`.

### Sub-section flattening

Sub-sections (level 2+) that are children of a top-level section are either:
- **Inlined** as `<section>` blocks inside the parent topic body (default), or
- **Promoted** to separate topic files when the section has its own title.

Top-level sections (level 1) always become separate topic files.

### Slug and ID generation

```python
slug = re.sub(r"[^\w\s-]", "", title.lower())
slug = re.sub(r"[\s_]+", "-", slug)[:60]
```

Duplicate slugs get a numeric suffix: `overview`, `overview-2`, `overview-3`, …

---

## Stage 3 — Validation rules applied

Delegates to:

| File type | Validator | Key rules |
|-----------|-----------|-----------|
| `.dita` | `validate_dita_topic.py` | Required elements, body tag match, shortdesc quality, duplicate IDs |
| `.ditamap` | `validate_ditamap.py` | `href` or `keyref` on every topicref, nesting depth ≤ 5, valid `@collection-type` |

Validation is non-destructive — files are not modified in this stage.

---

## Stage 4 — Optimization rules

### Auto-fixable

| Rule ID | Condition | Fix |
|---------|-----------|-----|
| `missing-shortdesc` | `<shortdesc>` absent | Insert first sentence of first `<p>` in body (max 50 words) |

### First-sentence algorithm

```
1. Find first <p> in <conbody>/<taskbody>/<refbody>/<body>
2. Split on sentence boundary: r"(?<=[.!?])\s+"
3. Take sentences[0]
4. If len(words) > 50: truncate at word 50, append "…"
5. Insert <shortdesc> after <title> in the root element
```

### Not auto-fixable (manual review required)

- Topic too long (`topic-too-long`)
- Too many steps (`too-many-steps`)
- Deeply nested content (`nesting-too-deep`)
- Duplicate paragraphs (`duplicate-content`)

---

## Stage 5 — Review checks

Delegates entirely to `review_dita_guide.py --best-practices`. Checks include:

- All `href` values in the map resolve to existing files
- No circular map references
- No duplicate `@id` values across the guide
- Best-practices findings aggregated across all topics

---

## Output directory structure

```
output_dir/
├── extracted.json          Stage 1 output — structured PDF content
├── root.ditamap            Stage 2 output — DITA root map
├── topics/
│   ├── overview.dita
│   ├── installation.dita
│   └── ...
├── validation_report.json  Stage 3 output
├── optimization_report.json Stage 4 output
└── review_report.json      Stage 5 output
```

---

## Improving output quality

### Pre-processing the PDF

| Problem | Recommended pre-processor |
|---------|--------------------------|
| Scanned PDF (no selectable text) | `ocrmypdf` |
| Two-column layout | `pdfplumber` crop + split columns |
| Password-protected PDF | `qpdf --decrypt` |
| Complex tables split across pages | Manual merge in extracted.json |

### Post-processing the DITA

After running the pipeline, consider using these dita-skills for further improvement:

| Skill | When to use |
|-------|-------------|
| `refactor-dita-content` | Split oversized topics, add conrefs, convert hrefs to keyrefs |
| `dita-best-practices` | Standalone re-analysis after manual edits |
| `validate-bookmap` | If you promote the root map to a bookmap |
| `ditaval-helper` | Add conditional filtering to the generated content |
