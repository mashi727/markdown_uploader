#!/bin/bash
# Markdown Uploader インストールスクリプト

set -e  # エラーが発生したら停止

echo "=== Markdown Uploader インストール ==="

# 1. リポジトリのクローン
if [ ! -d "markdown_uploader" ]; then
    echo "リポジトリをクローンしています..."
    git clone https://github.com/mashi727/markdown_uploader.git
    cd markdown_uploader
else
    echo "既存のディレクトリを使用します..."
    cd markdown_uploader
    git pull origin main  # 最新版を取得
fi

# 2. setup.pyの作成
echo "setup.pyを作成しています..."
cat > setup.py << 'EOF'
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
EOF

# 3. cli.pyの作成
echo "cli.pyを作成しています..."
cat > cli.py << 'EOF'
#!/usr/bin/env python3
"""
Markdown Uploader CLI
コマンドラインインターフェースモジュール
"""
import argparse
import sys
import os
from pathlib import Path
import logging

# srcディレクトリをPythonパスに追加
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from config import get_config
    from uploader import MarkdownUploader
    from notion_client import NotionDatabaseClient
except ImportError:
    # 別の方法で試す
    sys.path.insert(0, str(current_dir))
    from src.config import get_config
    from src.uploader import MarkdownUploader
    from src.notion_client import NotionDatabaseClient


def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="MarkdownファイルをNotionにアップロードします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  mdupload README.md              # ファイルをアップロード
  mdupload -v document.md         # 詳細ログ付きでアップロード
  mdupload --config              # 設定を表示
        """
    )
    
    parser.add_argument(
        "markdown_file",
        nargs="?",
        help="アップロードするMarkdownファイル"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細ログを表示"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="現在の設定を表示"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    return parser.parse_args()


def show_config():
    """現在の設定を表示"""
    try:
        config = get_config()
        
        print("=== Markdown Uploader 設定 ===")
        print(f"\nNotion設定:")
        print(f"  データベースID: {'設定済み' if config.database_id else '未設定'}")
        print(f"  APIトークン: {'設定済み' if config.notion_token else '未設定'}")
        
        print(f"\n画像アップロード設定:")
        print(f"  FTPユーザー: {'設定済み' if os.getenv('FTP_USER') else '未設定'}")
        print(f"  ImgBB APIキー: {'設定済み' if os.getenv('IMGBB_API_KEY') else '未設定'}")
    except Exception as e:
        print(f"設定の読み込みに失敗しました: {e}")
        print("\n設定ファイルを作成してください:")
        print("  echo 'YOUR_DATABASE_ID' > ~/.token/notion/.terminal_memo_id")
        print("  echo 'YOUR_API_TOKEN' > ~/.token/notion/.terminal_memo_token")


def main():
    """メインエントリーポイント"""
    args = parse_arguments()
    
    # 設定表示モード
    if args.config:
        show_config()
        return 0
    
    # ファイルが指定されていない場合
    if not args.markdown_file:
        print("エラー: Markdownファイルを指定してください")
        print("使用方法: mdupload [オプション] <markdownファイル>")
        return 1
    
    # ファイルの存在確認
    markdown_path = Path(args.markdown_file)
    if not markdown_path.exists():
        print(f"エラー: ファイルが見つかりません: {markdown_path}")
        return 1
    
    try:
        # 既存のmain.pyの処理を呼び出す
        import main as original_main
        sys.argv = ["main.py"]
        if args.verbose:
            sys.argv.append("-v")
        sys.argv.append(str(markdown_path))
        
        return original_main.main()
        
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        return 130
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
EOF

# 4. 実行権限の付与
chmod +x cli.py

# 5. 仮想環境の作成
echo "仮想環境を作成しています..."
python3 -m venv venv
source venv/bin/activate

# 6. 依存関係のインストール
echo "依存関係をインストールしています..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. パッケージのインストール
echo "パッケージをインストールしています..."
pip install -e .

# 8. 設定ディレクトリの作成
mkdir -p ~/.config

# 9. 完了メッセージ
echo ""
echo "=== インストール完了 ==="
echo ""
echo "次のステップ:"
echo "1. Notion設定ファイルを作成してください:"
echo "   echo 'YOUR_DATABASE_ID' > ~/.token/notion/.terminal_memo_id"
echo "   echo 'YOUR_API_TOKEN' > ~/.token/notion/.terminal_memo_token"
echo ""
echo "2. 必要に応じて画像アップロード設定:"
echo "   export FTP_USER='your_username'"
echo "   export FTP_PASS='your_password'"
echo "   # または"
echo "   export IMGBB_API_KEY='your_api_key'"
echo ""
echo "3. 仮想環境を有効化してください:"
echo "   source venv/bin/activate"
echo ""
echo "4. コマンドを実行してください:"
echo "   mdupload your_file.md"
echo ""
echo "設定を確認するには:"
echo "   mdupload --config"
