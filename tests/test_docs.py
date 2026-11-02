"""Consumer documentation structure checks; no network or compilation."""

from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

import yaml

from docs_config import DOCS, complete_examples, field, local_packages
from validate import ROOT, tracked_files


class DocumentationTests(unittest.TestCase):
    def test_device_catalog_coverage(self):
        catalog = (ROOT / "README.md").read_text()
        for path in tracked_files():
            if path.parent == Path("devices") and path.suffix == ".yaml":
                self.assertIn(f"]({path})", catalog, str(path))

    def test_local_links(self):
        for document in DOCS:
            text = (ROOT / document).read_text()
            text = re.sub(r"^```.*?^```\s*$", "", text, flags=re.MULTILINE | re.DOTALL)
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                target = (ROOT / document.parent / unquote(url.path)).resolve() if url.path else ROOT / document
                with self.subTest(document=str(document), link=link):
                    self.assertTrue(target.exists(), str(target))
                    if url.fragment and target.suffix == ".md":
                        headings = re.findall(r"^#+ (.+)$", target.read_text(), re.MULTILINE)
                        anchors = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                                   for heading in headings}
                        self.assertIn(unquote(url.fragment), anchors)

    def test_mirror_preserves_tags_and_vars(self):
        text = """```yaml
substitutions:
  name: example
packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    files:
      - path: device.yaml
        vars:
          entity: {type: light}
light:
  - id: !extend example_light
api:
  encryption:
    key: !secret api_key
```
```yaml
packages: []
```
"""
        examples = list(complete_examples(text))
        self.assertEqual(len(examples), 1)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "device.yaml").touch()
            node = local_packages(examples[0][1], root)
            entry = field(node, "packages").value[0]
            self.assertEqual(entry.tag, "!include")
            self.assertEqual(field(entry, "file").value, str(root / "device.yaml"))
            self.assertEqual(field(field(field(entry, "vars"), "entity"), "type").value, "light")
            serialized = yaml.serialize(node)
            self.assertIn("!extend", serialized)
            self.assertIn("!secret", serialized)
            self.assertNotIn("https://github.com", serialized)

    def test_local_mapping_include_and_named_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            node = yaml.compose("""
packages:
  appliance: !include
    file: devices/example.yaml
    vars:
      networking: {mode: ethernet}
""")
            node = local_packages(node, root)
            package = field(field(node, "packages"), "appliance")
            entry = field(package, "packages").value[0]
            self.assertEqual(entry.tag, "!include")
            self.assertEqual(field(entry, "file").value, str(root / "devices/example.yaml"))
            self.assertEqual(field(field(field(entry, "vars"), "networking"), "mode").value,
                             "ethernet")


if __name__ == "__main__":
    unittest.main()
