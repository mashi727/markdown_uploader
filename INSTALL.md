# markdown_uploader セットアップガイド

## プロジェクト構造の準備

コマンドラインツールとして動作させるため、以下のファイルをプロジェクトのルートディレクトリに追加します：

1. `setup.py` - パッケージ設定ファイル（提供済み）
2. `cli.py` - コマンドラインインターフェース（提供済み）

## インストール手順

### 1. リポジトリのクローンとファイル配置
```bash
git clone https://github.com/mashi727/markdown_uploader.git
cd markdown_uploader

# 提供されたファイルを配置
# - setup.py をプロジェクトルートに配置
# - cli.py をプロジェクトルートに配置
```

### 2. 仮想環境の作成（推奨）
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 4. コマンドラインツールとしてインストール
```bash
pip install -e .
```

## 設定

### 1. Notion設定ファイルの作成
```bash
# 設定ディレクトリの作成
mkdir -p ~/.config

# NotionデータベースIDを設定
echo "YOUR_NOTION_DATABASE_ID" > ~/.config/.terminal_memo_id

# Notion APIトークンを設定
echo "YOUR_NOTION_API_TOKEN" > ~/.config/.terminal_memo_token
```

### 2. 環境変数の設定（オプション）

#### FTPサーバー設定（画像アップロード用）
```bash
export FTP_USER="your_ftp_username"
export FTP_PASS="your_ftp_password"
```

#### ImgBB設定（画像アップロード用）
```bash
export IMGBB_API_KEY="your_imgbb_api_key"
```

これらの環境変数を永続化する場合は、`.bashrc`、`.zshrc`などに追加してください。

## 使用方法

### 基本的な使用方法
```bash
# インストール後はmduploadコマンドが使用可能
mdupload your_markdown_file.md

# または従来通り
python main.py your_markdown_file.md
```

### 詳細ログ表示
```bash
mdupload -v your_markdown_file.md
```

### ヘルプの表示
```bash
mdupload --help
```

## トラブルシューティング

### 1. コマンドが見つからない場合
```bash
# パスを確認
which mdupload

# または直接実行
python -m markdown_uploader your_file.md
```

### 2. 設定ファイルエラー
```bash
# 設定ファイルの確認
ls -la ~/.config/.terminal_memo_*

# パーミッションの修正
chmod 600 ~/.config/.terminal_memo_*
```

### 3. 画像アップロードエラー
- FTPまたはImgBBの設定が正しいか確認
- ネットワーク接続を確認
- 画像ファイルのパスが正しいか確認

## アンインストール
```bash
pip uninstall markdown-uploader
```
