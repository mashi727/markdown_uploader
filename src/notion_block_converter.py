"""
MarkdownからNotionブロックへの変換機能モジュール
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Set

from markdown_it import MarkdownIt

from .config import Config
from .markdown_parser import MarkdownParser
from .image_uploader import ImageUploader


class NotionBlockConverter:
    """MarkdownからNotionブロックへの変換を担当するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.parser = MarkdownParser()
        self.image_uploader = ImageUploader(config)
        self.md = MarkdownIt('commonmark', {'linkify': True})
        
        # 処理済み画像の追跡
        self.processed_images: Set[str] = set()
    
    def convert_markdown_to_blocks(self, md_text: str, md_dir: Path) -> List[Dict[str, Any]]:
        """MarkdownテキストをNotionブロックに変換する"""
        # Obsidianスタイルのリンクを変換
        md_text = re.sub(r"\[\[(.+?)\]\]", r"\1", md_text)
        
        tokens = self.md.parse(md_text)
        blocks = []
        i = 0
        
        # インライン数式のパターン
        inline_math_pattern = r'\$\$(.*?)\$\$'
        
        while i < len(tokens):
            token = tokens[i]
            t = token.type
            
            if t == 'heading_open':
                i = self._process_heading(tokens, i, blocks)
            elif t in ('bullet_list_open', 'ordered_list_open'):
                i = self._process_list(tokens, i, blocks)
            elif t == 'paragraph_open':
                i = self._process_paragraph(tokens, i, blocks, md_dir, inline_math_pattern)
            elif t == 'inline':
                i = self._process_inline(tokens, i, blocks, md_dir)
            elif t == 'fence':
                i = self._process_code_block(tokens, i, blocks)
            elif t == 'blockquote_open':
                i = self._process_blockquote(tokens, i, blocks)
            elif t == 'hr':
                blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
                i += 1
            else:
                i += 1
        
        return self._validate_blocks(blocks)
    
    def _process_heading(self, tokens, i: int, blocks: List[Dict]) -> int:
        """見出しを処理する"""
        token = tokens[i]
        lvl = int(token.tag[1])
        content = tokens[i+1].content
        blk = f"heading_{lvl}" if lvl <= 3 else 'paragraph'
        blocks.append({
            'object': 'block',
            'type': blk,
            blk: {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
        })
        return i + 3
    
    def _process_list(self, tokens, i: int, blocks: List[Dict]) -> int:
        """リストを処理する"""
        list_type = 'numbered_list_item' if tokens[i].type == 'ordered_list_open' else 'bulleted_list_item'
        i += 1
        
        while tokens[i].type not in ('bullet_list_close', 'ordered_list_close'):
            if tokens[i].type == 'list_item_open':
                txt = tokens[i+2].content
                
                # リンクを見出し付きブックマークとして処理
                links_processed = self._process_markdown_links_as_labeled_bookmarks(txt, blocks)
                
                # リンクがない場合はリストアイテムとして追加
                if not links_processed:
                    blocks.append({
                        'object': 'block',
                        'type': list_type,
                        list_type: {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                    })
                
                i += 5
                continue
            i += 1
        
        return i + 1
    
    def _process_paragraph(self, tokens, i: int, blocks: List[Dict], md_dir: Path, inline_math_pattern: str) -> int:
        """段落を処理する"""
        txt = tokens[i+1].content.strip()
        if not txt:
            return i + 3
        
        # インライン数式をチェック
        math_matches = list(re.finditer(inline_math_pattern, txt))
        if math_matches:
            self._process_inline_math(txt, math_matches, blocks)
        else:
            # 画像を含むかどうかをチェック
            has_image = self._process_paragraph_images(tokens[i+1], md_dir, blocks)
            
            # 画像を含まない場合のみリンクとして処理
            if not has_image:
                self._process_paragraph_text(txt, blocks)
        
        return i + 3
    
    def _process_inline_math(self, txt: str, math_matches: List, blocks: List[Dict]):
        """インライン数式を処理する（テキストの順序を保持）"""
        last_end = 0
        
        # テキストと数式を文書の順序通りに処理
        for match in math_matches:
            start, end = match.span()
            
            # 数式の前のテキストを先に追加（空文字列は除く）
            if start > last_end:
                prefix_text = txt[last_end:start].strip()
                if prefix_text:  # 空文字列チェックを追加
                    blocks.append({
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': prefix_text}}]}
                    })
            
            # 数式ブロックを追加（テキストの後に配置）
            math_content = match.group(1)
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': math_content}
            })
            logging.info(f"インライン数式ブロックを追加しました: {math_content[:30]}...")
            
            # 次のループのために終了位置を更新
            last_end = end
        
        # 最後の数式後のテキストを追加（空文字列は除く）
        if last_end < len(txt):
            suffix_text = txt[last_end:].strip()
            if suffix_text:  # 空文字列チェックを追加
                blocks.append({
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': suffix_text}}]}
                })
    
    def _process_paragraph_images(self, token, md_dir: Path, blocks: List[Dict]) -> bool:
        """段落内の画像を処理する"""
        has_image = False
        for child in token.children or []:
            if child.type == 'image':
                has_image = True
                raw = child.attrs.get('src', '') if child.attrs else ''
                if raw not in self.processed_images:
                    self.processed_images.add(raw)
                    src = raw if raw.startswith(('http://', 'https://')) else self.image_uploader.get_image_url((md_dir/raw).resolve())
                    if src:
                        blocks.append({
                            'object': 'block',
                            'type': 'image',
                            'image': {'type': 'external', 'external': {'url': src}}
                        })
                        logging.info(f"画像ブロックを追加しました: src={src}")
        return has_image
    
    def _process_paragraph_text(self, txt: str, blocks: List[Dict]):
        """段落のテキストを処理する"""
        links_processed = self._process_markdown_links_as_labeled_bookmarks(txt, blocks)
        
        if not links_processed:
            text_parts = self.parser.split_long_text(txt, self.config.max_rich_text_length)
            for part in text_parts:
                blocks.append({
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': part}}]}
                })
    
    def _process_inline(self, tokens, i: int, blocks: List[Dict], md_dir: Path) -> int:
        """インライン要素を処理する"""
        token = tokens[i]
        handled = False
        
        # 画像の処理
        for child in token.children or []:
            if child.type == 'image':
                raw = child.attrs.get('src', '') if child.attrs else ''
                if raw not in self.processed_images:
                    self.processed_images.add(raw)
                    src = raw if raw.startswith(('http://', 'https://')) else self.image_uploader.get_image_url((md_dir/raw).resolve())
                    if src:
                        blocks.append({
                            'object': 'block',
                            'type': 'image',
                            'image': {'type': 'external', 'external': {'url': src}}
                        })
                        logging.info(f"画像ブロックを追加しました (inline): src={src}")
                        handled = True
        
        if not handled:
            txt = token.content.strip()
            if txt:
                self._process_paragraph_text(txt, blocks)
        
        return i + 1
    
    def _process_code_block(self, tokens, i: int, blocks: List[Dict]) -> int:
        """コードブロックを処理する"""
        token = tokens[i]
        code = token.content
        info_str = token.info.strip()
        
        # 言語情報を取得
        lang = self._determine_code_language(info_str)
        
        # 数式ブロックかどうかをチェック
        if lang in ('math', 'latex', 'tex') or self.parser.is_latex_code_block(lang, code):
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': code}
            })
            logging.info(f"数式ブロックを追加しました: {code[:30]}...")
            return i + 1
        
        # コードが長い場合は分割
        if len(code) > self.config.max_rich_text_length:
            self._process_long_code_block(code, lang, blocks)
        else:
            blocks.append({
                'object': 'block',
                'type': 'code',
                'code': {
                    'language': lang,
                    'rich_text': [{'type': 'text', 'text': {'content': code}}]
                }
            })
        
        return i + 1
    
    def _determine_code_language(self, info_str: str) -> str:
        """コードブロックの言語を決定する"""
        if not info_str:
            return 'plain text'
        
        raw_lang = info_str.split()[0].lower()
        
        language_mapping = {
            'sh': 'bash',
            'shell': 'bash',
            'js': 'javascript',
            'javascript': 'javascript',
            'math': 'math',
            'latex': 'latex',
            'tex': 'tex',
            'puml': 'plain text',
            'plantuml': 'plain text',
            'paul': 'plain text',
            'gnuplot': 'plain text'
        }
        
        return language_mapping.get(raw_lang, raw_lang)
    
    def _process_long_code_block(self, code: str, lang: str, blocks: List[Dict]):
        """長いコードブロックを分割して処理する"""
        logging.info(f"長いコードブロックを分割します (長さ: {len(code)}文字)")
        code_parts = self.parser.split_long_text(code, self.config.max_rich_text_length)
        
        for idx, part in enumerate(code_parts):
            blocks.append({
                'object': 'block',
                'type': 'code',
                'code': {
                    'language': lang,
                    'rich_text': [{'type': 'text', 'text': {'content': part}}]
                }
            })
            
            if idx < len(code_parts) - 1:
                blocks.append({
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{'type': 'text', 'text': {'content': f"(コードブロック分割 {idx+1}/{len(code_parts)})"}}]
                    }
                })
    
    def _process_blockquote(self, tokens, i: int, blocks: List[Dict]) -> int:
        """引用ブロックを処理する"""
        qt = tokens[i+2].content
        
        links_processed = self._process_markdown_links_as_labeled_bookmarks(qt, blocks)
        
        if not links_processed:
            text_parts = self.parser.split_long_text(qt, self.config.max_rich_text_length)
            for part in text_parts:
                blocks.append({
                    'object': 'block',
                    'type': 'quote',
                    'quote': {'rich_text': [{'type': 'text', 'text': {'content': part}}]}
                })
        
        return i + 5
    
    def _process_markdown_links_as_labeled_bookmarks(self, text: str, blocks: List[Dict]) -> bool:
        """Markdownのリンクを見出し付きブックマークブロックとして処理する"""
        links = self.parser.extract_markdown_links(text)
        
        if not links:
            return False
        
        for link in links:
            link_text = link['text']
            url = link['url']
            
            # まず見出しテキストを追加
            blocks.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': link_text}}]}
            })
            
            # 次にURLをブックマークまたは埋め込みとして追加
            if self.parser.is_video_link(url, self.config.video_domains):
                blocks.append({'object': 'block', 'type': 'embed', 'embed': {'url': url}})
            else:
                blocks.append({'object': 'block', 'type': 'bookmark', 'bookmark': {'url': url}})
        
        return True
    
    def _validate_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """ブロックの妥当性を確認する"""
        valid_blocks = []
        for idx, block in enumerate(blocks):
            block_type = block.get('type')
            if block_type and block.get(block_type) is not None:
                valid_blocks.append(block)
            else:
                logging.warning(f"無効なブロックをスキップします (index {idx}): {block}")
        
        return valid_blocks