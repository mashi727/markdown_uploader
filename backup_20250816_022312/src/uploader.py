"""
Notionアップローダーメインモジュール
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from .config import Config
from .markdown_parser import MarkdownParser
from .notion_block_converter import NotionBlockConverter
from .notion_client import NotionClientWrapper


class NotionUploader:
    """Notionアップロード処理を統括するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.parser = MarkdownParser()
        self.converter = NotionBlockConverter(config)
        self.notion_client = NotionClientWrapper(config)
    
    def upload_file(self, md_path: Path):
        """Markdownファイルをアップロードする"""
        logging.info(f"アップロード開始: {md_path}")
        
        # ディレクトリ情報をログ出力
        self._log_directory_info(md_path)
        
        # フロントマターと本文を解析
        frontmatter, body = self.parser.parse_frontmatter_and_body(md_path)
        title = frontmatter.get('title') or md_path.stem
        abstract = frontmatter.get('abstract') or frontmatter.get('summary') or ''
        
        # MarkdownをNotionブロックに変換
        blocks = self.converter.convert_markdown_to_blocks(body, md_path.parent.resolve())
        
        # デバッグ情報を表示
        self._log_debug_info(blocks)
        
        # ページを作成
        self._create_pages(title, abstract, blocks)
    
    def _log_directory_info(self, md_path: Path):
        """ディレクトリ情報をログ出力する"""
        md_dir = md_path.parent.resolve()
        
        if md_dir.exists() and md_dir.is_dir():
            logging.info(f"Markdownディレクトリが存在します: {md_dir}")
            
            files = list(md_dir.glob('*'))
            if files:
                logging.info(f"ディレクトリ内のファイル数: {len(files)}")
                image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.svg']]
                if image_files:
                    logging.info(f"画像ファイル: {[f.name for f in image_files]}")
    
    def _log_debug_info(self, blocks: List[Dict[str, Any]]):
        """デバッグ情報を表示する"""
        if logging.getLogger().level <= logging.DEBUG:
            for i, block in enumerate(blocks):
                logging.debug(f"Block {i}: {block}")
    
    def _create_pages(self, title: str, abstract: str, blocks: List[Dict[str, Any]]):
        """ページを作成する（分割が必要な場合は複数ページ）"""
        total_blocks = len(blocks)
        
        if total_blocks > self.config.max_blocks_per_page:
            self._create_multiple_pages(title, abstract, blocks, total_blocks)
        else:
            self._create_single_page(title, abstract, blocks)
    
    def _create_single_page(self, title: str, abstract: str, blocks: List[Dict[str, Any]]):
        """単一ページを作成する"""
        new_page = self.notion_client.create_page(title, abstract, blocks)
        if new_page:
            logging.info(f"アップロード成功: {new_page['url']}")
        else:
            logging.error("ページの作成に失敗しました")
            raise RuntimeError("ページの作成に失敗しました")
    
    def _create_multiple_pages(self, title: str, abstract: str, blocks: List[Dict[str, Any]], total_blocks: int):
        """複数ページに分割して作成する"""
        logging.info(f"ブロック数が多いため複数ページに分割します: {total_blocks}ブロック")
        
        # メインページを作成
        main_blocks = blocks[:self.config.max_blocks_per_page]
        main_page = self.notion_client.create_page(title, abstract, main_blocks)
        
        if not main_page:
            logging.error("メインページの作成に失敗しました")
            raise RuntimeError("メインページの作成に失敗しました")
        
        main_page_id = main_page["id"]
        logging.info(f"メインページ作成成功: {main_page['url']}")
        
        # 残りのブロックを追加ページに分割
        remaining_blocks = blocks[self.config.max_blocks_per_page:]
        chunk_size = self.config.max_blocks_per_page
        chunk_num = 1
        
        while remaining_blocks:
            chunk = remaining_blocks[:chunk_size]
            remaining_blocks = remaining_blocks[chunk_size:]
            
            sub_title = f"{title} (続き {chunk_num})"
            sub_page = self.notion_client.create_page(sub_title, "", chunk, main_page_id)
            
            if sub_page:
                logging.info(f"追加ページ {chunk_num} 作成成功: {sub_page['url']}")
                chunk_num += 1
            else:
                logging.error(f"追加ページ {chunk_num} の作成に失敗しました")
                break
