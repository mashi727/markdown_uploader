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
        # remote-claude形式の前処理
        md_text = self.parser.preprocess_remote_claude_format(md_text)
        
        # Obsidianスタイルのリンクを変換
        md_text = re.sub(r"\[\[(.+?)\]\]", r"\1", md_text)
        
        # コールアウトを処理
        md_text = self._process_callouts(md_text)
        
        # 直接的にブロック数式を検出して変換
        blocks = []
        self._process_text_with_block_math(md_text, md_dir, blocks)
        
        return self._validate_blocks(blocks)
    
    def _process_callouts(self, md_text: str) -> str:
        """Obsidianスタイルのコールアウトを処理する"""
        lines = md_text.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # コールアウトの開始を検出
            callout_match = re.match(r'^>\s*\[!([A-Z]+)\](?:\s+(.+?))?\s*$', line)
            
            if callout_match:
                callout_type = callout_match.group(1)
                title = callout_match.group(2) or callout_type.title()
                emoji = self.parser.CALLOUT_TYPES.get(callout_type, '📌')
                
                # コールアウトブロックを収集
                content_lines = []
                i += 1
                
                while i < len(lines) and lines[i].startswith('>'):
                    content_line = lines[i][1:].lstrip()
                    if content_line:  # 空行でない場合のみ追加
                        content_lines.append(content_line)
                    i += 1
                
                # Notion形式に変換（コールアウトボックス風）
                processed_lines.append('')  # 前に空行
                processed_lines.append(f'**{emoji} {title}**')
                processed_lines.append('')  # タイトル後に空行
                
                # 内容を囲み枠風に表現
                if content_lines:
                    # 引用ブロックとして内容を追加
                    for content_line in content_lines:
                        processed_lines.append(f'> {content_line}')
                
                processed_lines.append('')  # 後に空行
            else:
                processed_lines.append(line)
                i += 1
        
        return '\n'.join(processed_lines)
    
    def _process_text_with_block_math(self, md_text: str, md_dir: Path, blocks: List[Dict]):
        """テキストをブロック数式を考慮して処理する"""
        # ブロック数式のパターン（改行を含む）
        block_math_pattern = r'\$\$\s*(.*?)\s*\$\$'
        
        # 最初に全てのブロック数式を見つける
        block_math_matches = list(re.finditer(block_math_pattern, md_text, re.DOTALL))
        
        if not block_math_matches:
            # ブロック数式がない場合は通常の処理
            self._process_regular_markdown(md_text, md_dir, blocks)
            return
        
        last_end = 0
        
        for match in block_math_matches:
            start, end = match.span()
            
            # 数式の前のテキストを処理
            if start > last_end:
                before_text = md_text[last_end:start].strip()
                if before_text:
                    self._process_regular_markdown(before_text, md_dir, blocks)
            
            # ブロック数式を処理
            math_content = match.group(1).strip()
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': math_content}
            })
            logging.info(f"ブロック数式を追加しました: {math_content[:50]}...")
            
            last_end = end
        
        # 最後の数式の後のテキストを処理
        if last_end < len(md_text):
            after_text = md_text[last_end:].strip()
            if after_text:
                self._process_regular_markdown(after_text, md_dir, blocks)
    
    def _process_regular_markdown(self, md_text: str, md_dir: Path, blocks: List[Dict]):
        """通常のMarkdownテキストを処理する"""
        tokens = self.md.parse(md_text)
        i = 0
        
        # インライン数式のパターン（行内の$...$）
        inline_math_pattern = r'\$([^$\n]+)\$'
        
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
    
    def _process_heading(self, tokens, i: int, blocks: List[Dict]) -> int:
        """見出しを処理する（絵文字付きの見出しに対応）"""
        token = tokens[i]
        lvl = int(token.tag[1])
        content = tokens[i+1].content
        
        # 実行記録のセクションに特別な処理を適用
        if '📊 実行記録:' in content or '💬 プロンプト' in content or '✨ 結果' in content:
            # トグル可能なセクションとして処理
            blk = f"heading_{min(lvl, 3)}"
            blocks.append({
                'object': 'block',
                'type': blk,
                blk: {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}],
                    'is_toggleable': True  # Notionでトグル可能に
                }
            })
        else:
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
                
                # メタデータのリスト項目を特別に処理
                if txt.startswith('**') and ':' in txt:
                    # メタデータ形式を整形
                    blocks.append({
                        'object': 'block',
                        'type': list_type,
                        list_type: {
                            'rich_text': [{'type': 'text', 'text': {'content': txt}}],
                            'color': 'gray_background'  # メタデータを視覚的に区別
                        }
                    })
                else:
                    # 通常のリスト項目
                    links_processed = self._process_markdown_links_as_labeled_bookmarks(txt, blocks)
                    
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
        
        # ブロック数式のパターンをチェック（$$...$$）
        block_math_pattern = r'\$\$\s*(.*?)\s*\$\$'
        block_math_match = re.search(block_math_pattern, txt, re.DOTALL)
        
        if block_math_match:
            # ブロック数式が含まれている場合、適切に処理
            math_content = block_math_match.group(1).strip()
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': math_content}
            })
            logging.info(f"段落内のブロック数式を追加しました: {math_content[:30]}...")
            return i + 3
        
        # インライン数式をチェック（行内の$...$）
        inline_math_matches = list(re.finditer(inline_math_pattern, txt))
        if inline_math_matches:
            self._process_inline_math(txt, inline_math_matches, blocks)
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
        
        # 数式ブロックかどうかを優先的にチェック
        if self._is_math_block(lang, code):
            # 数式ブロックとして処理
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': code.strip()}  # 前後の空白を除去
            })
            logging.info(f"数式ブロックを追加しました: {code.strip()[:30]}...")
            return i + 1
        
        # 通常のコードブロックとして処理
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
            'tex': 'latex',  # texもlatexとして扱う
            'puml': 'plain text',
            'plantuml': 'plain text',
            'paul': 'plain text',
            'gnuplot': 'plain text',
            'python': 'python',
            'py': 'python',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
            'csharp': 'csharp',
            'cs': 'csharp',
            'ruby': 'ruby',
            'rb': 'ruby',
            'go': 'go',
            'rust': 'rust',
            'rs': 'rust',
            'html': 'html',
            'css': 'css',
            'xml': 'xml',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sql': 'sql',
            'r': 'r',
            'matlab': 'matlab',
            'swift': 'swift',
            'kotlin': 'kotlin',
            'kt': 'kotlin',
            'php': 'php',
            'perl': 'perl',
            'scala': 'scala',
            'haskell': 'haskell',
            'hs': 'haskell',
            'typescript': 'typescript',
            'ts': 'typescript',
            'markdown': 'markdown',
            'md': 'markdown'
        }
        
        return language_mapping.get(raw_lang, raw_lang)
    
    def _is_math_block(self, lang: str, content: str) -> bool:
        """ブロックが数式かどうかを判定する（より厳密な判定）"""
        # LaTeX文書の場合は数式ブロックとして扱わない
        content_stripped = content.strip()
        
        # LaTeX文書のパターンをチェック
        latex_document_indicators = [
            r'\\documentclass',
            r'\\usepackage',
            r'\\begin{document}',
            r'\\end{document}',
            r'\\title{',
            r'\\author{',
            r'\\maketitle',
            r'\\section{',
            r'\\subsection{',
            r'\\chapter{',
            r'\\tableofcontents',
            r'\\bibliography'
        ]
        
        # LaTeX文書の場合はコードブロックとして扱う
        if any(indicator in content_stripped for indicator in latex_document_indicators):
            return False
        
        # 明示的な数学言語指定（ただし、文書構造でない場合のみ）
        if lang == 'math':
            return True
        
        # 内容による判定（より厳密に）
        # LaTeX数式の典型的なパターンをチェック
        math_indicators = [
            # 数式環境
            r'\\begin{equation',
            r'\\begin{align',
            r'\\begin{gather',
            r'\\begin{matrix',
            r'\\begin{pmatrix',
            r'\\begin{bmatrix',
            r'\\begin{cases',
            # 数式コマンド
            r'\\frac{',
            r'\\sum',
            r'\\int',
            r'\\lim',
            r'\\prod',
            # 演算子
            r'\\nabla',
            r'\\partial',
            # ギリシャ文字（よく使われるもの）
            r'\\alpha',
            r'\\beta',
            r'\\gamma',
            r'\\delta',
            r'\\epsilon',
            r'\\theta',
            r'\\lambda',
            r'\\mu',
            r'\\pi',
            r'\\sigma',
            r'\\phi',
            r'\\omega',
            # 括弧
            r'\\left',
            r'\\right',
            # フォント
            r'\\mathbf',
            r'\\mathcal',
            r'\\mathrm',
            # 演算記号
            r'\\cdot',
            r'\\times',
            r'\\div',
            # 集合記号
            r'\\cap',
            r'\\cup',
            r'\\subset',
            r'\\in',
            # 論理記号
            r'\\forall',
            r'\\exists',
            r'\\Rightarrow'
        ]
        
        # 複数の数式パターンが含まれている場合により確実
        pattern_count = sum(1 for pattern in math_indicators if pattern in content_stripped)
        
        # 3つ以上の数式パターンがある場合（より厳密に）
        if pattern_count >= 3:
            return True
        
        # 明確な数式環境の場合
        math_env_patterns = [
            r'\\begin{equation',
            r'\\begin{align',
            r'\\begin{gather',
            r'\\begin{matrix',
            r'\\begin{pmatrix',
            r'\\begin{bmatrix'
        ]
        if any(pattern in content_stripped for pattern in math_env_patterns):
            return True
        
        return False
    
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
        """引用ブロックを処理する（コールアウト風の引用にも対応）"""
        qt = tokens[i+2].content
        
        # remote-claude形式の引用（プロンプト部分）を特別に処理
        if '入力プロンプト' in qt or 'プロンプト' in qt:
            # プロンプト用の特別な引用スタイル
            text_parts = self.parser.split_long_text(qt, self.config.max_rich_text_length)
            for part in text_parts:
                blocks.append({
                    'object': 'block',
                    'type': 'callout',
                    'callout': {
                        'rich_text': [{'type': 'text', 'text': {'content': part}}],
                        'icon': {'emoji': '💬'},
                        'color': 'blue_background'
                    }
                })
        else:
            # 通常の引用ブロック
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
