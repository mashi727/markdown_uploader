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
        
        # ページプロパティの設定
        page_props = self._build_page_properties(title, abstract)
        
        # ブロックの前処理（calloutブロックの互換性処理）
        processed_blocks = self._preprocess_blocks(blocks)
        
        try:
            new_page = self.client.pages.create(
                parent=parent,
                properties=page_props,
                children=processed_blocks
            )
            return new_page
        except APIResponseError as err:
            logging.error(f"Notion API エラー: {err}")
            
            # calloutブロックがサポートされていない場合のフォールバック
            if 'callout' in str(err):
                logging.info("calloutブロックをquoteブロックに変換して再試行します")
                fallback_blocks = self._convert_callouts_to_quotes(processed_blocks)
                try:
                    new_page = self.client.pages.create(
                        parent=parent,
                        properties=page_props,
                        children=fallback_blocks
                    )
                    return new_page
                except APIResponseError as err2:
                    logging.error(f"再試行も失敗しました: {err2}")
                    traceback.print_exc()
                    return None
            
            traceback.print_exc()
            return None
    
    def _build_page_properties(self, title: str, abstract: str) -> Dict[str, Any]:
        """ページプロパティを構築する"""
        page_props = {
            'Title': {'title': [{'type': 'text', 'text': {'content': title}}]},
        }
        
        if abstract:
            # 長い要約は切り詰める
            max_abstract_length = 1000
            if len(abstract) > max_abstract_length:
                abstract = abstract[:max_abstract_length-3] + '...'
            
            page_props['Memo'] = {'rich_text': [{'type': 'text', 'text': {'content': abstract}}]}
        
        return page_props
    
    def _preprocess_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ブロックの前処理を行う"""
        processed = []
        
        for block in blocks:
            # ブロックタイプのバリデーション
            if self._is_valid_block(block):
                processed.append(block)
            else:
                logging.warning(f"無効なブロックをスキップ: {block.get('type', 'unknown')}")
        
        return processed
    
    def _is_valid_block(self, block: Dict[str, Any]) -> bool:
        """ブロックが有効かどうかを確認する"""
        valid_types = [
            'paragraph', 'heading_1', 'heading_2', 'heading_3',
            'bulleted_list_item', 'numbered_list_item', 'to_do',
            'toggle', 'child_page', 'child_database', 'embed',
            'image', 'video', 'file', 'pdf', 'bookmark',
            'callout', 'quote', 'divider', 'table_of_contents',
            'column', 'column_list', 'link_preview', 'synced_block',
            'template', 'link_to_page', 'table', 'table_row',
            'code', 'equation'
        ]
        
        block_type = block.get('type')
        return block_type in valid_types
    
    def _convert_callouts_to_quotes(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """calloutブロックをquoteブロックに変換する（フォールバック用）"""
        converted = []
        
        for block in blocks:
            if block.get('type') == 'callout':
                # calloutをquoteに変換
                callout_data = block.get('callout', {})
                rich_text = callout_data.get('rich_text', [])
                
                # アイコンがある場合はテキストの先頭に追加
                icon = callout_data.get('icon', {})
                emoji = icon.get('emoji', '')
                
                if emoji and rich_text:
                    # 絵文字をテキストの先頭に追加
                    first_text = rich_text[0]
                    if first_text.get('type') == 'text':
                        original_content = first_text.get('text', {}).get('content', '')
                        first_text['text']['content'] = f"{emoji} {original_content}"
                
                converted.append({
                    'object': 'block',
                    'type': 'quote',
                    'quote': {'rich_text': rich_text}
                })
                
                logging.info(f"calloutブロックをquoteブロックに変換しました")
            else:
                converted.append(block)
        
        return converted
