#!/usr/bin/env python3

import os
from setuptools import setup, find_packages

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read LICENSE
with open("LICENSE", "r", encoding="utf-8") as fh:
    license_text = fh.read()

version = {}
with open(os.path.join("naver", "_version.py")) as fp:
    exec(fp.read(), version)

setup(
    name="naver",
    version=version["__version__"],
    description="Official implementation of NAVER.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ControlNet",
    author_email="smczx@hotmail.com",
    url="https://github.com/ControlNet/NAVER",
    project_urls={
        "Bug Tracker": "https://github.com/ControlNet/NAVER/issues",
        "Repository": "https://github.com/ControlNet/NAVER",
    },
    keywords=["deep learning", "pytorch", "AI"],
    packages=find_packages(include=["naver", "naver.*"]),
    python_requires=">=3.10",
    install_requires=[
        "torch",
        "transformers",
        "datasets",
        "tokenizers",
        "python-dotenv",
        "word2number",
        "rich",
        "openai",
        "scipy",
        "accelerate",
        "sentencepiece",
        "orjson",
        "bbox-visualizer",
        "pyyaml",
        "ollama",
        "problog",
        "timm",
        "tensorneko==0.3.21",
        "hydra_vl4ai==0.0.6",
    ],
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
) 