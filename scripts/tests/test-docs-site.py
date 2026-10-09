#!/usr/bin/env python3
"""Validate the built documentation, including project-subpath link resolution."""
import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://docs.example.test/adlc5/"
PAGES = ("index.html", "installation/index.html", "quickstart/index.html",
         "lifecycle/index.html", "intelligence/index.html", "reference/index.html")


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = set()
        self.links = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.links.append(attrs[attr])

    def handle_data(self, data):
        self.text.append(data)


class DocsSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SITE_DIR:
            cls.site = Path(SITE_DIR).resolve()
        else:
            cls.temp = tempfile.TemporaryDirectory(prefix="adlc5-docs-test-")
            cls.addClassCleanup(cls.temp.cleanup)
            cls.site = Path(cls.temp.name)
            subprocess.run(
                [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", str(cls.site)],
                cwd=ROOT, env={**os.environ, "DOCS_SITE_URL": BASE_URL}, check=True,
            )
        cls.documents = {
            path.relative_to(cls.site).as_posix(): Document(path.read_text(encoding="utf-8"))
            for path in cls.site.rglob("*.html")
        }

    def test_generated_links(self):
        self.assertTrue(self.documents, "No generated HTML")
        for source, doc in self.documents.items():
            for link in doc.links:
                target = urlsplit(urljoin(BASE_URL + source, link))
                if target.netloc != urlsplit(BASE_URL).netloc:
                    continue
                with self.subTest(source=source, link=link):
                    self.assertTrue(target.path.startswith("/adlc5/"), "Escapes project subpath")
                    relative = unquote(target.path.removeprefix("/adlc5/"))
                    if not relative or relative.endswith("/"):
                        relative += "index.html"
                    self.assertTrue((self.site / relative).is_file(), f"Missing {relative}")
                    if target.fragment and relative in self.documents:
                        self.assertIn(unquote(target.fragment), self.documents[relative].ids)

    def test_search(self):
        index = json.loads((self.site / "search/search_index.json").read_text())
        locations = {entry["location"].split("#")[0] for entry in index["docs"]}
        self.assertTrue({"", "installation/", "quickstart/", "lifecycle/", "intelligence/", "reference/"} <= locations)

    def test_site_content(self):
        for page in PAGES:
            self.assertIn(page, self.documents)
            html = (self.site / page).read_text()
            for label in ("Overview", "Installation", "Quickstart", "Lifecycle", "Intelligence", "Reference"):
                self.assertIn(label, html)
            self.assertIn('aria-label="Search"', html)
            self.assertIn("__drawer", html)
            self.assertIn("__palette", html)
            self.assertIn("assets/brand/icon.svg", html)
        quickstart = " ".join(self.documents["quickstart/index.html"].text)
        for command in ("init-workspace.sh", "init-feature.sh", "@adlc5 for my-feature"):
            self.assertIn(command, quickstart)
        lifecycle = " ".join(self.documents["lifecycle/index.html"].text)
        for term in ("Specify", "Plan", "Tasks", "Implement", "pr-ready", "deployment", "writable"):
            self.assertIn(term, lifecycle)
        intelligence = " ".join(self.documents["intelligence/index.html"].text)
        for term in ("fifth pillar", "repo-index", "repo-spec", "context packs", "SOUL", "measurements"):
            self.assertIn(term, intelligence)
        for artifact in ("manifest.json", "repo-index.json", "module-map.json", "symbols.json",
                         "dependency-graph.json", "test-map.json"):
            self.assertIn(artifact, intelligence)
        self.assertIn("--with-project-wiki", intelligence)
        installation = " ".join("".join(self.documents["installation/index.html"].text).split())
        for command in ("package-plugin.py", "claude --plugin-dir", "plugin-setup.sh"):
            self.assertIn(command, installation)
        self.assertNotIn("plugin-setup.py", installation)
        for page in PAGES:
            self.assertNotIn("dango85", (self.site / page).read_text())
        self.assertTrue((self.site / "assets/brand/icon.svg").is_file())

    def test_workflow_actions_are_sha_pinned(self):
        workflow = (ROOT / ".github/workflows/docs.yml").read_text()
        actions = re.findall(r"^\s*(?:-\s*)?uses:\s+([^\s]+)", workflow, re.MULTILINE)
        self.assertEqual(len(actions), 5)
        for action in actions:
            with self.subTest(action=action):
                self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", help="Check an existing MkDocs output instead of rebuilding")
    args, unittest_args = parser.parse_known_args()
    SITE_DIR = args.site_dir
    unittest.main(argv=[sys.argv[0], *unittest_args])
