"""
Markdownパース機能モジュール
"""

import re
from pathlib import Path
from typing import Dict, Any, Tuple, List


class MarkdownParser:
    """Markdownファイルのパース処理を担当するクラス"""
    
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
        
        return frontmatter, body
    
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
