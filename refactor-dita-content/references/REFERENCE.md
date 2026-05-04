# Refactoring Reference — refactor-dita-content

Decision logic and constraints for each refactoring operation.

## split

**When to split:**
- Topic body > 300 words OR > 50 block elements (same threshold as `dita-best-practices`)
- Multiple `<section>` elements each with their own `<title>` → each becomes a separate topic

**Algorithm:**
1. Read the source topic; identify all `<section>` children of the body element
2. For each section with a `<title>`: create a new topic file of the same type, move the section contents into the body
3. Replace the original section with a `<topicref>` in the output map fragment
4. Sections without a `<title>` remain in the parent topic
5. Validate each generated topic with `validate-dita-topic` before writing

**File naming:** slugify the section title (spaces → hyphens, lowercase, strip punctuation)

**Constraints:**
- Does not recursively split nested sections
- Does not split `<refbody>` `<properties>` tables — they must stay with their `<refsyn>`

---

## extract-conrefs

**Similarity threshold:** Jaccard similarity ≥ 0.85 on word sets (minimum 5 words)

**conref library format:**
```xml
<topic id="conref-library">
  <title>Reusable Content</title>
  <body>
    <p id="reuse-p-001">Reusable paragraph text.</p>
  </body>
</topic>
```

**ID assignment:** `reuse-<element>-<sequential-number>` (e.g. `reuse-p-001`)

**conref reference format:** `library.dita#conref-library/reuse-p-001`

**Constraints:**
- Refuses to create chained conrefs (target already uses `@conref`)
- Minimum 3 words; single-word fragments are not extracted
- Does not extract `<title>` or `<shortdesc>` elements

---

## href-to-keyref

**Key naming:** `key-<filename-stem>` (e.g. `intro.dita` → `key-intro`)

**Steps:**
1. Scan all `<topicref href="...">` in the map; add `keys="key-<stem>"` if absent
2. Scan all topics referenced by the map for `<xref href="...">` and `<link href="...">`
3. Replace matched hrefs with `keyref="key-<stem>"`
4. External links (`http://`, `https://`) are not modified

**Constraints:**
- Does not modify hrefs that already have a `keyref` on the same element
- Writes modified files to `--output-dir`; originals are never overwritten

---

## upgrade

**Supported upgrades:**

| From | To | Body transformation |
|---|---|---|
| `topic` | `concept` | `<body>` → `<conbody>` |
| `topic` | `task` | `<body>` → `<taskbody>` + scaffold `<steps>` from `<ol>` if present |
| `topic` | `reference` | `<body>` → `<refbody>` + wrap `<simpletable>` in `<properties>` if present |

**Validation gate:** the upgraded topic is validated with `validate-dita-topic` before writing; the upgrade is aborted if errors remain.

**Constraints:**
- Only upgrades generic `<topic>` → specialised type; never downgrades
- Does not upgrade specialised topics (e.g. `concept` → `task`)
