#!/usr/bin/env python
"""
Markdown Uploader CLI
コマンドラインインターフェースモジュール
"""
import argparse
import sys
import os
from pathlib import Path
import logging

# srcディレクトリをPythonパスに追加
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 必要なモジュールをインポート
try:
    # 既存のmain.pyから設定を読み込む方法を確認
    import main
except ImportError as e:
    print(f"エラー: main.pyのインポートに失敗しました: {e}")
    sys.exit(1)


def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="MarkdownファイルをNotionにアップロードします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  mdupload README.md              # ファイルをアップロード
  mdupload -v document.md         # 詳細ログ付きでアップロード
  mdupload --dry-run test.md      # アップロードせずに確認
  mdupload --config              # 設定を表示
  
設定ファイル:
  ~/.token/notion/.terminal_memo_id     # NotionデータベースID
  ~/.token/notion/.terminal_memo_token  # Notion APIトークン
  
環境変数（オプション）:
  FTP_USER, FTP_PASS             # FTPサーバー設定
  IMGBB_API_KEY                  # ImgBB API設定
        """
    )
    
    parser.add_argument(
        "markdown_file",
        nargs="?",
        help="アップロードするMarkdownファイル"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細ログを表示"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にアップロードせずに処理内容を確認"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="現在の設定を表示"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    return parser.parse_args()


def show_config():
    """現在の設定を表示"""
    config_dir = Path.home() / ".token/notion"
    db_id_file = config_dir / ".terminal_memo_id"
    token_file = config_dir / ".terminal_memo_token"
    
    print("=== Markdown Uploader 設定 ===")
    
    print(f"\nNotion設定:")
    
    # データベースID
    if db_id_file.exists():
        try:
            with open(db_id_file, 'r') as f:
                db_id = f.read().strip()
                print(f"  データベースID: {'設定済み' if db_id else '未設定'}")
        except:
            print(f"  データベースID: 読み込みエラー")
    else:
        print(f"  データベースID: 未設定")
    
    # APIトークン
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                token = f.read().strip()
                print(f"  APIトークン: {'設定済み' if token else '未設定'}")
        except:
            print(f"  APIトークン: 読み込みエラー")
    else:
        print(f"  APIトークン: 未設定")
    
    print(f"\n画像アップロード設定:")
    print(f"  FTPユーザー: {'設定済み' if os.getenv('FTP_USER') else '未設定'}")
    print(f"  FTPパスワード: {'設定済み' if os.getenv('FTP_PASS') else '未設定'}")
    print(f"  ImgBB APIキー: {'設定済み' if os.getenv('IMGBB_API_KEY') else '未設定'}")
    
    print(f"\n設定ファイルの場所:")
    print(f"  {db_id_file}")
    print(f"  {token_file}")
    
    if not (db_id_file.exists() and token_file.exists()):
        print("\n設定ファイルを作成するには:")
        print(f"  echo 'YOUR_DATABASE_ID' > {db_id_file}")
        print(f"  echo 'YOUR_API_TOKEN' > {token_file}")


def check_config():
    """設定ファイルの存在を確認"""
    config_dir = Path.home() / ".token/notion"
    db_id_file = config_dir / ".terminal_memo_id"
    token_file = config_dir / ".terminal_memo_token"
    
    if not db_id_file.exists() or not token_file.exists():
        print("エラー: Notion設定が不完全です")
        print("以下のファイルを作成してください:")
        print(f"  echo 'YOUR_DATABASE_ID' > {db_id_file}")
        print(f"  echo 'YOUR_API_TOKEN' > {token_file}")
        return False
    
    # ファイルが空でないか確認
    try:
        with open(db_id_file, 'r') as f:
            if not f.read().strip():
                print(f"エラー: {db_id_file} が空です")
                return False
        with open(token_file, 'r') as f:
            if not f.read().strip():
                print(f"エラー: {token_file} が空です")
                return False
    except Exception as e:
        print(f"エラー: 設定ファイルの読み込みに失敗しました: {e}")
        return False
    
    return True


def main():
    """メインエントリーポイント"""
    args = parse_arguments()
    
    # 設定表示モード
    if args.config:
        show_config()
        return 0
    
    # ファイルが指定されていない場合
    if not args.markdown_file:
        print("エラー: Markdownファイルを指定してください")
        print("使用方法: mdupload [オプション] <markdownファイル>")
        print("ヘルプ: mdupload --help")
        return 1
    
    # ファイルの存在確認
    markdown_path = Path(args.markdown_file).resolve()
    if not markdown_path.exists():
        print(f"エラー: ファイルが見つかりません: {markdown_path}")
        return 1
    
    if not markdown_path.is_file():
        print(f"エラー: ディレクトリは指定できません: {markdown_path}")
        return 1
    
    # 設定の確認
    if not check_config():
        return 1
    
    try:
        # ドライランモード
        if args.dry_run:
            print(f"=== ドライランモード ===")
            print(f"ファイル: {markdown_path}")
            print(f"サイズ: {markdown_path.stat().st_size:,} bytes")
            
            # ファイル内容の簡単な解析
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            print(f"行数: {len(lines)}")
            
            # 画像ファイルの検出
            import re
            images = re.findall(r'!\[.*?\]\((.*?)\)', content)
            if images:
                print(f"画像: {len(images)}個")
                for img in images[:5]:  # 最初の5個まで表示
                    print(f"  - {img}")
                if len(images) > 5:
                    print(f"  ... 他 {len(images) - 5}個")
            
            # フロントマターの検出
            if content.startswith('---'):
                end_idx = content.find('---', 3)
                if end_idx > 0:
                    print("フロントマター: あり")
            
            print("\n実際にアップロードするには --dry-run オプションを外してください")
            return 0
        
        # 既存のmain.pyの処理を呼び出す
        print(f"アップロード中: {markdown_path}")
        
        # Pythonファイルを直接実行
        import subprocess
        cmd = [sys.executable, "main.py"]
        if args.verbose:
            cmd.append("-v")
        cmd.append(str(markdown_path))
        
        try:
            # カレントディレクトリをプロジェクトルートに変更して実行
            result = subprocess.run(cmd, cwd=str(current_dir))
            return result.returncode
        except Exception as e:
            print(f"実行エラー: {e}")
            return 1
        
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        return 130
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
