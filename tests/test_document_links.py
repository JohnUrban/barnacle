import re
from pathlib import Path
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


class DocumentationLinkTests(unittest.TestCase):
    def test_repaired_local_markdown_links_resolve(self):
        paths = [
            ROOT / "model" / "v0.10.6.md",
            ROOT / "model" / "archive" / "v0.10.5.md",
            ROOT / "model" / "archive" / "v0.10.4.md",
            ROOT / "model" / "archive" / "v0.10.3.md",
            ROOT / "model" / "archive" / "v0.10.1.md",
            ROOT / "model" / "archive" / "v0.10.2.md",
            ROOT / "assets" / "observations" / "0-measuring-tape" / "README.md",
        ]
        missing = []
        for doc in paths:
            text = doc.read_text()
            for raw in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
                target = unquote(raw.strip("<>").split("#", 1)[0])
                if not target or "://" in target:
                    continue
                if not (doc.parent / target).resolve().exists():
                    missing.append(f"{doc.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
