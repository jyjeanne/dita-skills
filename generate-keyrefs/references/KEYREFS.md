# DITA Key Space and Keyref Reference

Quick reference for DITA 1.3 key definitions and key references — the concepts
behind the `generate-keyrefs` skill.

---

## Key definition anatomy

```xml
<keydef key="KEY-NAME"
        href="target.dita"     <!-- optional: resource href -->
        scope="local|peer|external"
        format="dita|html|pdf|png|…"
        processing-role="resource-only">
  <topicmeta>
    <navtitle>Display title</navtitle>
    <keywords>
      <keyword>Inline text value</keyword>
    </keywords>
  </topicmeta>
</keydef>
```

`<keydef>` is specialised from `<topicref>` with `processing-role="resource-only"`
set by default — it never appears in a TOC.

---

## Key types and their keydef patterns

### Text substitution key

Provides an inline text value rendered wherever `keyref="…"` is used on
`<keyword>`, `<ph>`, `<term>`, etc.

```xml
<keydef key="product-name">
  <topicmeta>
    <keywords>
      <keyword>ACME Pro 2.0</keyword>
    </keywords>
  </topicmeta>
</keydef>
```

Usage:
```xml
Download <keyword keyref="product-name"/> from the portal.
<!-- renders as: Download ACME Pro 2.0 from the portal. -->
```

### External link key

```xml
<keydef key="support-portal"
        href="https://support.acme.com"
        scope="external"
        format="html"/>
```

Usage:
```xml
<xref keyref="support-portal">ACME Support</xref>
```

### Image key

```xml
<keydef key="logo-main" href="images/logo-v2.svg" format="svg"/>
```

Usage:
```xml
<image keyref="logo-main" alt="ACME logo"/>
```

### Topic reference key

```xml
<keydef key="install-guide" href="topics/install.dita"/>
```

Usage in a map:
```xml
<topicref keyref="install-guide"/>
```

Usage in a topic:
```xml
<xref keyref="install-guide">Installation Guide</xref>
```

---

## `scope` attribute values

| Value | When to use |
|-------|-------------|
| `local` | Target is in the same DITA publication (default) |
| `peer` | Target is in a related but separately built publication |
| `external` | Target is outside any DITA publication (web URL, absolute path) |

---

## `format` attribute values

| Value | Use for |
|-------|---------|
| `dita` | DITA topic (default when no `format` given and `href` ends in `.dita`) |
| `html` | External HTML page |
| `pdf` | PDF file |
| `png` / `jpg` / `svg` | Image files |
| `ditamap` | DITA map referenced as a key target |

---

## Key scope (`@keyscope`)

Keys are scoped to the map branch they are defined in.  
A `@keyscope` attribute creates a named scope:

```xml
<topicref href="module-a/module-a.ditamap" keyscope="module-a">
  <!-- keys defined here are prefixed "module-a." when accessed from outside -->
</topicref>
```

Cross-scope reference:
```xml
<xref keyref="module-a.install-guide"/>
```

---

## Key resolution order (DITA 1.3)

1. Keys are resolved in **map order** — the first `<keydef>` with a given key name wins.
2. Keys in child maps override keys from parent maps **only within their keyscope**.
3. Duplicate key definitions in the same scope produce a warning; the first wins.

---

## Keyref on different element types

| Element | What keyref provides |
|---------|---------------------|
| `<keyword keyref="k"/>` | Text content from `<keyword>` in keydef's `<topicmeta>` |
| `<ph keyref="k"/>` | Text content from first `<keyword>` in keydef |
| `<term keyref="k"/>` | Text + optional link to the target topic |
| `<xref keyref="k"/>` | Link to the keydef target href |
| `<link keyref="k"/>` | Related link to keydef target |
| `<image keyref="k"/>` | Image from keydef href |
| `<topicref keyref="k"/>` | Topic from keydef href |

---

## Checklist: before running `--apply`

- [ ] Commit or back up all topic files (`git commit` or copy)
- [ ] Run in dry-run mode first (no `--apply`) to review the change list
- [ ] Verify generated key names are meaningful; rename in `keydef_block` if needed
- [ ] Paste `keydef_block` into your root map **before** running `--apply`
- [ ] After applying, run `validate-ditamap` to confirm all keyrefs resolve
- [ ] Run `validate-dita-topic` on rewritten files to catch any structural issues
