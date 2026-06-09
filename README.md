<div align="center">

# 📘 DITA Skills

**AI-powered skills for DITA 1.3 structured authoring**

Validate, generate, review, and improve DITA XML content using AI assistants — grounded in the official DITA 1.3 DTDs.

[![CI](https://github.com/jyjeanne/dita-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/dita-skills/actions/workflows/ci.yml)
<!-- ↑ Replace `your-org` with your GitHub username or organisation before publishing -->
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![agentskills.io](https://img.shields.io/badge/format-agentskills.io-purple)](https://agentskills.io/specification)

</div>

---

## What is this?

**DITA Skills** is a library of structured AI skills for working with [DITA 1.3](https://docs.oasis-open.org/dita/dita/v1.3/dita-v1.3-part0-overview.html) — the XML standard for technical documentation. Each skill is a self-contained directory with a `SKILL.md` declaration, an optional Python script, and reference files extracted directly from the official DITA 1.3 DTDs.

Load skills into your AI assistant to give it precise, DTD-grounded knowledge about DITA structure — making AI suggestions correct by construction rather than by approximation.

---

## 🛠 Skills at a Glance

| Skill | What it does | Script |
|-------|-------------|:------:|
| [`validate-dita-topic`](./validate-dita-topic/) | Validates topics (concept, task, reference, troubleshooting, glossentry …) against DTD rules | ✅ |
| [`validate-ditamap`](./validate-ditamap/) | Checks map structure, topicref href/keyref, key uniqueness, reltable consistency | ✅ |
| [`validate-bookmap`](./validate-bookmap/) | Enforces bookmap content-model order, chapter requirement, appendices wrapping | ✅ |
| [`review-dita-guide`](./review-dita-guide/) | Reviews an **entire guide** — traverses bookmap → child maps → topics, detects missing files, circular refs, duplicate IDs | ✅ |
| [`generate-dita-topic`](./generate-dita-topic/) | Generates a starter XML template for any DITA 1.3 topic type | ✅ |
| [`generate-ditamap`](./generate-ditamap/) | Generates a map with keydef, topicref, and reltable scaffolding | ✅ |
| [`generate-bookmap`](./generate-bookmap/) | Generates a bookmap with chapters, parts, appendices, and front/back matter | ✅ |
| [`generate-keyrefs`](./generate-keyrefs/) | Scans topics to auto-generate keydef entries and keyref suggestions — replaces hard-coded text/hrefs with reusable keys | ✅ |
| [`dita-best-practices`](./dita-best-practices/) | Audits topics for quality: shortdesc length, step count, duplicate paragraphs, conref chains | ✅ |
| [`ditaval-helper`](./ditaval-helper/) | Validates and generates DITAVAL conditional-processing filter files | ✅ |
| [`pdf-to-dita`](./pdf-to-dita/) | **Full pipeline** — converts a PDF into a validated DITA 1.3 guide (extract → chunk → validate → optimize → review) | ✅ |
| [`refactor-dita-content`](./refactor-dita-content/) | Guides AI-driven restructuring: topic splitting, conref extraction, modularisation | 📖 |
| [`xslt-dita-helper`](./xslt-dita-helper/) | XSLT 2.0 templates, `@class`-based matching, and DITA-OT plugin patterns | 📖 |

**Python library integration skills** (Python 3.10+, requires the Python DITA processing library)

| Skill | What it does | Script |
|-------|-------------|:------:|
| [`context-setup`](./context-setup/) | Wire `resolveMap()` → `KeyspaceManager` → `DitaContext` — covers init order, DITAVAL integration, and shared errors dict | 📖 |
| [`map-resolve`](./map-resolve/) | `resolvemap.resolveMap()` API — submap inlining, DITAVAL filtering during resolution, `getDirectFilesFromMap()` | 📖 |
| [`keyspace-debug`](./keyspace-debug/) | Debug key space construction — inspect key trees, trace missing keys, keyscope lookups, duplicate key analysis | 📖 |
| [`error-handling`](./error-handling/) | Error model — `ErrorRecord`, `SEVERITY`, `recordError()`, `reportErrors()`, `Logger`/`ConsoleLogger` | 📖 |
| [`visitor-extend`](./visitor-extend/) | Write custom `Visitor`/`Visitable` classes — dispatch mechanics, tree recursion, existing visitor reference | 📖 |

> **✅ Script** — executable Python 3.9+ (stdlib only, exits 0/1, JSON output)  
> **📖 Reference** — guidance-only skill with reference docs and assets

---

## 🚀 Quick Start

> **Prerequisites:** Python 3.9 or later. No third-party packages needed to run the scripts (stdlib only). `lxml` and `pytest` are needed only for the test suite.

### Step 1 — Get the repository

```bash
git clone https://github.com/your-org/dita-skills.git
cd dita-skills
```

### Step 2 — Install skills into your AI tool

Pick your tool and run one command. The installer copies every skill directory to the location your AI tool scans automatically.

**Claude Code**
```bash
# Personal install — available in all your projects
python scripts/install_skills.py --target claude --scope personal

# Or project-only (current repo)
python scripts/install_skills.py --target claude --scope project
```

**Mistral Vibe**
```bash
python scripts/install_skills.py --target vibe --scope personal
```

**GitHub Copilot CLI**
```bash
python scripts/install_skills.py --target copilot --scope personal
```

**All three tools at once**
```bash
python scripts/install_skills.py --target all --scope personal
```

Preview before committing (safe, no changes):
```bash
python scripts/install_skills.py --target all --scope personal --dry-run
```

> **Tip:** Run `--dry-run` first to preview exactly which directories will be created before making any changes.

### Step 3 — Invoke a skill in your AI assistant

Once installed, skills are available immediately. Your AI assistant picks the right skill automatically based on your request, or you can invoke one directly:

| Tool | Auto-detection | Direct invocation |
|------|---------------|------------------|
| **Claude Code** | Ask about DITA → Claude selects the skill | `/validate-dita-topic` |
| **Mistral Vibe** | Skill is injected from context | Describe your DITA task: `Validate my task topic for DTD errors` |
| **Copilot CLI** | Matches skill `description` to your prompt | `Use the /validate-dita-topic skill to…` |

---

## 🎯 Skill Use Cases

Each skill is designed for a concrete DITA authoring task. The examples below show the prompts and outputs you can expect once the skills are installed.

---

### `validate-dita-topic` — Validate a DITA topic

**Use case:** You have written a task topic and want to verify it is structurally correct before committing.

**Prompt (Claude Code / Copilot CLI):**
```
/validate-dita-topic
Check docs/install/install-plugin.dita for DTD compliance.
```

**What the skill does:**  
Runs `validate_dita_topic.py` against the file. Checks required elements (`<shortdesc>`, `<steps>`, `<cmd>`), forbidden cross-type elements, duplicate `@id`, malformed `@conref`, and `@keyref` syntax.

**Example output:**
```json
{
  "is_valid": false,
  "errors": [
    {
      "element": "taskbody",
      "rule": "step-required",
      "message": "<steps> must contain at least one <step>",
      "line": 0
    }
  ],
  "warnings": [
    {
      "element": "shortdesc",
      "rule": "shortdesc-length",
      "message": "shortdesc is 148 words; recommended maximum is 50",
      "line": 0
    }
  ]
}
```

**CLI equivalent:**
```bash
python validate-dita-topic/scripts/validate_dita_topic.py docs/install/install-plugin.dita
```

---

### `validate-ditamap` — Validate a DITA map

**Use case:** Your publication fails to build. You need to quickly identify broken `href` targets, missing keys, or reltable inconsistencies.

**Prompt:**
```
Use the /validate-ditamap skill to check my user-guide.ditamap for broken references.
```

**What the skill does:**  
Parses every `<topicref>`, checks that each `href` has either a valid file reference or a `keyref`, finds duplicate `@keys` across keydefs, and validates `<reltable>` column consistency.

**Example output:**
```json
{
  "is_valid": false,
  "errors": [
    {
      "element": "topicref",
      "rule": "href-or-keyref-required",
      "message": "<topicref> has neither href nor keyref",
      "line": 0
    },
    {
      "element": "keydef",
      "rule": "duplicate-key",
      "message": "Key 'product-name' is defined more than once",
      "line": 0
    }
  ],
  "warnings": []
}
```

**CLI equivalent:**
```bash
python validate-ditamap/scripts/validate_ditamap.py user-guide.ditamap
```

---

### `validate-bookmap` — Validate a bookmap

**Use case:** Before submitting a PDF build to DITA-OT, verify the bookmap structure is correct — chapters in the right order, front matter before body, appendices properly wrapped.

**Prompt:**
```
/validate-bookmap
Validate my-manual.bookmap and tell me if the structure is publish-ready.
```

**What the skill does:**  
Enforces bookmap content-model order (`<frontmatter>` → `<chapter>` → `<appendices>`), checks that at least one `<chapter>` is present, validates `<backmatter>` placement, and flags `<appendix>` elements that are not wrapped inside `<appendices>`.

**CLI equivalent:**
```bash
python validate-bookmap/scripts/validate_bookmap.py my-manual.bookmap
```

---

### `review-dita-guide` — Review an entire DITA guide

**Use case:** You are about to publish a large user manual. You want a single report covering every file in the guide — missing topics, circular map references, and duplicate topic IDs that would break links.

**Prompt:**
```
/review-dita-guide
Do a full pre-publication review of docs/user-guide.bookmap
```

**What the skill does:**  
Traverses the entire hierarchy (bookmap → child ditamaps → leaf topics), validates each file, then runs cross-guide checks for missing hrefs, circular `<mapref>` loops, and duplicate `@id` values across all topics.

**Example output (summary section):**
```json
{
  "summary": {
    "total_files": 42,
    "maps": 5,
    "topics": 36,
    "missing": 1,
    "unknown": 0,
    "errors": 3,
    "warnings": 7,
    "cross_guide_issues": 2
  },
  "cross_guide": [
    {
      "rule": "duplicate-guide-id",
      "message": "Topic @id='install-overview' appears in 2 files; IDs must be unique for reliable linking",
      "paths": ["install/overview.dita", "setup/overview.dita"]
    }
  ]
}
```

**CLI equivalent:**
```bash
python review-dita-guide/scripts/review_dita_guide.py docs/user-guide.bookmap
python review-dita-guide/scripts/review_dita_guide.py docs/user-guide.bookmap --format summary
```

---

### `generate-dita-topic` — Generate a topic template

**Use case:** You need to create a new task topic for a feature you are documenting. Instead of writing boilerplate XML from scratch, ask the AI to generate it.

**Prompt:**
```
/generate-dita-topic
Create a task topic called "Configure the proxy settings"
```

**What the skill does:**  
Generates a well-formed XML template with the correct structure for the requested topic type — including `<shortdesc>`, `<taskbody>`, `<prereq>`, `<steps>`, `<result>`, and `<postreq>` placeholders.

**Example output:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">
<task id="configure-proxy-settings">
  <title>Configure the proxy settings</title>
  <shortdesc>Configure your network proxy to enable connectivity.</shortdesc>
  <taskbody>
    <prereq>You must have administrator access.</prereq>
    <steps>
      <step><cmd>Open the Settings panel.</cmd></step>
      <step><cmd>Select <uicontrol>Network</uicontrol>.</cmd></step>
    </steps>
    <result>The proxy is now configured.</result>
  </taskbody>
</task>
```

**CLI equivalent:**
```bash
python generate-dita-topic/scripts/generate_dita_topic.py task "Configure the proxy settings"
# Other types: concept | reference | troubleshooting | glossentry
```

---

### `generate-ditamap` — Generate a DITA map

**Use case:** You are starting a new component documentation set and need a map file with keydef entries and topicrefs already in place.

**Prompt:**
```
Generate a ditamap for a 3-topic user guide covering "Overview", "Installation", and "Configuration"
```

**What the skill does:**  
Produces a complete `.ditamap` with a `<title>`, `<keydef>` block for variable keys, and `<topicref>` elements pointing to suggested file names. Validates that topic titles are provided and generates sensible `href` slugs automatically.

**CLI equivalent:**
```bash
python generate-ditamap/scripts/generate_ditamap.py "User Guide" \
  --topics "Overview" "Installation" "Configuration"
```

---

### `generate-bookmap` — Generate a bookmap

**Use case:** A new product manual needs a bookmap scaffolding with front matter, chapters, and appendices — ready for DITA-OT.

**Prompt:**
```
/generate-bookmap
Create a bookmap for "My Product Manual" with chapters:
Getting Started, Core Features, Advanced Configuration
and an appendix: Release Notes
```

**What the skill does:**  
Generates a complete DITA 1.3 bookmap scaffold with `<frontmatter>`, `<chapter>`, `<appendices>`, and `<backmatter>` elements in the correct content-model order. Titles are normalised to safe `@id` slugs automatically.

**CLI equivalent:**
```bash
python generate-bookmap/scripts/generate_bookmap.py "My Product Manual" \
  --chapters "Getting Started" "Core Features" "Advanced Configuration" \
  --appendix "Release Notes"
```

---

### `dita-best-practices` — Audit topic quality

**Use case:** Before peer review, run a quality check on a concept topic to catch shortdesc issues, overly long paragraphs, and conref chain warnings.

**Prompt:**
```
/dita-best-practices
Audit concepts/product-overview.dita and highlight any quality issues.
```

**What the skill does:**  
Checks `<shortdesc>` length (recommended ≤ 50 words), paragraph count per section, step count in tasks, duplicate content between sections, and `@conref` chain depth.

**Example output:**
```json
{
  "file_type": "concept",
  "findings": [
    {
      "rule": "shortdesc-length",
      "severity": "warning",
      "message": "shortdesc is 87 words; recommended maximum is 50"
    },
    {
      "rule": "section-paragraph-count",
      "severity": "info",
      "message": "Section 'Background' has 6 paragraphs; consider splitting"
    }
  ]
}
```

**CLI equivalent:**
```bash
python dita-best-practices/scripts/best_practices.py concepts/product-overview.dita
```

---

### `ditaval-helper` — Manage DITAVAL filters

**Use case 1 — Validate an existing filter:**  
Your DITAVAL file is causing unexpected output. Ask the skill to check it for structural errors.

**Prompt:**
```
/ditaval-helper
Validate filters/internal-only.ditaval
```

**Use case 2 — Generate a new filter:**  
You need a filter that excludes internal content and flags enterprise features with a colour.

**Prompt:**
```
Generate a DITAVAL filter that:
- Excludes audience=internal
- Flags product=enterprise in blue italic
```

**CLI equivalent:**
```bash
# Validate
python ditaval-helper/scripts/ditaval_helper.py validate filters/internal-only.ditaval

# Generate
python ditaval-helper/scripts/ditaval_helper.py generate \
  --exclude audience=internal \
  --flag product=enterprise:color=#0055CC:style=italic
```

---

### `refactor-dita-content` — Refactor and modularise

**Use case:** A legacy concept topic has grown to 1 500 words with 6 sections. Ask the AI to plan how to split it into reusable components.

**Prompt:**
```
Use the /refactor-dita-content skill to analyse docs/legacy/big-concept.dita
and propose a modular topic structure with conref candidates.
```

**What the skill does:**  
Provides a structured playbook for identifying split points, extracting repeated content into `<conref>` source topics, and updating `<topicref>` references in the parent map. No code execution — pure AI-guided refactoring.

---

### `xslt-dita-helper` — XSLT and DITA-OT patterns

**Use case:** You are writing a DITA-OT plugin and need an XSLT template that matches task steps using `@class`-based DITA patterns.

**Prompt:**
```
Use the /xslt-dita-helper skill to write an XSLT 2.0 template that
transforms <steps> into an HTML ordered list, using @class matching.
```

**What the skill does:**  
Provides `@class`-based match templates, DITA specialisation hierarchy rules, and DITA-OT plugin integration patterns. Includes 29 reference patterns covering all major topic types.

**Reference asset:**
```xslt
<!-- @class-based matching — correct DITA-OT pattern -->
<xsl:template match="*[contains(@class,' task/steps ')]">
  <ol class="steps">
    <xsl:apply-templates/>
  </ol>
</xsl:template>
```

---

## 🐍 Python Library Integration Skill Use Cases

These skills target developers working with a Python DITA processing library that provides map resolution, key space construction, and DITAVAL filtering for DITA processing pipelines.

---

### `context-setup` — Set up a processing pipeline

**Use case:** You are building a DITA processor and need to wire together `resolveMap()`, `KeyspaceManager`, and `DitaContext` correctly.

**Prompt:**
```
Use the /context-setup skill to help me initialise a DitaContext
for processing docs/root.ditamap with a DITAVAL filter.
```

**What the skill does:**  
Provides the canonical 5-step pipeline pattern, explains the required initialisation order, and documents every constructor parameter with common mistakes (separate error dicts, building KeyspaceManager from an unresolved map, missing DITA-OT).

---

### `map-resolve` — Use `resolveMap()` correctly

**Use case:** Your resolved map is missing content from submaps, or `resolveMap()` raises a `ParseError`.

**Prompt:**
```
/map-resolve
Why are my submap topicrefs missing from the resolved map?
```

**What the skill does:**  
Documents the `resolveMap()` API, explains how submaps become `<topicgroup base="submap">` wrappers, and lists the full error table with causes and fixes.

---

### `keyspace-debug` — Debug key resolution

**Use case:** `keySpace.getKeyDefinition("my-key")` returns `None` but you can see the `<keydef>` in the map source.

**Prompt:**
```
Use /keyspace-debug to help me trace why key 'product-name'
resolves to None in my keyscoped submap.
```

**What the skill does:**  
Explains how to print the full key space tree with `RenderTree`, look up keys by scope name, detect missing keyscope boundaries, and understand the pull-up/push-down construction phases.

---

### `error-handling` — Work with the errors dict

**Use case:** You want to filter errors by severity and produce a structured report after a pipeline run.

**Prompt:**
```
/error-handling
Show me how to collect errors across resolveMap() and KeyspaceManager
and report only WARN and above.
```

**What the skill does:**  
Documents `SEVERITY`, `ErrorRecord`, `recordError()`, `reportErrors()`, and provides ready-to-use filter patterns and a custom `Logger` subclass example.

---

### `visitor-extend` — Write a custom visitor

**Use case:** You want to collect all `href` values from the key space tree into a list.

**Prompt:**
```
Use /visitor-extend to write a Visitor that walks the KeySpace tree
and returns all key names that have href bindings.
```

**What the skill does:**  
Explains the `visit_<ClassName>` dispatch mechanism, tree recursion rules, and provides a complete `HrefCollector` example you can adapt immediately.

---

## 🤖 AI Tool Reference

### Installation paths

| Scope | Claude Code | Mistral Vibe | GitHub Copilot CLI |
|-------|-------------|--------------|-------------------|
| **Personal** (all projects) | `~/.claude/skills/<skill>/` | `~/.vibe/skills/<skill>/` | `~/.copilot/skills/<skill>/` |
| **Project** (current repo) | `.claude/skills/<skill>/` | `.vibe/skills/<skill>/` | `.github/skills/<skill>/` |

### Installer reference

```bash
# Install specific skills only
python scripts/install_skills.py --target claude --scope project \
  --skills validate-dita-topic,review-dita-guide,dita-best-practices

# Overwrite an existing installation
python scripts/install_skills.py --target all --scope personal --overwrite

# List available skills
python scripts/install_skills.py --list

# JSON output for automation
python scripts/install_skills.py --target copilot --scope project --dry-run --json
```

### GitHub Copilot CLI

```bash
# List loaded skills
/skills list

# Toggle skills interactively
/skills

# Reload after adding a skill mid-session
/skills reload
```

Invoke a skill explicitly in your prompt:
```
Use the /validate-dita-topic skill to check this topic.
Use the /review-dita-guide skill to audit the full guide before publishing.
```

### Claude Code

Skills in `.claude/skills/` are auto-discovered, including nested directories (monorepo-friendly). Invoke directly or use `@filename` syntax for progressive context loading:

```
# Direct slash-command
/validate-bookmap

# Load skill + reference file together for deep analysis
@validate-dita-topic/SKILL.md @validate-dita-topic/references/RULES.md
This task topic fails to publish. Explain the DTD violations.
```

### Mistral Vibe

Skills in `.vibe/skills/` (project) or `~/.vibe/skills/` (global) are auto-loaded:

```bash
# Start Vibe — skills activate automatically
vibe

# Custom skill path in ~/.vibe/config.toml
# [skills]
# paths = ["~/.vibe/skills/", "~/shared/dita-skills/"]
```

For API integration, pass a skill as the system prompt:

```python
import mistralai

with open("validate-dita-topic/SKILL.md") as f:
    skill = f.read()

client = mistralai.Mistral(api_key="...")
response = client.chat.complete(
    model="mistral-large-latest",
    messages=[
        {"role": "system", "content": skill},
        {"role": "user",   "content": f"Validate:\n\n{dita_xml}"},
    ],
)
```

---

## 🔄 `pdf-to-dita` — PDF to DITA conversion pipeline

Convert any legacy PDF manual into a validated DITA 1.3 guide with a single command.

The pipeline runs five stages automatically:

| Stage | Script | What it does |
|-------|--------|-------------|
| 1 — Extract | `extract_pdf.py` | PDF → structured JSON (headings, paragraphs, lists, tables) |
| 2 — Chunk | `chunk_to_dita.py` | JSON → DITA topics + root ditamap (concept/task/reference auto-detected) |
| 3 — Validate | `validate_output.py` | Runs `validate-dita-topic` + `validate-ditamap` on every file |
| 4 — Optimize | `optimize_dita.py` | Runs `dita-best-practices`, auto-inserts missing `<shortdesc>` |
| 5 — Review | `review_dita_guide.py` | Full cross-guide review — missing targets, duplicate IDs |

---

### Use case — Migrate a legacy API manual to structured DITA

**Situation:** You have a 120-page `api-reference.pdf` from a previous product version and need it in your DITA-based documentation system.

**Step 1 — Install and run:**

```bash
pip install pdfplumber

python pdf-to-dita/scripts/pipeline.py \
  legacy-api-reference.pdf \
  ./output/api-guide \
  --map-title "Product API Reference" \
  --format summary
```

**Pipeline output:**
```json
{
  "overall": "warnings",
  "stages": [
    { "stage": "extract",  "status": "ok",       "elapsed_s": 3.1 },
    { "stage": "chunk",    "status": "ok",       "elapsed_s": 0.4 },
    { "stage": "validate", "status": "warnings", "elapsed_s": 1.2 },
    { "stage": "optimize", "status": "ok",       "elapsed_s": 0.8 },
    { "stage": "review",   "status": "ok",       "elapsed_s": 0.6 }
  ],
  "validation": { "total_files": 18, "valid": 15, "invalid": 3, "total_errors": 5 }
}
```

**Generated file tree:**
```
output/api-guide/
├── root.ditamap              ← ready to open in Oxygen XML
├── extracted.json            ← Stage 1 raw structure (reusable)
├── topics/
│   ├── overview.dita         ← concept  (intro paragraphs)
│   ├── authentication.dita   ← task     (ordered steps detected)
│   ├── endpoints.dita        ← reference (parameter table detected)
│   ├── error-codes.dita      ← reference (Name/Code/Description table)
│   └── … 14 more topics
├── validation_report.json
├── optimization_report.json  ← shortdesc auto-inserted in 11 topics
└── review_report.json
```

**Step 2 — Fix issues then re-run stages 2–5 without re-reading the PDF:**

```bash
# Edit extracted.json if needed, then:
python pdf-to-dita/scripts/pipeline.py \
  --from-json ./output/api-guide/extracted.json \
  ./output/api-guide \
  --map-title "Product API Reference"
```

---

### With Claude Code

Install the skill once (see [Quick Start](#-quick-start)):

```bash
claude skill add pdf-to-dita ./pdf-to-dita/SKILL.md
```

Then use it in any conversation:

```
/pdf-to-dita

Convert legacy-api-reference.pdf into a DITA guide.
Output to ./output/api-guide. Map title: "Product API Reference".
After the pipeline runs, summarise which topics failed Stage 3 validation and why,
then suggest what to fix in each topic.
```

Claude Code runs all 5 stages, reads `validation_report.json` automatically, and gives you a prioritised fix list — no manual JSON inspection needed.

```
/pdf-to-dita

I already have extracted.json from a previous run at ./output/api-guide/extracted.json.
Re-run stages 2–5 only. Skip the review stage to save time.
```

---

### With GitHub Copilot CLI

Install the skill once (see [Quick Start](#-quick-start)):

```bash
gh copilot skill add pdf-to-dita ./pdf-to-dita/SKILL.md
```

Then invoke it in your terminal session:

```
gh copilot suggest "Use the pdf-to-dita skill to convert legacy-api-reference.pdf
into a DITA guide under ./output/api-guide with title 'Product API Reference'.
Report the number of topics generated and any validation errors."
```

Or interactively in `gh copilot chat`:

```
> run the pdf-to-dita pipeline on ./docs/manual.pdf → ./output/manual-dita
  then show me a summary of the review report
```

Copilot CLI will construct and execute the `pipeline.py` command, then parse and present the JSON reports inline in your terminal.

---

## 📁 Repo Structure

```
dita-skills/
├── specification.md            # Master spec — authoritative source for all skills
├── pyproject.toml              # Project config, test deps, coverage settings
├── dtd/                        # Official DITA 1.3 DTDs (base, technicalContent, bookmap …)
│
├── validate-dita-topic/        # ── Validation skills ──────────────────────────
│   ├── SKILL.md
│   ├── scripts/validate_dita_topic.py
│   └── references/RULES.md
├── validate-ditamap/
├── validate-bookmap/
│
├── review-dita-guide/          # ── Full-guide review ──────────────────────────
│   ├── SKILL.md
│   ├── scripts/review_dita_guide.py
│   └── references/RULES.md
│
├── generate-dita-topic/        # ── Generation skills ──────────────────────────
│   ├── SKILL.md
│   └── scripts/generate_dita_topic.py
├── generate-ditamap/
├── generate-bookmap/
│
├── dita-best-practices/        # ── Analysis skills ────────────────────────────
│   ├── SKILL.md
│   ├── scripts/best_practices.py
│   └── references/RULES.md
├── ditaval-helper/
│   ├── SKILL.md
│   ├── scripts/ditaval_helper.py
│   └── references/RULES.md
│
├── refactor-dita-content/      # ── Reference skills ───────────────────────────
│   ├── SKILL.md
│   └── references/REFERENCE.md
├── xslt-dita-helper/
│   ├── SKILL.md
│   ├── assets/xslt-patterns.xsl
│   ├── references/CLASS-ATTRIBUTES.md
│   └── references/DITA-OT-PLUGIN.md
│
├── context-setup/       # ── Python library integration skills ──────────────
│   └── SKILL.md
├── map-resolve/
│   └── SKILL.md
├── keyspace-debug/
│   └── SKILL.md
├── error-handling/
│   └── SKILL.md
├── visitor-extend/
│   └── SKILL.md
│
├── pdf-to-dita/                # ── PDF conversion pipeline ────────────────────
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── pipeline.py         # Main orchestrator (all 5 stages)
│   │   ├── extract_pdf.py      # Stage 1 — PDF text + structure extraction
│   │   ├── chunk_to_dita.py    # Stage 2 — DITA topic + map generation
│   │   ├── validate_output.py  # Stage 3 — Validation of generated files
│   │   └── optimize_dita.py    # Stage 4 — Best-practices auto-fix
│   ├── references/PIPELINE.md
│   └── tests/test_pipeline.py
│
├── scripts/                    # ── Automation ─────────────────────────────────
│   └── install_skills.py       # Install skills to Claude/Vibe/Copilot paths
│
└── tests/                      # ── Test suite ─────────────────────────────────
    ├── conftest.py
    ├── test_validate_dita_topic.py
    ├── test_validate_ditamap.py
    ├── test_validate_bookmap.py
    ├── test_generate_dita_topic.py
    ├── test_generate_maps.py
    ├── test_best_practices.py
    ├── test_ditaval_helper.py
    ├── test_xslt_patterns.py
    ├── test_review_dita_guide.py
    └── test_install_skills.py
```

---

## 🧪 Tests

**322 tests** across all scripts and the XSLT stylesheet. No test dependencies beyond `pytest`, `pytest-cov`, and `lxml`.

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# With coverage
pytest --cov --cov-report=term-missing
```

Tests run in CI on **Python 3.9, 3.10, 3.11, 3.12** on Ubuntu, macOS, and Windows.

---

## 🏗 Design Principles

| Principle | Detail |
|-----------|--------|
| **DTD-grounded** | Every validation rule cites the DITA 1.3 DTD element or attribute declaration |
| **Stdlib only** | Production scripts use only Python 3.9+ stdlib — no pip install in CI |
| **Exit-code contracts** | Scripts exit `0` (valid) or `1` (invalid/error) — composable in pipelines |
| **JSON output** | Machine-readable results: `{ "is_valid": bool, "errors": [...], "warnings": [...] }` |
| **agentskills.io compatible** | `SKILL.md` in every directory follows the open agent skill specification |

---

## 📚 DITA 1.3 Topic Types

| Topic type | Root element | Mandatory child | DTD |
|-----------|--------------|-----------------|-----|
| Concept | `<concept>` | `<conbody>` | `concept.dtd` |
| Task | `<task>` | `<taskbody>` → `<steps>` | `task.dtd` |
| Reference | `<reference>` | `<refbody>` | `reference.dtd` |
| Troubleshooting | `<troubleshooting>` | `<troublebody>` | `troubleshooting.dtd` |
| Glossary entry | `<glossentry>` | `<glossterm>` + `<glossdef>` | `glossentry.dtd` |

---

## Contributing

1. Each new skill lives in its own directory named exactly as the `name` field in `SKILL.md`
2. Follow the [agentskills.io specification](https://agentskills.io/specification) for `SKILL.md` format
3. Production scripts must remain stdlib-only; add test-only dependencies to `pyproject.toml [test]`
4. Add tests to `tests/` — the CI gate requires all tests to pass across the full Python matrix
5. Validation rules must cite the relevant DTD element/attribute declaration in `references/RULES.md`

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
<sub>Built for DITA 1.3 · Grounded in the OASIS DTDs · Works with any AI assistant</sub>
</div>
