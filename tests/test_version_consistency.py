"""desearch_py.__version__ is the single source of truth for the version.

setup.py reads it at build time. pyproject.toml has to repeat it because
poetry-core cannot read a dynamic version, so these tests catch drift.
"""

import os
import re
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import desearch_py


REPO_ROOT = Path(__file__).resolve().parent.parent


def pyproject_version():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    section = re.search(r"^\[tool\.poetry\]\s*$(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    if not section:
        raise AssertionError("[tool.poetry] section not found in pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', section.group(1), re.MULTILINE)
    if not match:
        raise AssertionError("version not found in [tool.poetry] of pyproject.toml")
    return match.group(1)


def setup_py_version():
    # Run setup.py against a stub setuptools so the test needs neither
    # setuptools nor a build, and capture the keyword arguments it passes.
    captured = {}
    fake_setuptools = types.ModuleType("setuptools")
    fake_setuptools.setup = lambda **kwargs: captured.update(kwargs)
    fake_setuptools.find_packages = lambda *args, **kwargs: []

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        with mock.patch.dict(sys.modules, {"setuptools": fake_setuptools}):
            runpy.run_path(str(REPO_ROOT / "setup.py"), run_name="__main__")
    finally:
        os.chdir(cwd)
    return captured["version"]


class VersionConsistencyTests(unittest.TestCase):
    def test_pyproject_version_matches_package(self):
        self.assertEqual(pyproject_version(), desearch_py.__version__)

    def test_setup_py_version_matches_package(self):
        self.assertEqual(setup_py_version(), desearch_py.__version__)


if __name__ == "__main__":
    unittest.main()
