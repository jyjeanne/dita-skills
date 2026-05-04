#!/usr/bin/env python3
"""
generate_dita_topic.py — DITA 1.3 topic template generator

Usage:
    python generate_dita_topic.py <type> <title> [id]

    type: topic | concept | task | reference | troubleshooting | glossentry
    id:   defaults to slugified title if omitted

Output: well-formed DITA 1.3 XML with correct DOCTYPE
"""

import re
import sys

# Public identifiers from dtd/technicalContent/dtd/ headers
_DOCTYPES: dict[str, tuple[str, str]] = {
    "topic":           ("-//OASIS//DTD DITA 1.3 Topic//EN",           "topic.dtd"),
    "concept":         ("-//OASIS//DTD DITA 1.3 Concept//EN",         "concept.dtd"),
    "task":            ("-//OASIS//DTD DITA 1.3 Task//EN",            "task.dtd"),
    "reference":       ("-//OASIS//DTD DITA 1.3 Reference//EN",       "reference.dtd"),
    "troubleshooting": ("-//OASIS//DTD DITA 1.3 Troubleshooting//EN", "troubleshooting.dtd"),
    "glossentry":      ("-//OASIS//DTD DITA 1.3 Glossary Entry//EN",  "glossentry.dtd"),
}


def slugify(text: str) -> str:
    """Convert a title to a valid XML ID."""
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    # XML IDs must start with a letter or underscore
    if slug and slug[0].isdigit():
        slug = "id-" + slug
    return slug or "generated-id"


def generate(topic_type: str, title: str, topic_id: str | None = None) -> str:
    if topic_type not in _DOCTYPES:
        raise ValueError(f"Unknown topic type '{topic_type}'. "
                         f"Valid types: {', '.join(_DOCTYPES)}")

    tid = topic_id or slugify(title)
    pub_id, sys_id = _DOCTYPES[topic_type]
    header = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
              f'<!DOCTYPE {topic_type} PUBLIC "{pub_id}" "{sys_id}">\n')

    builder = _BUILDERS.get(topic_type, _build_topic)
    return header + builder(title, tid)


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------

def _build_topic(title: str, tid: str) -> str:
    return f"""\
<topic id="{tid}">
  <title>{title}</title>
  <shortdesc>{{{{FILL}}}}</shortdesc>
  <prolog>
    <metadata>
      <keywords><indexterm>{title}</indexterm></keywords>
    </metadata>
  </prolog>
  <body>
    <p>{{{{FILL}}}}</p>
  </body>
  <related-links/>
</topic>"""


def _build_concept(title: str, tid: str) -> str:
    return f"""\
<concept id="{tid}">
  <title>{title}</title>
  <shortdesc>{{{{FILL}}}}</shortdesc>
  <conbody>
    <p>{{{{FILL}}}}</p>
    <section>
      <title>{{{{FILL}}}}</title>
      <p>{{{{FILL}}}}</p>
    </section>
  </conbody>
</concept>"""


def _build_task(title: str, tid: str) -> str:
    return f"""\
<task id="{tid}">
  <title>{title}</title>
  <shortdesc>{{{{FILL}}}}</shortdesc>
  <taskbody>
    <prereq>
      <p>{{{{FILL}}}}</p>
    </prereq>
    <context>
      <p>{{{{FILL}}}}</p>
    </context>
    <steps>
      <step>
        <cmd>{{{{FILL}}}}</cmd>
        <info><p>{{{{FILL}}}}</p></info>
        <stepresult><p>{{{{FILL}}}}</p></stepresult>
      </step>
    </steps>
    <result>
      <p>{{{{FILL}}}}</p>
    </result>
    <postreq>
      <p>{{{{FILL}}}}</p>
    </postreq>
  </taskbody>
</task>"""


def _build_reference(title: str, tid: str) -> str:
    return f"""\
<reference id="{tid}">
  <title>{title}</title>
  <shortdesc>{{{{FILL}}}}</shortdesc>
  <refbody>
    <refsyn>{{{{FILL}}}}</refsyn>
    <section>
      <title>{{{{FILL}}}}</title>
      <p>{{{{FILL}}}}</p>
    </section>
    <properties>
      <prophead>
        <proptypehd>Property</proptypehd>
        <propvaluehd>Value</propvaluehd>
        <propdeschd>Description</propdeschd>
      </prophead>
      <property>
        <proptype>{{{{FILL}}}}</proptype>
        <propvalue>{{{{FILL}}}}</propvalue>
        <propdesc>{{{{FILL}}}}</propdesc>
      </property>
    </properties>
  </refbody>
</reference>"""


def _build_troubleshooting(title: str, tid: str) -> str:
    return f"""\
<troubleshooting id="{tid}">
  <title>{title}</title>
  <shortdesc>{{{{FILL}}}}</shortdesc>
  <troublebody>
    <condition>
      <p>{{{{FILL}}}}</p>
    </condition>
    <troubleSolution>
      <cause>
        <p>{{{{FILL}}}}</p>
      </cause>
      <remedy>
        <responsibleParty>{{{{FILL}}}}</responsibleParty>
        <steps>
          <step>
            <cmd>{{{{FILL}}}}</cmd>
          </step>
        </steps>
      </remedy>
    </troubleSolution>
  </troublebody>
</troubleshooting>"""


def _build_glossentry(title: str, tid: str) -> str:
    return f"""\
<glossentry id="{tid}">
  <glossterm>{title}</glossterm>
  <glossdef>{{{{FILL}}}}</glossdef>
</glossentry>"""


_BUILDERS = {
    "topic":           _build_topic,
    "concept":         _build_concept,
    "task":            _build_task,
    "reference":       _build_reference,
    "troubleshooting": _build_troubleshooting,
    "glossentry":      _build_glossentry,
}


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: generate_dita_topic.py <type> <title> [id]", file=sys.stderr)
        print(f"Types: {', '.join(_DOCTYPES)}", file=sys.stderr)
        sys.exit(2)

    topic_type = sys.argv[1].lower()
    title = sys.argv[2]
    topic_id = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        print(generate(topic_type, title, topic_id))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
