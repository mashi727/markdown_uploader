from setuptools import setup, find_packages

setup(
    name="markdown_uploader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        # requirements.txtの内容をここに列記
        "notion-client",
        "pyyaml",
        "requests",
        # その他の依存関係
    ],
    entry_points={
        "console_scripts": [
            "md-upload=main:main",
            "markdown-uploader=main:main",
        ],
    },
    author="Your Name",
    description="MarkdownファイルをNotionにアップロードするツール",
    python_requires=">=3.7",
)