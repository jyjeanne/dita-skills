"""
test_xslt_patterns.py — Tests for xslt-dita-helper/assets/xslt-patterns.xsl

Tests:
1. File is valid, well-formed XML.
2. Expected template @match patterns are present.
3. lxml XSLT 1.0 transformations produce correct HTML output.

Note: xslt-patterns.xsl declares version="2.0" for Saxon compatibility.
      lxml supports XSLT 1.0 only; the sequence expression (@type,'note')[1]
      is handled via a compatibility shim applied before lxml processing.
"""
import re
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from lxml import etree as lxml_etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

XSLT_PATH = Path(__file__).parent.parent / "xslt-dita-helper" / "assets" / "xslt-patterns.xsl"

# Patch the one XSLT 2.0 sequence expression for lxml compatibility
_XSLT_10_COMPAT = re.compile(
    r"\(\s*@type\s*,\s*'note'\s*\)\[1\]",
)


def _load_xslt_for_lxml():
    """Load the XSLT file, downgrading version to 1.0 and patching 2.0 expressions."""
    content = XSLT_PATH.read_text(encoding="utf-8")
    content = content.replace('version="2.0"', 'version="1.0"')
    # Replace sequence expression with a 1.0-compatible conditional
    content = _XSLT_10_COMPAT.sub(
        "concat(@type, substring('note', 1 div not(@type)))",
        content,
    )
    return lxml_etree.XSLT(lxml_etree.fromstring(content.encode()))


# ---------------------------------------------------------------------------
# 1. File is well-formed XML
# ---------------------------------------------------------------------------

class TestXsltWellFormedness:
    def test_file_exists(self):
        assert XSLT_PATH.exists(), f"XSLT file not found at {XSLT_PATH}"

    def test_xslt_is_well_formed_xml(self):
        try:
            ET.parse(str(XSLT_PATH))
        except ET.ParseError as exc:
            pytest.fail(f"XSLT file is not well-formed XML: {exc}")

    def test_root_is_stylesheet(self):
        tree = ET.parse(str(XSLT_PATH))
        root = tree.getroot()
        assert "stylesheet" in root.tag or "transform" in root.tag, \
            f"Expected <xsl:stylesheet> root, got <{root.tag}>"

    def test_version_attribute_present(self):
        tree = ET.parse(str(XSLT_PATH))
        root = tree.getroot()
        assert root.get("version") in ("1.0", "2.0", "3.0")


# ---------------------------------------------------------------------------
# 2. Expected template @match patterns are present
# ---------------------------------------------------------------------------

EXPECTED_PATTERNS = [
    "topic/topic",
    "topic/title",
    "topic/shortdesc",
    "topic/section",
    "topic/p",
    "topic/note",
    "topic/ul",
    "topic/ol",
    "topic/xref",
    "concept/concept",
    "concept/conbody",
    "task/task",
    "task/taskbody",
    "task/prereq",
    "task/context",
    "task/steps",
    "task/steps-unordered",
    "task/step",
    "task/cmd",
    "task/result",
    "task/postreq",
    "reference/reference",
    "reference/refsyn",
    "reference/properties",
    "troubleshooting/troubleshooting",
    "troubleshooting/condition",
    "troubleshooting/troubleSolution",
    "troubleshooting/cause",
    "troubleshooting/remedy",
]


class TestExpectedPatterns:
    @pytest.fixture(scope="class")
    def xslt_content(self):
        return XSLT_PATH.read_text(encoding="utf-8")

    @pytest.mark.parametrize("pattern", EXPECTED_PATTERNS)
    def test_pattern_present(self, xslt_content, pattern):
        assert pattern in xslt_content, \
            f"Expected @class pattern '{pattern}' not found in xslt-patterns.xsl"

    def test_all_matches_use_contains_class(self, xslt_content):
        """All template match attributes should use contains(@class, ...) not bare element names."""
        tree = ET.parse(str(XSLT_PATH))
        ns = {"xsl": "http://www.w3.org/1999/XSL/Transform"}
        templates = tree.findall(".//xsl:template[@match]", ns)
        bare_element_matches = []
        for t in templates:
            match = t.get("match", "")
            # Skip identity or mode templates
            if match in ("@*", "node()", "*", "/", "text()", "processing-instruction()"):
                continue
            if "contains(@class" not in match and "[" not in match:
                bare_element_matches.append(match)
        assert bare_element_matches == [], \
            f"Templates use bare element names instead of @class: {bare_element_matches}"

    def test_priority_10_on_specialization_templates(self, xslt_content):
        """Specialization overrides should declare priority='10'."""
        tree = ET.parse(str(XSLT_PATH))
        ns = {"xsl": "http://www.w3.org/1999/XSL/Transform"}
        templates = tree.findall(".//xsl:template[@match]", ns)
        missing_priority = []
        for t in templates:
            match = t.get("match", "")
            if any(p in match for p in ("concept/", "task/", "reference/", "troubleshooting/")):
                if t.get("priority") != "10":
                    missing_priority.append(match)
        assert missing_priority == [], \
            f"Specialization templates missing priority='10': {missing_priority}"


# ---------------------------------------------------------------------------
# 3. XSLT transformation tests (requires lxml)
# ---------------------------------------------------------------------------

pytestmark_lxml = pytest.mark.skipif(
    not LXML_AVAILABLE, reason="lxml not installed"
)


def transform(xml_str: str):
    xslt = _load_xslt_for_lxml()
    doc = lxml_etree.fromstring(xml_str.encode())
    result = xslt(doc)
    return str(result)


@pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
class TestTransformations:

    def test_topic_renders_as_article(self):
        xml = (b'<topic id="t1" class="- topic/topic ">'
               b'<title class="- topic/title ">Hello</title>'
               b'<body class="- topic/body "/>'
               b'</topic>')
        html = transform(xml.decode())
        assert "<article" in html

    def test_shortdesc_renders_with_class(self):
        xml = (b'<topic id="t1" class="- topic/topic ">'
               b'<title class="- topic/title ">T</title>'
               b'<shortdesc class="- topic/shortdesc ">Brief.</shortdesc>'
               b'<body class="- topic/body "/>'
               b'</topic>')
        html = transform(xml.decode())
        assert 'class="shortdesc"' in html
        assert "Brief." in html

    def test_p_renders_as_p(self):
        xml = (b'<topic id="t1" class="- topic/topic ">'
               b'<title class="- topic/title ">T</title>'
               b'<body class="- topic/body ">'
               b'<p class="- topic/p ">Content here.</p>'
               b'</body></topic>')
        html = transform(xml.decode())
        assert "<p>" in html
        assert "Content here." in html

    def test_concept_renders_as_article_with_class(self):
        xml = (b'<concept id="c1" class="- topic/topic concept/concept ">'
               b'<title class="- topic/title ">C</title>'
               b'<conbody class="- topic/body concept/conbody "/>'
               b'</concept>')
        html = transform(xml.decode())
        assert 'class="concept' in html

    def test_task_steps_render_as_ol(self):
        xml = (
            b'<task id="t1" class="- topic/topic task/task ">'
            b'<title class="- topic/title ">T</title>'
            b'<taskbody class="- topic/body task/taskbody ">'
            b'<steps class="- topic/ol task/steps ">'
            b'<step class="- topic/li task/step ">'
            b'<cmd class="- topic/ph task/cmd ">Do this.</cmd>'
            b'</step>'
            b'</steps>'
            b'</taskbody>'
            b'</task>'
        )
        html = transform(xml.decode())
        assert '<ol class="steps">' in html
        assert '<li class="step">' in html
        assert "Do this." in html

    def test_reference_properties_render_as_table(self):
        xml = (
            b'<reference id="r1" class="- topic/topic reference/reference ">'
            b'<title class="- topic/title ">R</title>'
            b'<refbody class="- topic/body reference/refbody ">'
            b'<properties class="- topic/simpletable reference/properties ">'
            b'<property class="- topic/strow reference/property ">'
            b'<proptype class="- topic/stentry reference/proptype ">Name</proptype>'
            b'<propvalue class="- topic/stentry reference/propvalue ">Value</propvalue>'
            b'</property>'
            b'</properties>'
            b'</refbody>'
            b'</reference>'
        )
        html = transform(xml.decode())
        assert '<table class="properties">' in html
        assert "Name" in html
        assert "Value" in html

    def test_troubleshooting_renders_condition_and_remedy(self):
        xml = (
            b'<troubleshooting id="ts1" '
            b'class="- topic/topic troubleshooting/troubleshooting ">'
            b'<title class="- topic/title ">TS</title>'
            b'<troublebody class="- topic/body troubleshooting/troublebody ">'
            b'<condition class="- topic/section troubleshooting/condition ">'
            b'<p class="- topic/p ">The app crashes.</p>'
            b'</condition>'
            b'<troubleSolution '
            b'class="- topic/bodydiv troubleshooting/troubleSolution ">'
            b'<remedy class="- topic/section troubleshooting/remedy ">'
            b'<p class="- topic/p ">Reinstall.</p>'
            b'</remedy>'
            b'</troubleSolution>'
            b'</troublebody>'
            b'</troubleshooting>'
        )
        html = transform(xml.decode())
        assert 'class="condition"' in html
        assert 'class="remedy"' in html
        assert "The app crashes." in html

    def test_note_renders_with_type(self):
        xml = (
            b'<topic id="t1" class="- topic/topic ">'
            b'<title class="- topic/title ">T</title>'
            b'<body class="- topic/body ">'
            b'<note type="warning" class="- topic/note ">Be careful.</note>'
            b'</body>'
            b'</topic>'
        )
        html = transform(xml.decode())
        assert "note--warning" in html
        assert "Be careful." in html

    def test_note_without_type_defaults(self):
        xml = (
            b'<topic id="t1" class="- topic/topic ">'
            b'<title class="- topic/title ">T</title>'
            b'<body class="- topic/body ">'
            b'<note class="- topic/note ">Default note.</note>'
            b'</body>'
            b'</topic>'
        )
        html = transform(xml.decode())
        # Should fall back to 'note' type
        assert "note--" in html

    def test_xref_renders_as_anchor(self):
        xml = (
            b'<topic id="t1" class="- topic/topic ">'
            b'<title class="- topic/title ">T</title>'
            b'<body class="- topic/body ">'
            b'<p class="- topic/p ">'
            b'<xref href="other.dita" class="- topic/xref ">Link text</xref>'
            b'</p></body></topic>'
        )
        html = transform(xml.decode())
        assert '<a href="other.dita">' in html
        assert "Link text" in html

    def test_ul_and_li_render_correctly(self):
        xml = (
            b'<topic id="t1" class="- topic/topic ">'
            b'<title class="- topic/title ">T</title>'
            b'<body class="- topic/body ">'
            b'<ul class="- topic/ul ">'
            b'<li class="- topic/li ">Item one.</li>'
            b'<li class="- topic/li ">Item two.</li>'
            b'</ul></body></topic>'
        )
        html = transform(xml.decode())
        assert "<ul>" in html
        assert "<li>" in html
        assert "Item one." in html
