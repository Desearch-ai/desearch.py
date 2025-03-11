from setuptools import setup, find_packages

setup(
    name="datura_py",
    version="0.0.1",
    description="A Python SDK for interacting with the Datura API service.",
    author="Leva",
    author_email="changelia@gmail.com",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
