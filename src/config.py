"""
設定管理モジュール
"""

import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """設定クラス"""
    
    # Notion設定
    database_id: str
    notion_token: str
    
    # FTP設定
    ftp_host: str = "m2.coreserver.jp"
    ftp_user: Optional[str] = None
    ftp_pass: Optional[str] = None
    ftp_directory: str = "public_html/assets"
    ftp_base_url: str = "http://massy.m2.coreserver.jp/assets"
    
    # ImgBB設定
    imgbb_api_key: Optional[str] = None
    
    # Notion制限
    max_blocks_per_page: int = 100
    max_rich_text_length: int = 2000
    
    # サポートされる動画ドメイン
    video_domains: tuple = ('youtube.com', 'youtu.be', 'vimeo.com')
    
    def __init__(self):
        """設定を初期化する"""
        self._load_notion_config()
        self._load_ftp_config()
        self._load_imgbb_config()
    
    def _load_notion_config(self):
        """Notion設定を読み込む"""
        config_dir = Path("~/.config").expanduser()
        
        try:
            self.database_id = (config_dir / ".terminal_memo_id").read_text(encoding='utf-8').strip()
            self.notion_token = (config_dir / ".terminal_memo_token").read_text(encoding='utf-8').strip()
        except FileNotFoundError as e:
            logging.error(f"Notion認証ファイルが見つかりません: {e}")
            sys.exit(1)
    
    def _load_ftp_config(self):
        """FTP設定を読み込む"""
        self.ftp_user = os.environ.get("FTP_USER")
        self.ftp_pass = os.environ.get("FTP_PASS")
        
        if not self.ftp_user or not self.ftp_pass:
            logging.warning("FTP認証情報が設定されていません。")
    
    def _load_imgbb_config(self):
        """ImgBB設定を読み込む"""
        self.imgbb_api_key = os.environ.get("IMGBB_API_KEY")
    
    @property
    def has_ftp_config(self) -> bool:
        """FTP設定が有効かどうか"""
        return bool(self.ftp_user and self.ftp_pass)
    
    @property
    def has_imgbb_config(self) -> bool:
        """ImgBB設定が有効かどうか"""
        return bool(self.imgbb_api_key)
