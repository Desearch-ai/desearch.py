from setuptools import setup, find_packages

setup(
    name="datura_py",
    version="0.0.15",
    description="A Python SDK for interacting with the Datura API service.",
    author="Datura",
    author_email="",
    license="MIT",
    package_data={"datura_py": ["py.typed"]},
    packages=find_packages(),
    install_requires=["requests", "typing-extensions", "pydantic"],
    python_requires=">=3.6",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
