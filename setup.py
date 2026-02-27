from setuptools import find_packages, setup

setup(
    name="desearch_py",
    version="1.1.0",
    description="A Python SDK for interacting with the Desearch API service.",
    author="Desearch",
    author_email="",
    license="MIT",
    package_data={"desearch_py": ["py.typed"]},
    packages=find_packages(),
    install_requires=["aiohttp", "typing-extensions", "pydantic"],
    python_requires=">=3.9",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
