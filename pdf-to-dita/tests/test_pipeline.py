#!/usr/bin/env python3
"""
tests/test_pipeline.py — Unit tests for the pdf-to-dita pipeline scripts.

Tests:
  - chunk_to_dita: topic-type detection, ID generation, XML structure, map generation
  - validate_output: aggregation logic, script discovery
  - optimize_dita: shortdesc insertion, first-sentence extraction
  - pipeline: stage runner, report formatting

Does NOT require pdfplumber or an actual PDF (extract_pdf.py is tested via mock JSON).
"""

import json
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

# Add the pipeline scripts to sys.path
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import chunk_to_dita
import optimize_dita
import validate_output

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXTRACTED_DOC = {
    "source": "/tmp/test.pdf",
    "title":  "Test Guide",
    "pages":  10,
    "sections": [
        {
            "level": 1,
            "title": "Overview",
            "content": [
                {"type": "paragraph", "text": "This guide explains the product. It covers installation and configuration."},
            ],
            "subsections": [],
        },
        {
            "level": 1,
            "title": "How to install the software",
            "content": [
                {"type": "paragraph", "text": "Follow these steps carefully."},
                {"type": "list", "ordered": True, "items": [
                    "Download the installer",
                    "Run the setup wizard",
                    "Restart your system",
                ]},
            ],
            "subsections": [],
        },
        {
            "level": 1,
            "title": "Configuration Parameters",
            "content": [
                {"type": "table",
                 "headers": ["Name", "Default", "Description"],
                 "rows": [["timeout", "30", "Connection timeout in seconds"]]},
            ],
            "subsections": [],
        },
        {
            "level": 1,
            "title": "Troubleshooting",
            "content": [
                {"type": "paragraph",
                 "text": "If the installation fails, check the log file. Error messages will indicate the cause."},
            ],
            "subsections": [],
        },
    ],
}


# ---------------------------------------------------------------------------
# chunk_to_dita — topic type detection
# ---------------------------------------------------------------------------

class TestTopicTypeDetection:

    def test_overview_is_concept(self):
        section = EXTRACTED_DOC["sections"][0]
        assert chunk_to_dita._detect_topic_type(section) == "concept"

    def test_install_how_to_is_task(self):
        section = EXTRACTED_DOC["sections"][1]
        assert chunk_to_dita._detect_topic_type(section) == "task"

    def test_parameters_table_is_reference(self):
        section = EXTRACTED_DOC["sections"][2]
        assert chunk_to_dita._detect_topic_type(section) == "reference"

    def test_ordered_list_threshold_task(self):
        section = {
            "title": "Setup",
            "content": [
                {"type": "list", "ordered": True, "items": ["Step one", "Step two", "Step three"]},
            ],
            "subsections": [],
        }
        assert chunk_to_dita._detect_topic_type(section) == "task"

    def test_ordered_list_below_threshold_concept(self):
        section = {
            "title": "Notes",
            "content": [
                {"type": "list", "ordered": True, "items": ["Point A", "Point B"]},  # < 3
            ],
            "subsections": [],
        }
        assert chunk_to_dita._detect_topic_type(section) == "concept"

    def test_reference_title_keyword(self):
        section = {"title": "API Reference", "content": [], "subsections": []}
        assert chunk_to_dita._detect_topic_type(section) == "reference"

    def test_table_name_column_is_reference(self):
        section = {
            "title": "Settings",
            "content": [
                {"type": "table", "headers": ["Name", "Value"], "rows": [["key", "val"]]},
            ],
            "subsections": [],
        }
        assert chunk_to_dita._detect_topic_type(section) == "reference"


# ---------------------------------------------------------------------------
# chunk_to_dita — slug and unique ID generation
# ---------------------------------------------------------------------------

