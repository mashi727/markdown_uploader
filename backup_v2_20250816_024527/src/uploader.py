"""
Notionアップローダーメインモジュール
"""

import logging
import re
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
        
        # ファイルタイプを判定
        file_type = self._detect_file_type(md_path)
        logging.info(f"検出されたファイルタイプ: {file_type}")
        
        # フロントマターと本文を解析
        frontmatter, body = self.parser.parse_frontmatter_and_body(md_path)
        
        # remote-claude形式の場合、タイトルを適切に設定
        if file_type == 'remote-claude':
            title = self._generate_remote_claude_title(frontmatter, body, md_path)
            abstract = self._generate_remote_claude_abstract(frontmatter, body)
        else:
            title = frontmatter.get('title') or md_path.stem
            abstract = frontmatter.get('abstract') or frontmatter.get('summary') or ''
        
        # MarkdownをNotionブロックに変換
        blocks = self.converter.convert_markdown_to_blocks(body, md_path.parent.resolve())
        
        # デバッグ情報を表示
        self._log_debug_info(blocks)
        
        # ページを作成（メタデータを含む）
        self._create_pages_with_metadata(title, abstract, blocks, frontmatter, file_type)
    
    def _detect_file_type(self, md_path: Path) -> str:
        """ファイルのタイプを判定する"""
        try:
            content = md_path.read_text(encoding='utf-8')
            
            # remote-claude形式のパターン
            if re.search(r'## 実行記録:\s*\d{4}-\d{2}-\d{2}', content):
                return 'remote-claude'
            
            # Obsidian形式のパターン
            if re.search(r'\[\[.*?\]\]', content) or re.search(r'>\s*\[!.*?\]', content):
                return 'obsidian'
            
            # 通常のMarkdown
            return 'standard'
            
        except Exception as e:
            logging.warning(f"ファイルタイプの判定に失敗: {e}")
            return 'standard'
    
    def _generate_remote_claude_title(self, frontmatter: Dict, body: str, md_path: Path) -> str:
        """remote-claude形式のファイルからタイトルを生成する"""
        # 実行時間があればそれを使用
        if 'execution_time' in frontmatter:
            exec_time = frontmatter['execution_time']
            
            # プロンプトの最初の部分を抽出
            prompt_match = re.search(r'>\s*(.{1,50})', body)
            if prompt_match:
                prompt_preview = prompt_match.group(1).strip()
                # 改行や特殊文字を除去
                prompt_preview = re.sub(r'[>\n\r\t]', ' ', prompt_preview).strip()
                prompt_preview = prompt_preview[:30] + '...' if len(prompt_preview) > 30 else prompt_preview
                return f"Claude実行記録 - {prompt_preview} ({exec_time})"
            
            return f"Claude実行記録 - {exec_time}"
        
        # フォールバック
        return frontmatter.get('title') or md_path.stem
    
    def _generate_remote_claude_abstract(self, frontmatter: Dict, body: str) -> str:
        """remote-claude形式のファイルから要約を生成する"""
        abstract_parts = []
        
        # メタデータから要約を構築
        if 'connection_host' in frontmatter:
            abstract_parts.append(f"接続先: {frontmatter['connection_host']}")
        
        if 'prompt_file' in frontmatter:
            abstract_parts.append(f"プロンプトファイル: {frontmatter['prompt_file']}")
        
        # プロンプトの最初の部分を抽出
        prompt_match = re.search(r'### 💬 プロンプト.*?\n>\s*(.{1,100})', body, re.DOTALL)
        if prompt_match:
            prompt_preview = prompt_match.group(1).strip()
            prompt_preview = re.sub(r'[>\n\r\t]', ' ', prompt_preview).strip()
            prompt_preview = prompt_preview[:80] + '...' if len(prompt_preview) > 80 else prompt_preview
            abstract_parts.append(f"プロンプト: {prompt_preview}")
        
        # 結果の最初の部分を抽出
        result_match = re.search(r'### ✨ 結果\s*\n(.{1,100})', body, re.DOTALL)
        if result_match:
            result_preview = result_match.group(1).strip()
            result_preview = re.sub(r'[#>\n\r\t]', ' ', result_preview).strip()
            result_preview = result_preview[:80] + '...' if len(result_preview) > 80 else result_preview
            abstract_parts.append(f"結果: {result_preview}")
        
        return ' | '.join(abstract_parts) if abstract_parts else ''
    
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
    
    def _create_pages_with_metadata(self, title: str, abstract: str, blocks: List[Dict[str, Any]], 
                                    frontmatter: Dict, file_type: str):
        """メタデータ付きでページを作成する"""
        # remote-claude形式の場合、メタデータをページ先頭に追加
        if file_type == 'remote-claude' and frontmatter:
            metadata_blocks = self._create_metadata_blocks(frontmatter)
            # メタデータブロックを先頭に追加
            blocks = metadata_blocks + blocks
        
        total_blocks = len(blocks)
        
        if total_blocks > self.config.max_blocks_per_page:
            self._create_multiple_pages(title, abstract, blocks, total_blocks)
        else:
            self._create_single_page(title, abstract, blocks)
    
    def _create_metadata_blocks(self, frontmatter: Dict) -> List[Dict[str, Any]]:
        """メタデータからNotionブロックを作成する"""
        blocks = []
        
        # メタデータセクションのヘッダー
        blocks.append({
            'object': 'block',
            'type': 'heading_3',
            'heading_3': {
                'rich_text': [{'type': 'text', 'text': {'content': '📋 メタデータ'}}],
                'is_toggleable': True
            }
        })
        
        # メタデータテーブルを作成
        if 'execution_time' in frontmatter:
            blocks.append({
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"⏰ 実行時刻: {frontmatter['execution_time']}"}}],
                    'color': 'gray_background'
                }
            })
        
        if 'connection_host' in frontmatter:
            blocks.append({
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"🖥️ 接続先: {frontmatter['connection_host']}"}}],
                    'color': 'gray_background'
                }
            })
        
        if 'prompt_file' in frontmatter:
            blocks.append({
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"📝 プロンプトファイル: {frontmatter['prompt_file']}"}}],
                    'color': 'gray_background'
                }
            })
        
        # 区切り線を追加
        blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
        
        return blocks
    
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
