"""
Markdownパース機能モジュール
"""

import re
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional


class MarkdownParser:
    """Markdownファイルのパース処理を担当するクラス"""
    
    # Obsidianスタイルのコールアウトタイプ
    CALLOUT_TYPES = {
        'NOTE': '📝',
        'TIP': '💡',
        'INFO': 'ℹ️',
        'TODO': '☑️',
        'IMPORTANT': '❗',
        'WARNING': '⚠️',
        'CAUTION': '⚠️',
        'ERROR': '❌',
        'DANGER': '🚨',
        'EXAMPLE': '📋',
        'QUOTE': '💬',
        'ABSTRACT': '📄',
        'SUCCESS': '✅',
        'QUESTION': '❓',
        'FAILURE': '❌',
        'BUG': '🐛',
        'FAQ': '❔',
        'RESULT': '✨',  # 結果用の新しいタイプ
        'PROMPT': '💬'   # プロンプト用の新しいタイプ
    }
    
    @staticmethod
    def parse_frontmatter_and_body(file_path: Path) -> Tuple[Dict[str, str], str]:
        """フロントマターと本文を分離してパースする"""
        try:
            text = file_path.read_text(encoding='utf-8')
        except Exception as e:
            raise RuntimeError(f"ファイル読み込みに失敗: {e}")
        
        fm_match = re.match(r"^---\s*\n(.+?)\n---\s*\n(.*)$", text, flags=re.S)
        
        if fm_match:
            fm_content, body = fm_match.group(1), fm_match.group(2)
            frontmatter = {}
            
            for line in fm_content.splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    frontmatter[key.strip()] = val.strip()
        else:
            frontmatter, body = {}, text
        
        # 実行記録のメタデータを抽出（remote-claude形式）
        execution_metadata = MarkdownParser._extract_execution_metadata(body)
        if execution_metadata:
            frontmatter.update(execution_metadata)
        
        return frontmatter, body
    
    @staticmethod
    def _extract_execution_metadata(text: str) -> Dict[str, str]:
        """実行記録のメタデータを抽出する"""
        metadata = {}
        
        # 実行記録のパターンを検索
        execution_pattern = r'## 実行記録:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        match = re.search(execution_pattern, text)
        if match:
            metadata['execution_time'] = match.group(1)
        
        # 接続先の抽出
        host_pattern = r'\*\*接続先:\*\*\s*(.+?)(?:\s|$)'
        match = re.search(host_pattern, text)
        if match:
            metadata['connection_host'] = match.group(1).strip()
        
        # プロンプトファイルの抽出
        prompt_file_pattern = r'\*\*プロンプトファイル:\*\*\s*(.+?)(?:\s|$)'
        match = re.search(prompt_file_pattern, text)
        if match:
            metadata['prompt_file'] = match.group(1).strip()
        
        return metadata
    
    @staticmethod
    def preprocess_remote_claude_format(text: str) -> str:
        """remote-claude形式のマークダウンを前処理する"""
        lines = text.split('\n')
        processed_lines = []
        in_result_section = False
        result_section_started = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 実行記録セクションの処理
            if re.match(r'^#{2,}\s+実行記録:', line):
                processed_lines.append(re.sub(r'^#{2,}\s+実行記録:', '## 📊 実行記録:', line))
                i += 1
                continue
            
            # プロンプトセクションの処理
            if re.match(r'^###\s+プロンプト', line):
                processed_lines.append('### 💬 プロンプト')
                i += 1
                continue
            
            # 結果セクションの開始を検出
            if re.match(r'^###\s+結果', line):
                processed_lines.append('### ✨ 結果')
                # 結果セクションをコールアウト形式で開始
                processed_lines.append('> [!RESULT] 実行結果')
                in_result_section = True
                result_section_started = True
                i += 1
                continue
            
            # 結果セクション内の処理
            if in_result_section:
                # 次のセクションの開始を検出（## や --- など）
                if re.match(r'^#{1,3}\s+', line) or line.strip() == '---':
                    in_result_section = False
                    processed_lines.append(line)
                else:
                    # 結果内容を引用ブロック化
                    if line.strip():  # 空行でない場合
                        # すでに引用記号がある場合はそのまま、ない場合は追加
                        if not line.startswith('>'):
                            processed_lines.append(f'> {line}')
                        else:
                            processed_lines.append(line)
                    else:
                        # 空行も引用ブロック内で維持
                        processed_lines.append('>')
                i += 1
                continue
            
            # その他の行はそのまま追加
            processed_lines.append(line)
            i += 1
        
        return '\n'.join(processed_lines)
    
    @staticmethod
    def extract_markdown_links(text: str) -> List[Dict[str, Any]]:
        """Markdownのリンク構文からリンク情報を抽出する"""
        pattern = r'\[(.*?)\]\((.*?)\)'
        matches = list(re.finditer(pattern, text))
        links = []
        
        for match in matches:
            links.append({
                'text': match.group(1),
                'url': match.group(2),
                'original': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        
        return links
    
    @staticmethod
    def split_long_text(text: str, max_length: int = 2000) -> List[str]:
        """長いテキストを指定された最大長で分割する"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        for line in text.splitlines(True):  # keepends=True で改行を維持
            if len(current_chunk) + len(line) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    # 1行が最大長を超える場合は、文字単位で分割
                    while len(line) > max_length:
                        chunks.append(line[:max_length])
                        line = line[max_length:]
                    current_chunk = line
            else:
                current_chunk += line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    @staticmethod
    def is_latex_code_block(lang: str, content: str) -> bool:
        """コードブロックがLaTeXコードかどうかを判定する"""
        # 言語指定が数学関連かどうか
        if lang in ('math', 'latex', 'tex'):
            return True
        
        # 内容がLaTeXのパターンを含むかどうか
        latex_patterns = [
            r'\\begin{', r'\\end{', r'\\frac', r'\\sum', r'\\int', 
            r'\\lim', r'\\nabla', r'\\partial', r'\\alpha', r'\\beta',
            r'\\gamma', r'\\delta', r'\\epsilon', r'\\zeta', r'\\eta',
            r'\\theta', r'\\iota', r'\\kappa', r'\\lambda', r'\\mu',
            r'\\nu', r'\\xi', r'\\pi', r'\\rho', r'\\sigma', r'\\tau',
            r'\\upsilon', r'\\phi', r'\\chi', r'\\psi', r'\\omega',
            r'\\left', r'\\right', r'\\mathbf', r'\\mathcal', r'\\mathrm',
            r'\\cdot', r'\\times', r'\\div', r'\\pm', r'\\mp',
            r'\\cap', r'\\cup', r'\\subset', r'\\supset', r'\\in',
            r'\\notin', r'\\forall', r'\\exists', r'\\neg', r'\\vee',
            r'\\wedge', r'\\Rightarrow', r'\\Leftarrow', r'\\Leftrightarrow'
        ]
        
        return any(pattern in content for pattern in latex_patterns)
    
    @staticmethod
    def is_video_link(url: str, video_domains: tuple) -> bool:
        """URLが動画リンクかどうかを判定する"""
        return bool(url) and any(domain in url for domain in video_domains)
