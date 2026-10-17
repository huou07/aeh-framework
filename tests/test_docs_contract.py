"""Documentation discipline, enforced like code.

The Hub's own quality standard says a document with no status is current by
convention, so stale text is a bug. This test makes that structural instead of
aspirational, for the current document set only:

* every current document under `docs/` carries `Status:` and `Last reviewed:`;
* every current document is reachable from the `docs/README.md` index;
* every relative link and `#anchor` in those documents resolves.

Preserved history is exempt and listed below with its reason: those files keep
their original bytes and their links were relative to a retired runtime, so
"fixing" them would destroy the record. Archival material is for history, never
current authority.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
DOCS = HUB_ROOT / "docs"
INDEX = DOCS / "README.md"

# Preserved, not current authority: exact former policy or archived research.
PRESERVED = (
    "docs/writing-agents-md/legacy-",           # former hub guide and skill copies
    "docs/writing-agents-md/shared-AGENTS.md",  # exact former /srv policy, byte-preserved
    "docs/research/",                           # research archive with its own index
)

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")


def is_preserved(relative: str) -> bool:
    return relative.startswith(PRESERVED)


def relative_paths() -> list[str]:
    return sorted(str(path.relative_to(HUB_ROOT))
                  for path in DOCS.rglob("*.md"))


def anchor_of(heading: str) -> str:
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def anchors_of(path: Path) -> set[str]:
    anchors = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if match:
            anchors.add(anchor_of(match.group(1)))
    return anchors


class DocumentationContract(unittest.TestCase):
    def test_current_documents_declare_status_and_review_date(self):
        missing = []
        for relative in relative_paths():
            if is_preserved(relative):
                continue
            text = (HUB_ROOT / relative).read_text(encoding="utf-8")
            lines = text.splitlines()
            problems = []
            if not any(line.startswith("Status:") for line in lines):
                problems.append("no Status:")
            if not any(line.startswith("Last reviewed:") for line in lines):
                problems.append("no Last reviewed:")
            if problems:
                missing.append(f"{relative}: {', '.join(problems)}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_current_documents_are_indexed(self):
        index_text = INDEX.read_text(encoding="utf-8")
        unindexed = []
        for relative in relative_paths():
            if is_preserved(relative) or relative == "docs/README.md":
                continue
            name = relative[len("docs/"):]
            if name not in index_text:
                unindexed.append(relative)
        self.assertEqual(unindexed, [], "document not reachable from docs/README.md: "
                         + ", ".join(unindexed))

    def test_relative_links_and_anchors_resolve(self):
        broken = []
        for relative in relative_paths():
            if is_preserved(relative):
                continue
            document = HUB_ROOT / relative
            text = document.read_text(encoding="utf-8")
            for target in LINK_RE.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, _, anchor = target.partition("#")
                resolved = (document.parent / path_part).resolve() if path_part else document
                if path_part and not resolved.exists():
                    broken.append(f"{relative}: missing target {target}")
                    continue
                if anchor and resolved.suffix == ".md" and resolved.is_file():
                    if anchor not in anchors_of(resolved):
                        broken.append(f"{relative}: missing anchor {target}")
        self.assertEqual(broken, [], "\n".join(broken))

    def test_index_and_documents_link_the_standard(self):
        """The quality standard must be reachable from the index and AGENTS.md."""
        agents = (HUB_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("docs/quality-standard.md", agents)
        self.assertIn("](quality-standard.md)", INDEX.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
