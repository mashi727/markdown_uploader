from setuptools import setup, find_packages
import os

# プロジェクトのルートディレクトリを取得
here = os.path.abspath(os.path.dirname(__file__))

# README.mdを読み込む
with open(os.path.join(here, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

# requirements.txtから依存関係を読み込む
with open(os.path.join(here, "requirements.txt"), "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="markdown-uploader",
    version="1.0.0",
    author="mashi727",
    author_email="",
    description="MarkdownファイルをNotionにアップロードするPythonツール",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mashi727/markdown_uploader",
    packages=find_packages(where="."),
    package_dir={"": "."},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.900",
            "pytest-cov>=2.12",
        ]
    },
    entry_points={
        "console_scripts": [
            "mdupload=cli:main",
            "markdown-upload=cli:main",
        ],
    },
    include_package_data=True,
    py_modules=["cli", "main"],
)