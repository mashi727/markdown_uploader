"""
画像アップロード機能モジュール
"""

import time
import uuid
import ftplib
import base64
import logging
import traceback
from pathlib import Path
from typing import Optional

import requests

from .config import Config


class ImageUploader:
    """画像アップロード処理を担当するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def get_image_url(self, local_path: Path) -> str:
        """画像URLを取得する"""
        logging.info(f"画像URLの取得を開始: {local_path}")
        
        if not local_path.exists() or not local_path.is_file():
            logging.warning(f"ファイルが存在しません: {local_path}")
            return ''
        
        # FTPアップロードを試行
        if self.config.has_ftp_config:
            url = self._upload_to_ftp(local_path)
            if url:
                return url
        
        # ImgBBアップロードを試行
        if self.config.has_imgbb_config:
            url = self._upload_to_imgbb(local_path)
            if url:
                return url
        
        logging.warning(f"画像URLの取得に失敗し placeholder を使用: {local_path}")
        return "https://via.placeholder.com/600x400?text=Image+Upload+Failed"
    
    def _upload_to_ftp(self, local_path: Path) -> Optional[str]:
        """FTPサーバーに画像をアップロードする"""
        try:
            timestamp = int(time.time())
            file_uuid = str(uuid.uuid4())[:8].upper()
            file_ext = local_path.suffix.lower()
            file_name = f"{timestamp}_{file_uuid}{file_ext}"
            
            with ftplib.FTP(self.config.ftp_host) as ftp:
                ftp.login(user=self.config.ftp_user, passwd=self.config.ftp_pass)
                ftp.cwd("public_html")
                
                try:
                    ftp.cwd("assets")
                except ftplib.error_perm:
                    ftp.mkd("assets")
                    ftp.cwd("assets")
                
                with open(local_path, 'rb') as file:
                    ftp.storbinary(f'STOR {file_name}', file)
            
            url = f"{self.config.ftp_base_url}/{file_name}"
            logging.info(f"FTPアップロード成功: {url}")
            return url
            
        except Exception as e:
            logging.error(f"FTPアップロードエラー: {e}")
            traceback.print_exc()
            return None
    
    def _upload_to_imgbb(self, local_path: Path) -> Optional[str]:
        """ImgBBに画像をアップロードしてURLを取得する"""
        try:
            with open(local_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                'image': base64_image,
                'key': self.config.imgbb_api_key
            }
            
            response = requests.post("https://api.imgbb.com/1/upload", data=payload)
            response.raise_for_status()
            
            data = response.json().get('data', {})
            url = data.get('url', '')
            
            if url:
                logging.info(f"ImgBBアップロード成功: {url}")
            
            return url
            
        except Exception as e:
            logging.error(f"ImgBBアップロードエラー: {e}")
            traceback.print_exc()
            return None
