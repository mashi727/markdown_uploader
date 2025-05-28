#!/usr/bin/env python
"""
Notion Markdown Uploader セットアップスクリプト
"""

from setuptools import setup, find_packages
from pathlib import Path

# README.mdを読み込む
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="notion-markdown-uploader",
    version="2.0.0",
    description="MarkdownファイルをNotionにアップロードするツール",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/notion-markdown-uploader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "markdown-it-py>=3.0.0",
        "notion-client>=2.0.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "notion-upload=main:main",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
)
