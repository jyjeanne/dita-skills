# 📘 DITA AI Skills Specification

## 1. Overview

### 1.1 Purpose

This document defines AI-powered skills for assisting DITA writers and XSLT developers in:

* Validating DITA XML files against DITA 1.3 DTDs
* Generating DITA templates (topic, ditamap, bookmap)
* Enforcing DITA best practices
* Supporting structured authoring workflows

### 1.2 DTD Reference

All validation rules are derived from the official DITA 1.3 DTDs located in the `dtd/` directory:

| DTD path | Covers |
| ---------------------------------------- | --------------------------------- |
| `dtd/technicalContent/dtd/concept.dtd`   | Concept topics                    |
| `dtd/technicalContent/dtd/task.dtd`      | Task topics (strict taskbody)     |
| `dtd/technicalContent/dtd/generalTask.dtd` | General task (relaxed taskbody) |
| `dtd/technicalContent/dtd/reference.dtd` | Reference topics                  |
| `dtd/technicalContent/dtd/topic.dtd`     | Base topic                        |
| `dtd/technicalContent/dtd/troubleshooting.dtd` | Troubleshooting topics      |
| `dtd/technicalContent/dtd/glossentry.dtd` | Glossary entries                 |
| `dtd/technicalContent/dtd/map.dtd`       | Technical content maps            |
| `dtd/bookmap/dtd/bookmap.dtd`            | Bookmaps                          |
| `dtd/base/dtd/basetopic.dtd`             | Base topic elements               |
| `dtd/base/dtd/basemap.dtd`              | Base map elements                 |

---

## 2. Scope

### 2.1 Supported DITA Types

| Type | Root element | Body element | DTD public identifier |
| --------------- | ------------------ | ------------------- | ---------------------------------------- |
| topic           | `<topic>`          | `<body>`            | `-//OASIS//DTD DITA 1.3 Topic//EN`       |
| concept         | `<concept>`        | `<conbody>`         | `-//OASIS//DTD DITA 1.3 Concept//EN`     |
| task            | `<task>`           | `<taskbody>`        | `-//OASIS//DTD DITA 1.3 Task//EN`        |
| reference       | `<reference>`      | `<refbody>`         | `-//OASIS//DTD DITA 1.3 Reference//EN`   |
| troubleshooting | `<troubleshooting>`| `<troublebody>`     | `-//OASIS//DTD DITA 1.3 Troubleshooting//EN` |
| glossentry      | `<glossentry>`     | `<glossbody>`       | `-//OASIS//DTD DITA 1.3 Glossary Entry//EN` |
| map             | `<map>`            | *(n/a)*             | `-//OASIS//DTD DITA 1.3 Map//EN`         |
| bookmap         | `<bookmap>`        | *(n/a)*             | `-//OASIS//DTD DITA 1.3 BookMap//EN`     |

### 2.2 Skill Categories

| Category               | Description                       |
| ---------------------- | --------------------------------- |
| Validation             | XML + DITA 1.3 DTD compliance     |
| Generation             | Templates and scaffolding         |
| Refactoring            | Structure improvement             |
| Authoring Assistance   | Content suggestions               |
| Transformation Support | XSLT-aware hints                  |
| Conditional Processing | DITAVAL filtering assistance      |

---

## 3. Skill Definitions

