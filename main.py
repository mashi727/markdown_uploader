#!/usr/bin/env python
"""
Notion Markdown Uploader - メインエントリーポイント
"""

import sys
import argparse
import logging
from pathlib import Path

from src.config import Config
from src.uploader import NotionUploader


def setup_logging(verbose: bool = False):
    """ログ設定を初期化する"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')
    
    # 外部ライブラリのログレベルを調整
    logging.getLogger('markdown_it').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def validate_file(file_path: str) -> Path:
    """ファイルパスの検証を行う"""
    md_path = Path(file_path)
    if not md_path.exists():
        logging.error(f"ファイルが存在しません: {file_path}")
        sys.exit(1)
    return md_path


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="MarkdownファイルをNotionにアップロードする"
    )
    parser.add_argument('file', help='.md file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='詳細ログ')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    try:
        # 設定の初期化
        config = Config()
        
        # ファイルパス検証
        md_path = validate_file(args.file)
        
        # アップローダーの初期化と実行
        uploader = NotionUploader(config)
        uploader.upload_file(md_path)
        
    except KeyboardInterrupt:
        logging.info("処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logging.error(f"予期しないエラーが発生しました: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
