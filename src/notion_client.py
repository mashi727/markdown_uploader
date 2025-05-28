"""
Notionクライアント機能モジュール
"""

import logging
import traceback
from typing import List, Dict, Any, Optional

from notion_client import Client, APIResponseError

from .config import Config


class NotionClientWrapper:
    """Notion APIクライアントのラッパークラス"""
    
    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = Client(auth=config.notion_token)
        except Exception as e:
            logging.error(f"Notionクライアントの初期化に失敗しました: {e}")
            traceback.print_exc()
            raise
    
    def create_page(self, title: str, abstract: str, blocks: List[Dict[str, Any]], parent_id: Optional[str] = None) -> Optional[Dict]:
        """Notionページを作成する"""
        parent = {'database_id': self.config.database_id}
        if parent_id:
            # 子ページを作成する場合
            parent = {'page_id': parent_id}
        
        page_props = {
            'Title': {'title': [{'type': 'text', 'text': {'content': title}}]},
        }
        
        if abstract:
            page_props['Memo'] = {'rich_text': [{'type': 'text', 'text': {'content': abstract}}]}
        
        try:
            new_page = self.client.pages.create(
                parent=parent,
                properties=page_props,
                children=blocks
            )
            return new_page
        except APIResponseError as err:
            logging.error(f"Notion API エラー: {err}")
            traceback.print_exc()
            return None