Each skill is structured following the [agentskills.io specification](https://agentskills.io/specification):

```
<skill-name>/
├── SKILL.md          # Required: YAML frontmatter + instructions
├── scripts/          # Optional: executable validation/generation code
├── references/       # Optional: DTD excerpts, detailed rules
└── assets/           # Optional: XML templates
```

The `SKILL.md` frontmatter must follow these constraints:

| Field | Required | Constraints |
| ------------- | -------- | ------------------------------------------------------------------ |
| `name`        | Yes      | Max 64 chars. Lowercase letters, numbers, hyphens only. No leading/trailing/consecutive hyphens. Must match directory name. |
| `description` | Yes      | Max 1024 chars. Describes what the skill does and when to use it.  |
| `license`     | No       | License name or reference to bundled license file.                 |
| `compatibility` | No     | Max 500 chars. Environment requirements.                           |
| `metadata`    | No       | Arbitrary key-value mapping.                                       |
| `allowed-tools` | No     | Space-delimited list of pre-approved tools.                        |

**Example SKILL.md frontmatter:**
```yaml
---
name: validate-dita-topic
description: Validates a DITA topic against DITA 1.3 structural and semantic rules. Use this skill when you need to check a concept, task, reference, troubleshooting, or base topic for DTD compliance, missing required elements, or structural errors.
compatibility: Requires access to dtd/ directory for DTD resolution.
---
```

---

### 3.1 validate-dita-topic

**Skill name:** `validate-dita-topic`
**Skill directory:** [`validate-dita-topic/`](validate-dita-topic/SKILL.md)
**Script:** [`validate-dita-topic/scripts/validate_dita_topic.py`](validate-dita-topic/scripts/validate_dita_topic.py)

#### Description

Validates a DITA topic against DITA 1.3 structural and semantic rules derived from the DTDs in `dtd/technicalContent/dtd/`.

#### Script usage

```bash
# Validate a file (exit 0 = valid, 1 = invalid)
python validate-dita-topic/scripts/validate_dita_topic.py path/to/topic.dita

# Pipe XML directly
cat topic.dita | python validate-dita-topic/scripts/validate_dita_topic.py -

# Enforce a specific topic type
python validate-dita-topic/scripts/validate_dita_topic.py topic.dita concept
```

#### Input

```json
{
  "xml_content": "string",
  "topic_type": "topic | concept | task | reference | troubleshooting | glossentry"
}
```

#### Validation Rules (from DTDs)

**All topic types:**
* Root element must match `topic_type` and carry a non-empty `id` attribute
* `DOCTYPE` declaration must use the correct public identifier (see §2.1)
* Must contain `<title>` as the first child element
* `<shortdesc>` is strongly recommended (warned if absent)
* `<prolog>` is optional but must appear before the body element if present
* `<related-links>` is optional and must appear after the body element
* IDs must be unique within the document
* `conref` targets must resolve to an element of the same type
* `keyref` values must be defined in the applicable map context
* `@xml:lang` should be set on the root element for localization
* `@outputclass` and filtering attributes (`@audience`, `@platform`, `@product`, `@props`) are allowed on any element

**Concept (`concept.dtd`):**
* Body element: `<conbody>` (required)
* `conbody` content model: `(body.cnt)*, (section | example | conbodydiv)*`
  * `<conbodydiv>` may group sections and examples; it may not contain `<section>` siblings at the same level
* No `<steps>` or task-specific elements allowed

**Task (`task.dtd` — strict taskbody constraint applies):**
* Body element: `<taskbody>` (required)
* `taskbody` content model (strict, per `strictTaskbodyConstraint.mod`):
  `(prereq?, context?, (steps | steps-unordered | steps-informal)?, result?, tasktroubleshooting?, example*, postreq*)`
* `<steps>` requires at least one `<step>`; each `<step>` **must** contain `<cmd>` as its first child
* `<steps-unordered>` has the same structure as `<steps>` but renders as an unordered list
* `<steps-informal>` contains prose instead of structured `<step>` elements
* Optional step children (in order after `<cmd>`): `<info>`, `<substeps>`, `<tutorialinfo>`, `<stepxmp>`, `<choices>` or `<choicetable>`, `<stepresult>`, `<steptroubleshooting>`
* `<prereq>`, `<context>`, `<result>`, `<postreq>` each appear at most once

**Reference (`reference.dtd`):**
* Body element: `<refbody>` (required)
* `refbody` content model: `(data | example | foreign | refbodydiv | refsyn | properties | section | simpletable | table)*`
  * `<refsyn>` holds syntax diagrams or command signatures
  * `<properties>` holds a property table with `<property>` rows containing `<proptype>`, `<propvalue>`, `<propdesc>` cells
  * `<refbodydiv>` groups related `<section>`, `<refsyn>`, or `<properties>` elements

**Troubleshooting (`troubleshooting.dtd`):**
* Body element: `<troublebody>` (required)
* `troublebody` content model: `(condition?, troubleSolution+)?`
  * `<condition>` describes the observed problem
  * `<troubleSolution>` contains `(cause*, remedy*)`
    * `<cause>` explains the root cause
    * `<remedy>` provides the resolution, and may contain `<responsibleParty>`

**Glossentry (`glossentry.dtd`):**
* Root element: `<glossentry>`
* Required children: `<glossterm>`, `<glossdef>`
* Optional: `<prolog>`, `<glossBody>`

#### Output

```json
{
  "is_valid": true,
  "errors": [
    { "element": "string", "rule": "string", "message": "string", "line": 0 }
  ],
  "warnings": [
    { "element": "string", "rule": "string", "message": "string", "line": 0 }
  ]
}
```

---

### 3.2 validate-ditamap

**Skill name:** `validate-ditamap`

#### Description

Validates DITA map structure and topic references.

#### Validation Rules (from `dtd/base/dtd/map.mod`, `dtd/technicalContent/dtd/map.dtd`)

* Root must be `<map>` with a `title` child or `@title` attribute
* `<topicref>` content model: `(topicmeta?, (anchor | data | navref | topicref)*)`
* Each `<topicref>` must have `href` **or** `keyref` (not neither); `keys` is optional and defines a key
* `href` values must resolve to a `.dita` or `.ditamap` file; fragment references use `file.dita#topicid`
* Key definitions (`<keydef>`) must have a unique `keys` value within the map scope
* `<reltable>` defines relationship tables; `<relrow>` must contain exactly the same number of `<relcell>` elements as header `<relcolspec>` elements
* `@collection-type` on `<topicref>` accepts: `unordered`, `sequence`, `choice`, `family`
* Nesting depth: warn if exceeds 5 levels (best practice)
* Detect circular references across nested maps

---

### 3.3 validate-bookmap

**Skill name:** `validate-bookmap`

#### Description

Validates DITA bookmap structure.

#### Validation Rules (from `dtd/bookmap/dtd/bookmap.mod`)

* Root must be `<bookmap>` with correct DOCTYPE
* Content model (exact DTD order): `(title | booktitle)?, bookmeta?, frontmatter?, chapter*, part*, (appendices? | appendix*), backmatter?, reltable*`
  * `<booktitle>` requires `<mainbooktitle>` child; `<booktitlealt>` is optional
  * `<bookmeta>` may contain `<publisherinformation>`, `<bookid>`, `<bookchangehistory>`, `<bookrights>`
  * `<frontmatter>` and `<backmatter>` may contain `<toc>`, `<tablelist>`, `<figurelist>`, `<indexlist>`, `<notices>`, `<preface>`, `<amendments>`
  * `<part>` groups chapters; may contain `<chapter>` children
  * `<appendices>` wraps multiple `<appendix>` elements (alternative to bare `<appendix>*`)
* At least one `<chapter>` or `<part>` is required
* All `href` values in chapter/appendix must resolve

---

### 3.4 generate-dita-topic

**Skill name:** `generate-dita-topic`

#### Description

Generates valid DITA topic templates with correct DOCTYPE declarations.

#### Input

```json
{
  "topic_type": "topic | concept | task | reference | troubleshooting | glossentry",
  "title": "string",
  "id": "string"
}
```

#### Templates

##### Base Topic

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA 1.3 Topic//EN" "topic.dtd">
<topic id="{{id}}">
  <title>{{title}}</title>
  <shortdesc></shortdesc>
  <prolog>
    <metadata><keywords><indexterm>{{title}}</indexterm></keywords></metadata>
  </prolog>
  <body>
    <p></p>
  </body>
  <related-links/>
</topic>
```

##### Concept

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA 1.3 Concept//EN" "concept.dtd">
<concept id="{{id}}">
  <title>{{title}}</title>
  <shortdesc></shortdesc>
  <conbody>
    <p></p>
    <section>
      <title></title>
      <p></p>
    </section>
  </conbody>
</concept>
```

##### Task

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA 1.3 Task//EN" "task.dtd">
<task id="{{id}}">
  <title>{{title}}</title>
  <shortdesc></shortdesc>
  <taskbody>
    <prereq><p></p></prereq>
    <context><p></p></context>
    <steps>
      <step>
        <cmd></cmd>
        <info><p></p></info>
        <stepresult><p></p></stepresult>
      </step>
    </steps>
    <result><p></p></result>
    <postreq><p></p></postreq>
  </taskbody>
</task>
```

##### Reference

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA 1.3 Reference//EN" "reference.dtd">
<reference id="{{id}}">
  <title>{{title}}</title>
  <shortdesc></shortdesc>
  <refbody>
    <refsyn></refsyn>
    <section>
      <title></title>
      <p></p>
    </section>
    <properties>
      <prophead>
        <proptypehd>Property</proptypehd>
        <propvaluehd>Value</propvaluehd>
        <propdeschd>Description</propdeschd>
      </prophead>
      <property>
        <proptype></proptype>
        <propvalue></propvalue>
        <propdesc></propdesc>
      </property>
    </properties>
  </refbody>
</reference>
```

##### Troubleshooting

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE troubleshooting PUBLIC "-//OASIS//DTD DITA 1.3 Troubleshooting//EN" "troubleshooting.dtd">
<troubleshooting id="{{id}}">
  <title>{{title}}</title>
  <shortdesc></shortdesc>
  <troublebody>
    <condition><p></p></condition>
    <troubleSolution>
      <cause><p></p></cause>
      <remedy>
        <responsibleParty></responsibleParty>
        <steps>
          <step><cmd></cmd></step>
        </steps>
      </remedy>
    </troubleSolution>
  </troublebody>
</troubleshooting>
```

##### Glossary Entry

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE glossentry PUBLIC "-//OASIS//DTD DITA 1.3 Glossary Entry//EN" "glossentry.dtd">
<glossentry id="{{id}}">
  <glossterm>{{title}}</glossterm>
  <glossdef></glossdef>
</glossentry>
```

---

### 3.5 generate-ditamap

**Skill name:** `generate-ditamap`

#### Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA 1.3 Map//EN" "map.dtd">
<map id="{{id}}">
  <title>{{title}}</title>
  <topicref href="topic.dita" keys="topic-key"/>
  <reltable>
    <relcolspec/>
    <relcolspec/>
    <relrow>
      <relcell><topicref href="topic.dita"/></relcell>
      <relcell><topicref href="related.dita"/></relcell>
    </relrow>
  </reltable>
</map>
```

---

### 3.6 generate-bookmap

**Skill name:** `generate-bookmap`

#### Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE bookmap PUBLIC "-//OASIS//DTD DITA 1.3 BookMap//EN" "bookmap.dtd">
<bookmap id="{{id}}">
  <booktitle>
    <mainbooktitle>{{title}}</mainbooktitle>
    <booktitlealt></booktitlealt>
  </booktitle>
  <bookmeta>
    <publisherinformation>
      <organization><name></name></organization>
    </publisherinformation>
    <bookid><isbn></isbn></bookid>
  </bookmeta>
  <frontmatter>
    <toc/>
    <figurelist/>
    <tablelist/>
  </frontmatter>
  <chapter href="chapter1.dita">
    <topicref href="section1.dita"/>
  </chapter>
  <chapter href="chapter2.dita"/>
  <appendix href="appendixA.dita"/>
  <backmatter>
    <indexlist/>
  </backmatter>
</bookmap>
```

---

### 3.7 dita-best-practices

**Skill name:** `dita-best-practices`

#### Description

Analyzes DITA content for quality and maintainability issues.

#### Checks

* **Topic size**: warn if a topic body exceeds ~300 words or 50 block elements
* **Nesting depth**: warn if `<section>` or `<topicref>` nesting exceeds 3 levels
* **Reuse**: flag repeated text blocks that could be `conref` fragments
* **Key usage**: warn when `href` is used without a corresponding `keys` definition in the map
* **shortdesc**: error if `<shortdesc>` exceeds 50 words or contains block elements
* **Step count**: warn if a `<steps>` block has more than 10 `<step>` elements (consider splitting the task)
* **Duplicate IDs**: error if any `id` attribute value is reused within a document
* **`conref` chains**: error if a `conref` target itself contains a `conref` (chained conrefs are prohibited)
* **Empty elements**: warn on empty `<cmd>`, `<title>`, `<shortdesc>`, `<p>` elements

---

### 3.8 refactor-dita-content

**Skill name:** `refactor-dita-content`

#### Description

Improves structure and modularity of DITA content.

#### Capabilities

* Split large topics into focused sub-topics and generate a linking `<topicref>` hierarchy
* Normalize element order to match DTD content models
* Extract repeated paragraphs into a shared `conref` source file
* Convert inline `href` links to `keyref` references and generate key definitions
* Upgrade topic type (e.g., promote a generic `<topic>` to `<concept>` or `<task>` when the content fits)

---

### 3.9 xslt-dita-helper

**Skill name:** `xslt-dita-helper`

#### Description

Provides XSLT and XPath assistance for DITA transformations.

#### Features

* XPath suggestions using DITA element/attribute names from `dtd/` modules
* Template match pattern validation against DITA class attributes
* Transformation guidance for DITA-OT plugin development
* Specialization class attribute patterns (e.g., `- topic/topic concept/concept `)

#### DITA Class Attribute Patterns

| Specialization   | `@class` value |
| ---------------- | ------------------------------------------------------- |
| concept          | `- topic/topic concept/concept `                        |
| conbody          | `- topic/body concept/conbody `                         |
| task             | `- topic/topic task/task `                              |
| taskbody         | `- topic/body task/taskbody `                           |
| reference        | `- topic/topic reference/reference `                    |
| refbody          | `- topic/body reference/refbody `                       |
| troubleshooting  | `- topic/topic troubleshooting/troubleshooting `        |
| troublebody      | `- topic/body troubleshooting/troublebody `             |
| troubleSolution  | `- topic/bodydiv troubleshooting/troubleSolution `      |
| refsyn           | `- topic/section reference/refsyn `                     |
| properties       | `- topic/simpletable reference/properties `             |

#### Example: Matching by class attribute (preferred over element name)

```xslt
<!-- Preferred: works for specializations -->
<xsl:template match="*[contains(@class, ' task/taskbody ')]">
  <div class="taskbody"><xsl:apply-templates/></div>
</xsl:template>

<!-- Less robust: breaks with specializations -->
<xsl:template match="taskbody">
  <div class="taskbody"><xsl:apply-templates/></div>
</xsl:template>
```

---

### 3.10 ditaval-helper

**Skill name:** `ditaval-helper`

#### Description

Assists with DITAVAL conditional processing files for filtering and flagging DITA content. DITAVAL files are applied at build time (DITA-OT) to include, exclude, or visually flag content based on filtering attributes set on DITA elements.

#### Input

```json
{
  "conditions": [
    {
      "attribute": "audience | platform | product | props | rev | otherprops",
      "value": "string",
      "action": "include | exclude | flag | passthrough"
    }
  ],
  "style_conflict_action": "flag | use-conflict-marks"
}
```

#### DITAVAL Elements

| Element | Parent | Purpose |
|---|---|---|
| `<val>` | *(root)* | Container for all DITAVAL rules |
| `<prop>` | `<val>` | Filter or flag a conditional attribute+value |
| `<revprop>` | `<val>` | Flag or include/exclude content by revision mark (`@rev`) |
| `<style-conflict>` | `<val>` | Resolve visual conflicts when multiple flags apply to the same element |
| `<startflag>` | `<prop>`, `<revprop>` | Image or text inserted before flagged content |
| `<endflag>` | `<prop>`, `<revprop>` | Image or text inserted after flagged content |

#### Filtering Attributes on DITA Elements

These `@`-attributes on any DITA element are evaluated against DITAVAL `<prop>` rules:

| Attribute | Typical values | Notes |
|---|---|---|
| `@audience` | `developer`, `admin`, `end-user` | Who the content is for |
| `@platform` | `linux`, `windows`, `macos` | Target OS or environment |
| `@product` | `pro`, `enterprise`, `free` | Product edition |
| `@props` | any token | Generic filtering; supports grouped values `(a b)` |
| `@otherprops` | any token | Custom filtering (deprecated in DITA 2.0; prefer `@props`) |
| `@rev` | `1.2`, `sprint-4` | Revision mark; used with `<revprop>` |

#### Action Priority and Default Behaviour

When multiple `<prop>` rules could apply to the same element, the resolution order is:

1. **Explicit `exclude`** wins over any other action for the same attribute+value.
2. **Explicit `include`** or `flag` applies when no exclude rule matches.
3. If **no rule** matches a given attribute value, the default action is `include`.
4. If a `<prop att="audience">` (no `val`) is set to `exclude`, it excludes all values of `@audience` **not otherwise listed** with an explicit rule.

> Rule: A `<prop>` without `val` sets the **default action** for that attribute. A `<prop>` with `val` overrides that default for the specific value.

#### `<style-conflict>` resolution

When two `<prop action="flag">` rules apply to the same element (e.g., the element carries both `@audience="developer"` and `@platform="linux"`, both flagged with different colors), the `<style-conflict>` element defines the fallback:

```xml
<style-conflict foreground-conflict-color="#CC0000" background-conflict-color="#FFEEEE"/>
```

If `<style-conflict>` is absent, the processor uses its own default conflict styling.

#### DITAVAL Template — Full Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>

  <!-- ── Default actions ─────────────────────────────────── -->
  <!-- Exclude ALL audience values not explicitly listed below -->
  <prop action="exclude" att="audience"/>

  <!-- ── Per-value overrides ──────────────────────────────── -->
  <prop action="include" att="audience" val="developer"/>
  <prop action="include" att="audience" val="admin"/>

  <prop action="exclude" att="platform" val="windows"/>
  <prop action="include" att="platform" val="linux"/>
  <prop action="include" att="platform" val="macos"/>

  <!-- ── Flagging ─────────────────────────────────────────── -->
  <prop action="flag" att="product" val="enterprise">
    <startflag imageref="assets/flag-enterprise.png">
      <alt-text>Enterprise only</alt-text>
    </startflag>
    <endflag imageref="assets/flag-end.png">
      <alt-text>End enterprise</alt-text>
    </endflag>
  </prop>

  <!-- Text-only flag (no image) -->
  <prop action="flag" att="product" val="preview"
        color="#FF6600" backcolor="#FFF3E0"
        style="italic"/>

  <!-- ── Revision flagging ────────────────────────────────── -->
  <revprop action="flag" val="2.1"
           color="#0055CC" backcolor="#E8F0FF"
           style="underline">
    <startflag>
      <alt-text>New in 2.1</alt-text>
    </startflag>
  </revprop>

  <!-- ── Style conflict resolution ────────────────────────── -->
  <style-conflict
    foreground-conflict-color="#CC0000"
    background-conflict-color="#FFEEEE"/>

</val>
```

#### `<prop>` and `<revprop>` Visual Attributes

| Attribute | Applies to | Values |
|---|---|---|
| `color` | `<prop>`, `<revprop>` | CSS color name or hex (`#RRGGBB`) |
| `backcolor` | `<prop>`, `<revprop>` | CSS color name or hex |
| `style` | `<prop>`, `<revprop>` | `underline`, `double-underline`, `italics`, `overline`, `line-through` |
| `imageref` | `<startflag>`, `<endflag>` | Path to image file relative to DITAVAL location |

#### Validation Rules for DITAVAL Files

| Rule | Level |
|---|---|
| Root element must be `<val>` | Error |
| Each `<prop>` must have `att` and `action` | Error |
| `action` must be one of `include`, `exclude`, `flag`, `passthrough` | Error |
| `flag` action with no `<startflag>` or `<endflag>` and no visual attributes | Warning |
| Duplicate `att`+`val` combination across `<prop>` elements | Error |
| `<revprop>` must have `action`; `val` is optional | Error |
| `<style-conflict>` must appear at most once | Error |
| `imageref` path that does not exist relative to DITAVAL file | Warning |

#### Multiple DITAVAL Files

DITA-OT supports applying multiple DITAVAL files in a single build. Rules are merged:

* **Exclude always wins**: if any DITAVAL file excludes a value, it is excluded regardless of other files.
* **Flag merges**: flags from different files are combined; `<style-conflict>` from the first file in the list takes precedence.
* Specify multiple files in a DITA-OT build with: `--filter file1.ditaval --filter file2.ditaval`

#### Common Patterns

**Strip internal-only content for external delivery:**
```xml
<prop action="exclude" att="audience" val="internal"/>
```

**Produce a Windows-only build:**
```xml
<prop action="exclude" att="platform"/>
<prop action="include" att="platform" val="windows"/>
```

**Highlight draft content during review without excluding it:**
```xml
<revprop action="flag" val="draft" color="#FF0000" style="underline">
  <startflag><alt-text>[DRAFT]</alt-text></startflag>
</revprop>
```

---

## 4. Prompt Engineering

### System Prompt

```
You are a DITA XML expert based on DITA 1.3 specification.

You must:
- Enforce strict XML validity against the DTDs in dtd/
- Follow DITA specialization rules (use @class-based matching in XSLT)
- Suggest improvements aligned with dita-best-practices rules
- Promote reusable structured content using conref and keyref
- Always include a correct DOCTYPE declaration in generated XML
```

---

## 5. Validation Rules Summary

### All Topics

| Rule | Level |
| ---- | ----- |
| `id` attribute required on root element | Error |
| `<title>` required as first child | Error |
| `<shortdesc>` absent | Warning |
| `<shortdesc>` exceeds 50 words or contains block elements | Warning |
| Incorrect body element for topic type | Error |
| Duplicate `id` within document | Error |
| Unresolvable `conref` target | Error |
| Chained `conref` (target itself uses conref) | Error |
| Unresolvable `keyref` (no key definition in map) | Warning |
| Missing or incorrect DOCTYPE | Warning |

### Concept

| Rule | Level |
| ---- | ----- |
| `<conbody>` missing | Error |
| Task or reference elements inside `<conbody>` | Error |

### Task

| Rule | Level |
| ---- | ----- |
| `<taskbody>` missing | Error |
| `<steps>` contains no `<step>` | Error |
| `<step>` missing `<cmd>` | Error |
| `<prereq>`, `<context>`, `<result>`, `<postreq>` appear more than once | Error |
| More than 10 steps in a single `<steps>` block | Warning |

### Reference

| Rule | Level |
| ---- | ----- |
| `<refbody>` missing | Error |
| `<property>` row has no `<proptype>`, `<propvalue>`, or `<propdesc>` | Warning |

### Troubleshooting

| Rule | Level |
| ---- | ----- |
| `<troublebody>` missing | Error |
| `<troubleSolution>` absent | Error |
| `<condition>` appears more than once | Error |

### Map

| Rule | Level |
| ---- | ----- |
| `<topicref>` has neither `href` nor `keyref` | Error |
| Broken `href` reference | Error |
| Duplicate `keys` value | Error |
| Nesting depth > 5 | Warning |
| Circular reference in nested maps | Error |

### Bookmap

| Rule | Level |
| ---- | ----- |
| No `<chapter>` or `<part>` present | Error |
| DTD order violated (e.g., `<backmatter>` before `<chapter>`) | Error |
| `<booktitle>` missing `<mainbooktitle>` | Error |
| `<appendices>` and bare `<appendix>` used together | Error |

---

## 6. Execution Workflow

1. Input XML or generation request
2. Parse and well-formedness check
3. Detect topic type from root element
4. Apply type-specific DTD-derived validation rules
5. Return structured output with errors and warnings

---

## 7. Extensibility

Planned future skills:

* `schematron-generator` — generates Schematron rules from DITA best-practices checks
* `dita-specialization-assistant` — scaffolds new DITA specialization DTD/schema files
* `translation-readiness-checker` — validates `@xml:lang`, `@translate`, and `<term>` usage
* `content-reuse-analyzer` — finds reuse candidates and suggests `conref`/`keyref` refactoring

---

## 8. Design Principles

* DITA 1.3 compliance (validated against DTDs in `dtd/`)
* Modular content and single-sourcing
* Separation of content and structure
* Reusability-first: prefer `conref`/`keyref` over duplication
* agentskills.io-compatible skill packaging (SKILL.md + optional scripts/references/assets)

---

## 9. Example Workflow

1. Generate topic → `generate-dita-topic`
2. Validate topic → `validate-dita-topic`
3. Generate map → `generate-ditamap`
4. Validate map → `validate-ditamap`
5. Apply DITAVAL → `ditaval-helper`
6. Optimize → `dita-best-practices`
7. Transform → `xslt-dita-helper`

---

## 10. Summary

This specification enables:

* Automated DITA validation against DITA 1.3 DTDs
* Template generation with correct DOCTYPE declarations
* AI-assisted authoring for all standard DITA topic types
* agentskills.io-compatible skill packaging
* Scalable structured documentation workflows

---
