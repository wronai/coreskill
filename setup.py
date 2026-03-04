#!/usr/bin/env python3
"""
CoreSkill - Ewolucyjny system AI z ewoluującymi skillami
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="coreskill",
    version="1.0.0",
    author="CoreSkill Team",
    description="Ewolucyjny system AI z ewoluującymi skillami",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wronai/coreskill",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "litellm>=1.0.0",
        "nfo",
        # Add other dependencies as needed
    ],
    entry_points={
        "console_scripts": [
            "coreskill=cli:main_cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.txt"],
    },
)
