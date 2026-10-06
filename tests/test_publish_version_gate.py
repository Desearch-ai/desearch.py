import sys
import types
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish.yml"


def _workflow_function(name: str):
    text = WORKFLOW.read_text()
    marker = f"def {name}"
    start = text.index(marker)
    line_start = text.rfind("\n", 0, start) + 1
    next_def = text.index("\n        def ", start + 1)
    block = text[line_start:next_def]
    lines = []
    for line in block.splitlines():
        if line.startswith("        "):
            lines.append(line[8:])
        elif line == "":
            lines.append("")
        else:
            raise AssertionError(f"unexpected workflow indentation: {line!r}")
    namespace = {"sys": sys}
    exec("import sys\n" + "\n".join(lines), namespace)
    return namespace[name]


class PublishVersionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package_version = _workflow_function("package_version")
        cls.require_code_version = _workflow_function("require_code_version")

    def _with_version(self, value, present: bool):
        real = sys.modules.get("desearch_py")
        fake = types.ModuleType("desearch_py")
        if present:
            fake.__version__ = value
        sys.modules["desearch_py"] = fake
        try:
            return type(self).package_version()
        finally:
            if real is None:
                sys.modules.pop("desearch_py", None)
            else:
                sys.modules["desearch_py"] = real

    def test_missing_version_refuses_upload(self):
        found = self._with_version(None, present=False)
        with self.assertRaises(SystemExit) as caught:
            type(self).require_code_version(found, "1.3.1")
        self.assertIn("desearch_py.__version__ is missing", str(caught.exception))

    def test_empty_version_refuses_upload(self):
        found = self._with_version("  ", present=True)
        with self.assertRaises(SystemExit) as caught:
            type(self).require_code_version(found, "1.3.1")
        self.assertIn("desearch_py.__version__ is missing", str(caught.exception))

    def test_mismatched_version_refuses_upload(self):
        found = self._with_version("9.9.9", present=True)
        with self.assertRaises(SystemExit) as caught:
            type(self).require_code_version(found, "1.3.1")
        self.assertIn("!=", str(caught.exception))
        self.assertIn("9.9.9", str(caught.exception))

    def test_matching_version_passes(self):
        found = self._with_version("1.3.1", present=True)
        type(self).require_code_version(found, "1.3.1")


if __name__ == "__main__":
    unittest.main()