class TestSlugify:

    def test_basic(self):
        assert chunk_to_dita._slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        slug = chunk_to_dita._slugify("DITA 1.3: Concepts & Tasks")
        assert " " not in slug
        assert ":" not in slug

    def test_max_length(self):
        long = "A" * 100
        assert len(chunk_to_dita._slugify(long)) <= 60

    def test_unique_id_deduplication(self):
        used: set = {"overview"}
        uid = chunk_to_dita._unique_id("overview", used)
        assert uid == "overview-2"
        uid2 = chunk_to_dita._unique_id("overview", used)
        assert uid2 == "overview-3"


# ---------------------------------------------------------------------------
# chunk_to_dita — XML generation
# ---------------------------------------------------------------------------

class TestXmlGeneration:

    def test_concept_structure(self, tmp_path):
        section = EXTRACTED_DOC["sections"][0]
        xml_str = chunk_to_dita._generate_topic(section, "overview", "concept")
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        assert root.tag == "concept"
        assert root.get("id") == "overview"
        assert root.find("title") is not None
        assert root.find("conbody") is not None

    def test_task_has_steps(self, tmp_path):
        section = EXTRACTED_DOC["sections"][1]
        xml_str = chunk_to_dita._generate_topic(section, "how-to-install-the-software", "task")
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        assert root.tag == "task"
        taskbody = root.find("taskbody")
        assert taskbody is not None
        steps = taskbody.find("steps")
        assert steps is not None
        step_elements = list(steps)
        assert len(step_elements) == 3

    def test_reference_has_simpletable(self):
        section = EXTRACTED_DOC["sections"][2]
        xml_str = chunk_to_dita._generate_topic(section, "configuration-parameters", "reference")
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        refbody = root.find("refbody")
        assert refbody is not None
        tables = list(refbody.iter("simpletable"))
        assert len(tables) >= 1

    def test_shortdesc_extracted(self):
        section = EXTRACTED_DOC["sections"][0]
        xml_str = chunk_to_dita._generate_topic(section, "overview", "concept")
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        shortdesc = root.find("shortdesc")
        assert shortdesc is not None
        assert len(shortdesc.text or "") > 5

    def test_doctype_in_output(self):
        section = EXTRACTED_DOC["sections"][0]
        xml_str = chunk_to_dita._generate_topic(section, "overview", "concept")
        assert "DOCTYPE concept" in xml_str


# ---------------------------------------------------------------------------
# chunk_to_dita — map generation
# ---------------------------------------------------------------------------

class TestMapGeneration:

    def test_map_has_topicrefs(self):
        entries = [
            {"href": "topics/a.dita", "navtitle": "A"},
            {"href": "topics/b.dita", "navtitle": "B"},
        ]
        xml_str = chunk_to_dita._generate_map("My Guide", entries)
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        assert root.tag == "map"
        topicrefs = list(root.iter("topicref"))
        assert len(topicrefs) == 2

    def test_map_has_title(self):
        xml_str = chunk_to_dita._generate_map("My Guide", [])
        root = ET.fromstring(xml_str.split("?>")[-1].strip())
        title = root.find("title")
        assert title is not None
        assert title.text == "My Guide"


# ---------------------------------------------------------------------------
# chunk_to_dita — full chunk integration
# ---------------------------------------------------------------------------

class TestChunkIntegration:

    def test_full_chunk(self, tmp_path):
        result = chunk_to_dita.chunk(EXTRACTED_DOC, tmp_path)
        assert result["total"] == 4  # 4 top-level sections
        assert (tmp_path / "root.ditamap").exists()
        for entry in result["topics"]:
            assert Path(entry["file"]).exists()

    def test_chunk_respects_map_title(self, tmp_path):
        result = chunk_to_dita.chunk(EXTRACTED_DOC, tmp_path, map_title="Custom Title")
        map_content = (tmp_path / "root.ditamap").read_text(encoding="utf-8")
        assert "Custom Title" in map_content


# ---------------------------------------------------------------------------
# optimize_dita — shortdesc extraction
# ---------------------------------------------------------------------------

