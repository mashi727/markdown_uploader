"""
MarkdownからNotionブロックへの変換機能モジュール
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

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
        # remote-claude形式かどうかを判定
        is_remote_claude = self._is_remote_claude_format(md_text)
        
        if is_remote_claude:
            # remote-claude形式の特別な処理
            logging.info("remote-claude形式を検出しました")
            return self._convert_remote_claude_format(md_text, md_dir)
        else:
            # 通常のMarkdown処理
            logging.info("通常のMarkdown形式として処理します")
            # Obsidianスタイルのリンクを変換
            md_text = re.sub(r"\[\[(.+?)\]\]", r"\1", md_text)
            
            # コールアウトを処理
            md_text = self._process_callouts(md_text)
            
            # 直接的にブロック数式を検出して変換
            blocks = []
            self._process_text_with_block_math(md_text, md_dir, blocks)
            
            return self._validate_blocks(blocks)
    
    def _is_remote_claude_format(self, md_text: str) -> bool:
        """remote-claude形式かどうかを判定"""
        # より厳密な判定パターン
        patterns = [
            r'## 実行記録:\s*\d{4}-\d{2}-\d{2}',
            r'\*\*接続先:\*\*',
            r'\*\*プロンプトファイル:\*\*',
            r'### プロンプト',
            r'### 結果'
        ]
        
        # 少なくとも3つ以上のパターンがマッチすればremote-claude形式と判定
        matches = sum(1 for pattern in patterns if re.search(pattern, md_text))
        return matches >= 3
    
    def _convert_remote_claude_format(self, md_text: str, md_dir: Path) -> List[Dict[str, Any]]:
        """remote-claude形式を特別に処理"""
        blocks = []
        
        # セクションを解析
        sections = self._parse_remote_claude_sections(md_text)
        
        logging.info(f"解析されたセクション: {sections.keys()}")
        
        # 実行記録ヘッダー
        if sections.get('execution_header'):
            blocks.append({
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"📊 {sections['execution_header']}"}}]
                }
            })
        
        # メタデータ
        if sections.get('metadata'):
            for meta_line in sections['metadata']:
                blocks.append({
                    'object': 'block',
                    'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [{'type': 'text', 'text': {'content': meta_line}}],
                        'color': 'gray_background'
                    }
                })
        
        # プロンプトセクション
        if sections.get('prompt_title'):
            blocks.append({
                'object': 'block',
                'type': 'heading_3',
                'heading_3': {
                    'rich_text': [{'type': 'text', 'text': {'content': '💬 プロンプト'}}]
                }
            })
            
            # プロンプト内容を引用ブロックとして追加
            if sections.get('prompt_content'):
                prompt_text = sections['prompt_content'].strip()
                logging.info(f"プロンプト内容: {prompt_text[:100]}...")
                
                # プロンプトをコールアウトとして表示
                blocks.append({
                    'object': 'block',
                    'type': 'callout',
                    'callout': {
                        'rich_text': [{'type': 'text', 'text': {'content': prompt_text}}],
                        'icon': {'emoji': '💬'},
                        'color': 'blue_background'
                    }
                })
        
        # 結果セクション（トグル内に配置）
        if sections.get('result_content'):
            result_content = sections['result_content'].strip()
            logging.info(f"結果内容の長さ: {len(result_content)} 文字")
            
            # 結果のヘッダー
            blocks.append({
                'object': 'block',
                'type': 'heading_3',
                'heading_3': {
                    'rich_text': [{'type': 'text', 'text': {'content': '✨ 結果'}}]
                }
            })
            
            # 結果ブロックを作成
            result_children = self._create_result_blocks(result_content, md_dir)
            
            logging.info(f"結果ブロック数: {len(result_children)}")
            
            # トグルブロックを作成し、子要素を含める
            toggle_block = {
                'object': 'block',
                'type': 'toggle',
                'toggle': {
                    'rich_text': [{'type': 'text', 'text': {'content': '📖 実行結果を表示'}}],
                    'color': 'purple_background'
                }
            }
            
            # 子要素がある場合のみchildrenを追加
            if result_children:
                toggle_block['toggle']['children'] = result_children
            
            blocks.append(toggle_block)
        else:
            logging.warning("結果セクションが見つかりませんでした")
        
        return self._validate_blocks(blocks)
    
    def _parse_remote_claude_sections(self, md_text: str) -> Dict[str, Any]:
        """remote-claude形式のセクションを解析（改善版）"""
        sections = {}
        lines = md_text.split('\n')
        
        current_section = None
        prompt_lines = []
        result_lines = []
        metadata_lines = []
        
        # セクションの境界を見つける
        prompt_start = -1
        result_start = -1
        
        for i, line in enumerate(lines):
            # 実行記録のヘッダー
            if match := re.match(r'^##\s*実行記録:\s*(.+)$', line):
                sections['execution_header'] = f"実行記録: {match.group(1)}"
                current_section = 'metadata'
                continue
            
            # メタデータ（接続先、プロンプトファイル）
            if current_section == 'metadata' and '**' in line:
                # **を除去してクリーンな形式に
                clean_line = re.sub(r'\*\*([^:]+):\*\*\s*(.+)', r'\1: \2', line)
                if clean_line != line:  # 変換が成功した場合のみ追加
                    metadata_lines.append(clean_line)
                continue
            
            # プロンプトセクションの開始
            if re.match(r'^###\s+プロンプト', line):
                sections['prompt_title'] = 'プロンプト'
                prompt_start = i + 1
                current_section = 'prompt'
                continue
            
            # 結果セクションの開始
            if re.match(r'^###\s+結果', line):
                sections['result_title'] = '結果'
                result_start = i + 1
                current_section = 'result'
                # プロンプトセクションの終了
                if prompt_start >= 0 and result_start > prompt_start:
                    prompt_lines = lines[prompt_start:i]
                continue
        
        # プロンプト内容の処理
        if prompt_lines:
            # > [!NOTE] などのコールアウトと引用記号を除去
            clean_prompt_lines = []
            skip_next = False
            for line in prompt_lines:
                if line.startswith('> [!'):
                    skip_next = True
                    continue
                if skip_next and line.startswith('> **'):
                    skip_next = False
                    continue
                # 引用記号を除去
                if line.startswith('>'):
                    clean_line = line[1:].lstrip()
                    if clean_line or line == '>':  # 空行も保持
                        clean_prompt_lines.append(clean_line)
                elif line.strip() and not line.startswith('#'):
                    clean_prompt_lines.append(line)
            
            sections['prompt_content'] = '\n'.join(clean_prompt_lines).strip()
        
        # 結果内容の処理
        if result_start >= 0:
            # 結果の終わりを見つける（次のセクションまたはファイルの終わり）
            result_end = len(lines)
            for i in range(result_start, len(lines)):
                # 区切り線（フロントマター）を検出
                if lines[i].startswith('---') and i > result_start:
                    result_end = i
                    break
                # 新しい実行記録セクションを検出（別のremote-claude実行）
                if re.match(r'^##\s+実行記録:', lines[i]) and i > result_start:
                    result_end = i
                    break
                # 注意: 結果内の ## は含める（Claude の応答の一部なので）
            
            result_lines = lines[result_start:result_end]
            
            # 結果内容をクリーンアップ
            clean_result_lines = []
            for line in result_lines:
                # 引用記号がある場合は除去
                if line.startswith('>'):
                    clean_line = line[1:].lstrip()
                    clean_result_lines.append(clean_line)
                else:
                    clean_result_lines.append(line)
            
            sections['result_content'] = '\n'.join(clean_result_lines).strip()
            
            logging.info(f"結果セクション: {result_start}行目から{result_end}行目まで")
        
        # セクションを設定
        if metadata_lines:
            sections['metadata'] = metadata_lines
        
        # デバッグ情報
        logging.info(f"プロンプト内容の長さ: {len(sections.get('prompt_content', ''))} 文字")
        logging.info(f"結果内容の長さ: {len(sections.get('result_content', ''))} 文字")
        
        return sections
    
    def _create_result_blocks(self, result_content: str, md_dir: Path) -> List[Dict[str, Any]]:
        """結果内容からNotionブロックを作成（トグル内用）"""
        if not result_content:
            logging.warning("結果内容が空です")
            return []
        
        blocks = []
        
        logging.info(f"結果内容をMarkdownとして処理: {result_content[:100]}...")
        
        # 結果の内容を処理
        # マークダウンの各要素を適切に変換
        tokens = self.md.parse(result_content)
        
        logging.info(f"トークン数: {len(tokens)}")
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            t = token.type
            
            logging.debug(f"トークン {i}: {t}")
            
            if t == 'heading_open':
                i = self._process_heading_for_toggle(tokens, i, blocks)
            elif t in ('bullet_list_open', 'ordered_list_open'):
                i = self._process_list_for_toggle(tokens, i, blocks)
            elif t == 'paragraph_open':
                i = self._process_paragraph_for_toggle(tokens, i, blocks, md_dir)
            elif t == 'fence':
                i = self._process_code_block(tokens, i, blocks)
            elif t == 'blockquote_open':
                i = self._process_blockquote_for_toggle(tokens, i, blocks)
            elif t == 'hr':
                blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
                i += 1
            elif t == 'inline':
                # インライン要素の処理
                txt = token.content.strip()
                if txt:
                    blocks.append({
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                    })
                i += 1
            else:
                i += 1
        
        logging.info(f"生成されたブロック数: {len(blocks)}")
        
        return blocks
    
    def _process_heading_for_toggle(self, tokens, i: int, blocks: List[Dict]) -> int:
        """トグル内の見出しを処理"""
        token = tokens[i]
        lvl = int(token.tag[1])
        content = tokens[i+1].content
        
        # トグル内では見出しレベルを調整しない（元のレベルを維持）
        blk = f"heading_{min(lvl, 3)}"  # 最大h3まで
        
        blocks.append({
            'object': 'block',
            'type': blk,
            blk: {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
        })
        
        logging.debug(f"見出しを追加: {content}")
        
        return i + 3
    
    def _process_list_for_toggle(self, tokens, i: int, blocks: List[Dict]) -> int:
        """トグル内のリストを処理"""
        list_type = 'numbered_list_item' if tokens[i].type == 'ordered_list_open' else 'bulleted_list_item'
        i += 1
        
        while i < len(tokens) and tokens[i].type not in ('bullet_list_close', 'ordered_list_close'):
            if tokens[i].type == 'list_item_open':
                # リストアイテムの内容を取得
                content_idx = i + 2
                if content_idx < len(tokens):
                    txt = tokens[content_idx].content
                    
                    blocks.append({
                        'object': 'block',
                        'type': list_type,
                        list_type: {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                    })
                    
                    logging.debug(f"リストアイテムを追加: {txt[:50]}...")
                
                # 次のリストアイテムへ
                i += 5
            else:
                i += 1
        
        return i + 1
    
    def _process_paragraph_for_toggle(self, tokens, i: int, blocks: List[Dict], md_dir: Path) -> int:
        """トグル内の段落を処理"""
        if i + 1 < len(tokens):
            txt = tokens[i+1].content.strip()
            if txt:
                # インライン数式のパターン
                inline_math_pattern = r'\$([^$\n]+)\$'
                
                # ブロック数式のパターンをチェック
                block_math_pattern = r'\$\$\s*(.*?)\s*\$\$'
                block_math_match = re.search(block_math_pattern, txt, re.DOTALL)
                
                if block_math_match:
                    math_content = block_math_match.group(1).strip()
                    blocks.append({
                        'object': 'block',
                        'type': 'equation',
                        'equation': {'expression': math_content}
                    })
                    logging.debug(f"数式を追加: {math_content[:30]}...")
                else:
                    # インライン数式をチェック
                    inline_math_matches = list(re.finditer(inline_math_pattern, txt))
                    if inline_math_matches:
                        self._process_inline_math(txt, inline_math_matches, blocks)
                    else:
                        # 通常のテキスト処理
                        blocks.append({
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                        })
                        logging.debug(f"段落を追加: {txt[:50]}...")
        
        return i + 2
    
    def _process_blockquote_for_toggle(self, tokens, i: int, blocks: List[Dict]) -> int:
        """トグル内の引用を処理"""
        i += 1
        content_lines = []
        
        while i < len(tokens) and tokens[i].type != 'blockquote_close':
            if tokens[i].type == 'paragraph_open':
                if i + 1 < len(tokens):
                    content_lines.append(tokens[i+1].content)
                i += 2
            i += 1
        
        if content_lines:
            content = '\n'.join(content_lines)
            blocks.append({
                'object': 'block',
                'type': 'quote',
                'quote': {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
            })
        
        return i + 1
    
    def _process_code_block(self, tokens, i: int, blocks: List[Dict]) -> int:
        """コードブロックを処理"""
        token = tokens[i]
        language = token.info or 'plain text'
        content = token.content
        
        # Notion APIで無効な言語名を変換
        language_mapping = {
            'text': 'plain text',
            'txt': 'plain text',
            'plaintext': 'plain text',
            'sh': 'shell',
            'bash': 'shell',
            'zsh': 'shell',
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'yml': 'yaml',
            'md': 'markdown',
            '': 'plain text'
        }
        
        # 言語名の正規化
        normalized_language = language.lower().strip()
        if normalized_language in language_mapping:
            language = language_mapping[normalized_language]
        elif normalized_language == '':
            language = 'plain text'
        
        # 数式として処理するかチェック
        if normalized_language in ('math', 'latex', 'tex'):
            blocks.append({
                'object': 'block',
                'type': 'equation',
                'equation': {'expression': content}
            })
        else:
            blocks.append({
                'object': 'block',
                'type': 'code',
                'code': {
                    'language': language,
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            })
        
        return i + 1
    
    def _process_inline_math(self, text: str, matches, blocks: List[Dict]):
        """インライン数式を含むテキストを処理"""
        if not matches:
            blocks.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': text}}]}
            })
            return
        
        rich_text = []
        last_end = 0
        
        for match in matches:
            # 数式前のテキスト
            if match.start() > last_end:
                rich_text.append({
                    'type': 'text',
                    'text': {'content': text[last_end:match.start()]}
                })
            
            # 数式
            math_content = match.group(1)
            rich_text.append({
                'type': 'equation',
                'equation': {'expression': math_content}
            })
            
            last_end = match.end()
        
        # 残りのテキスト
        if last_end < len(text):
            rich_text.append({
                'type': 'text',
                'text': {'content': text[last_end:]}
            })
        
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {'rich_text': rich_text}
        })
    
    def _process_callouts(self, md_text: str) -> str:
        """Obsidianスタイルのコールアウトを処理"""
        lines = md_text.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # コールアウトの開始を検出
            callout_match = re.match(r'>\s*\[!(\w+)\](?:\s*(.*))?', line)
            if callout_match:
                callout_type = callout_match.group(1).upper()
                callout_title = callout_match.group(2) or callout_type.title()
                
                # コールアウトの内容を収集
                callout_content = []
                i += 1
                
                while i < len(lines) and (lines[i].startswith('>') or lines[i].strip() == ''):
                    content_line = lines[i]
                    if content_line.startswith('>'):
                        content_line = content_line[1:].lstrip()
                    callout_content.append(content_line)
                    i += 1
                
                # コールアウトをMarkdown引用に変換
                emoji = self.parser.CALLOUT_TYPES.get(callout_type, '📝')
                processed_lines.append(f'> **{emoji} {callout_title}**')
                processed_lines.append('>')
                for content in callout_content:
                    if content.strip():
                        processed_lines.append(f'> {content}')
                    else:
                        processed_lines.append('>')
                
                continue
            
            processed_lines.append(line)
            i += 1
        
        return '\n'.join(processed_lines)
    
    def _process_text_with_block_math(self, md_text: str, md_dir: Path, blocks: List[Dict]):
        """テキストを処理してブロック数式を検出"""
        # ブロック数式のパターン
        block_math_pattern = r'\$\$\s*(.*?)\s*\$\$'
        
        # テキストを分割
        parts = re.split(block_math_pattern, md_text, flags=re.DOTALL)
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
                
            if i % 2 == 1:  # 数式部分
                blocks.append({
                    'object': 'block',
                    'type': 'equation',
                    'equation': {'expression': part.strip()}
                })
            else:  # 通常のMarkdown部分
                # 通常のMarkdown処理
                tokens = self.md.parse(part)
                j = 0
                while j < len(tokens):
                    token = tokens[j]
                    t = token.type
                    
                    if t == 'heading_open':
                        j = self._process_heading(tokens, j, blocks)
                    elif t in ('bullet_list_open', 'ordered_list_open'):
                        j = self._process_list(tokens, j, blocks)
                    elif t == 'paragraph_open':
                        j = self._process_paragraph(tokens, j, blocks, md_dir)
                    elif t == 'fence':
                        j = self._process_code_block(tokens, j, blocks)
                    elif t == 'blockquote_open':
                        j = self._process_blockquote(tokens, j, blocks)
                    elif t == 'hr':
                        blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
                        j += 1
                    else:
                        j += 1
    
    def _process_heading(self, tokens, i: int, blocks: List[Dict]) -> int:
        """見出しを処理"""
        token = tokens[i]
        level = int(token.tag[1])
        content = tokens[i+1].content
        
        heading_type = f"heading_{min(level, 3)}"
        blocks.append({
            'object': 'block',
            'type': heading_type,
            heading_type: {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
        })
        
        return i + 3
    
    def _process_list(self, tokens, i: int, blocks: List[Dict]) -> int:
        """リストを処理"""
        list_type = 'numbered_list_item' if tokens[i].type == 'ordered_list_open' else 'bulleted_list_item'
        i += 1
        
        while i < len(tokens) and tokens[i].type not in ('bullet_list_close', 'ordered_list_close'):
            if tokens[i].type == 'list_item_open':
                content_idx = i + 2
                if content_idx < len(tokens):
                    txt = tokens[content_idx].content
                    blocks.append({
                        'object': 'block',
                        'type': list_type,
                        list_type: {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                    })
                i += 5
            else:
                i += 1
        
        return i + 1
    
    def _process_paragraph(self, tokens, i: int, blocks: List[Dict], md_dir: Path) -> int:
        """段落を処理"""
        if i + 1 < len(tokens):
            txt = tokens[i+1].content.strip()
            if txt:
                # 画像の処理
                img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                img_match = re.search(img_pattern, txt)
                
                if img_match:
                    alt_text = img_match.group(1)
                    img_path = img_match.group(2)
                    
                    # 相対パスを絶対パスに変換
                    if not img_path.startswith(('http://', 'https://')):
                        full_img_path = md_dir / img_path
                        img_url = self.image_uploader.get_image_url(full_img_path)
                    else:
                        img_url = img_path
                    
                    blocks.append({
                        'object': 'block',
                        'type': 'image',
                        'image': {'external': {'url': img_url}}
                    })
                else:
                    # インライン数式のパターン
                    inline_math_pattern = r'\$([^$\n]+)\$'
                    inline_math_matches = list(re.finditer(inline_math_pattern, txt))
                    
                    if inline_math_matches:
                        self._process_inline_math(txt, inline_math_matches, blocks)
                    else:
                        blocks.append({
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': txt}}]}
                        })
        
        return i + 2
    
    def _process_blockquote(self, tokens, i: int, blocks: List[Dict]) -> int:
        """引用ブロックを処理"""
        i += 1
        content_lines = []
        
        while i < len(tokens) and tokens[i].type != 'blockquote_close':
            if tokens[i].type == 'paragraph_open':
                if i + 1 < len(tokens):
                    content_lines.append(tokens[i+1].content)
                i += 2
            i += 1
        
        if content_lines:
            content = '\n'.join(content_lines)
            blocks.append({
                'object': 'block',
                'type': 'quote',
                'quote': {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
            })
        
        return i + 1
    
    def _validate_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ブロックを検証して制限に準拠させる"""
        validated_blocks = []
        
        for block in blocks:
            # ブロック数の制限チェック
            if len(validated_blocks) >= self.config.max_blocks_per_page:
                logging.warning(f"ブロック数が制限({self.config.max_blocks_per_page})に達しました")
                break
            
            # rich_textの長さ制限チェック
            self._validate_rich_text_length(block)
            
            # トグルブロックの子要素も検証
            if block.get('type') == 'toggle' and 'toggle' in block and 'children' in block['toggle']:
                children = block['toggle']['children']
                validated_children = []
                
                for child in children:
                    if len(validated_children) < 50:  # トグル内の子要素制限
                        self._validate_rich_text_length(child)
                        validated_children.append(child)
                    else:
                        logging.warning("トグル内の子要素が制限に達しました")
                        break
                
                block['toggle']['children'] = validated_children
            
            validated_blocks.append(block)
        
        return validated_blocks
    
    def _validate_rich_text_length(self, block: Dict[str, Any]):
        """rich_textの長さを制限内に収める"""
        if 'paragraph' in block:
            self._truncate_rich_text(block['paragraph'])
        elif 'heading_1' in block:
            self._truncate_rich_text(block['heading_1'])
        elif 'heading_2' in block:
            self._truncate_rich_text(block['heading_2'])
        elif 'heading_3' in block:
            self._truncate_rich_text(block['heading_3'])
        elif 'quote' in block:
            self._truncate_rich_text(block['quote'])
        elif 'bulleted_list_item' in block:
            self._truncate_rich_text(block['bulleted_list_item'])
        elif 'numbered_list_item' in block:
            self._truncate_rich_text(block['numbered_list_item'])
        elif 'toggle' in block:
            self._truncate_rich_text(block['toggle'])
        elif 'callout' in block:
            self._truncate_rich_text(block['callout'])
    
    def _truncate_rich_text(self, block_content: Dict[str, Any]):
        """rich_textを制限内に切り詰める"""
        if 'rich_text' in block_content:
            rich_text_list = block_content['rich_text']
            total_length = 0
            truncated_rich_text = []
            
            for rt in rich_text_list:
                if rt.get('type') == 'text':
                    text_content = rt['text']['content']
                    remaining_length = self.config.max_rich_text_length - total_length
                    
                    if len(text_content) <= remaining_length:
                        truncated_rich_text.append(rt)
                        total_length += len(text_content)
                    else:
                        # 切り詰める
                        truncated_text = text_content[:remaining_length - 3] + '...'
                        rt['text']['content'] = truncated_text
                        truncated_rich_text.append(rt)
                        break
                else:
                    truncated_rich_text.append(rt)
            
            block_content['rich_text'] = truncated_rich_text