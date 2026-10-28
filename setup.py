import re
from pathlib import Path

from setuptools import find_packages, setup


def read_version():
    # Parse the file instead of importing desearch_py: the package imports
    # aiohttp, which may not be installed at build time.
    init_py = Path(__file__).parent / "desearch_py" / "__init__.py"
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        init_py.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError(f"Unable to find __version__ in {init_py}")
    return match.group(1)


setup(
    name="desearch_py",
    version=read_version(),
    description="A Python SDK for interacting with the Desearch API service.",
    author="Desearch",
    author_email="",
    license="MIT",
    package_data={"desearch_py": ["py.typed"]},
    packages=find_packages(),
    install_requires=["aiohttp", "typing-extensions", "pydantic"],
    python_requires=">=3.10",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