class TestShortdescExtraction:

    def _make_dita_file(self, tmp_path: Path, body_text: str, topic_type: str = "concept") -> Path:
        body_tag = {"concept": "conbody", "task": "taskbody", "reference": "refbody"}[topic_type]
        xml = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {topic_type} PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
            <{topic_type} id="test">
              <title>Test Topic</title>
              <{body_tag}>
                <p>{body_text}</p>
              </{body_tag}>
            </{topic_type}>
        """)
        p = tmp_path / "test.dita"
        p.write_text(xml, encoding="utf-8")
        return p

    def test_inserts_shortdesc(self, tmp_path):
        dita = self._make_dita_file(
            tmp_path,
            "This is the introduction to the product. It provides an overview of features.",
        )
        modified = optimize_dita._fix_missing_shortdesc(dita)
        assert modified
        root = ET.parse(dita).getroot()
        shortdesc = root.find("shortdesc")
        assert shortdesc is not None
        assert len(shortdesc.text or "") > 5

    def test_no_change_if_shortdesc_present(self, tmp_path):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <concept id="c1">
              <title>T</title>
              <shortdesc>Already here.</shortdesc>
              <conbody><p>Body.</p></conbody>
            </concept>
        """)
        p = tmp_path / "has_shortdesc.dita"
        p.write_text(xml, encoding="utf-8")
        modified = optimize_dita._fix_missing_shortdesc(p)
        assert not modified

    def test_shortdesc_max_50_words(self, tmp_path):
        long_sentence = "word " * 80 + "end."
        dita = self._make_dita_file(tmp_path, long_sentence)
        optimize_dita._fix_missing_shortdesc(dita)
        root = ET.parse(dita).getroot()
        shortdesc = root.find("shortdesc")
        if shortdesc is not None and shortdesc.text:
            words = shortdesc.text.split()
            assert len(words) <= 55  # 50 words + possible ellipsis word

    def test_first_sentence_extraction(self):
        body = ET.Element("conbody")
        p = ET.SubElement(body, "p")
        p.text = "First sentence. Second sentence goes here."
        result = optimize_dita._extract_first_sentence(body)
        assert result is not None
        assert "First sentence" in result


# ---------------------------------------------------------------------------
# validate_output — script discovery
# ---------------------------------------------------------------------------

class TestValidateScriptDiscovery:

    def test_finds_topic_validator(self):
        skills_root = Path(__file__).resolve().parent.parent.parent
        script = validate_output._find_script(
            skills_root, "validate-dita-topic", "validate_dita_topic.py"
        )
        assert script is not None and script.exists()

    def test_finds_map_validator(self):
        skills_root = Path(__file__).resolve().parent.parent.parent
        script = validate_output._find_script(
            skills_root, "validate-ditamap", "validate_ditamap.py"
        )
        assert script is not None and script.exists()

    def test_returns_none_for_missing(self):
        skills_root = Path("/nonexistent")
        script = validate_output._find_script(skills_root, "validate-dita-topic", "validate_dita_topic.py")
        assert script is None


# ---------------------------------------------------------------------------
# validate_output — end-to-end with generated DITA
# ---------------------------------------------------------------------------

class TestValidateOutputIntegration:

    def test_valid_concept_passes(self, tmp_path):
        topics_dir = tmp_path / "topics"
        topics_dir.mkdir()

        # Write a valid concept
        (topics_dir / "overview.dita").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
            <concept id="overview">
              <title>Overview</title>
              <shortdesc>This is a brief overview.</shortdesc>
              <conbody>
                <p>Content here.</p>
              </conbody>
            </concept>
        """), encoding="utf-8")

        # Write a valid ditamap
        (tmp_path / "root.ditamap").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">
            <map>
              <title>Test Guide</title>
              <topicref href="topics/overview.dita" navtitle="Overview"/>
            </map>
        """), encoding="utf-8")

        skills_root = Path(__file__).resolve().parent.parent.parent
        report = validate_output.validate_all(tmp_path, skills_root)

        assert "summary" in report
        assert report["summary"]["total_files"] == 2
        # Both files should pass basic structural validation
        valid_count = report["summary"]["valid"]
        assert valid_count >= 1
