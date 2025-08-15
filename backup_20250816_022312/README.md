# Notion Markdown Uploader

MarkdownファイルをNotionにアップロードするPythonツールです。フロントマター、画像、数式、コードブロックなど、様々なMarkdown要素をサポートしています。

## 特徴

- **フロントマター対応**: YAMLフロントマターからタイトルや要約を抽出
- **画像アップロード**: FTPサーバーやImgBBへの画像アップロード機能
- **数式サポート**: LaTeX形式の数式をNotionの数式ブロックに変換
- **リンク処理**: Markdownリンクを見出し付きブックマークとして変換
- **大容量対応**: 大きなファイルを複数ページに自動分割
- **柔軟な設定**: 環境変数による設定管理

## インストール

```bash
pip install -r requirements.txt
```

## 設定

### 1. Notion認証情報

以下のファイルを作成してください：

- `~/.token/notion/.terminal_memo_id`: NotionデータベースID
- `~/.token/notion/.terminal_memo_token`: Notion APIトークン

### 2. 画像アップロード設定（オプション）

環境変数で設定：

```bash
# FTPサーバー設定
export FTP_USER="your_ftp_username"
export FTP_PASS="your_ftp_password"

# ImgBB設定
export IMGBB_API_KEY="your_imgbb_api_key"
```

## 使用方法

```bash
python main.py your_markdown_file.md

# 詳細ログ表示
python main.py -v your_markdown_file.md
```

## プロジェクト構造

```
.
├── main.py                 # エントリーポイント
├── src/
│   ├── __init__.py
│   ├── config.py          # 設定管理
│   ├── uploader.py        # メインアップローダー
│   ├── markdown_parser.py # Markdownパーサー
│   ├── notion_block_converter.py # Notionブロック変換
│   ├── notion_client.py   # Notionクライアント
│   └── image_uploader.py  # 画像アップロード
├── requirements.txt
├── setup.py
└── README.md
```

## サポートされる機能

### Markdown要素

- 見出し（H1-H6）
- 段落
- リスト（箇条書き・番号付き）
- コードブロック
- 引用
- 水平線
- 画像
- リンク

### 特殊機能

- **数式**: `$$...$$` または言語指定 `math`/`latex`/`tex` のコードブロック
- **動画埋め込み**: YouTube、Vimeoリンクの自動埋め込み
- **画像アップロード**: ローカル画像の自動アップロード
- **長文分割**: Notion APIの制限に応じた自動分割

### フロントマター例

```yaml
---
title: "記事のタイトル"
abstract: "記事の要約"
summary: "記事のサマリー"
---

# Markdownコンテンツ

本文はここに書きます...
```

## 開発

### テストの実行

```bash
pip install -e ".[dev]"
pytest
```

### コードフォーマット

```bash
black .
flake8 .
mypy src/
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューは歓迎です。

## 注意事項

- Notion APIの制限により、1ページあたり100ブロックまでです
- 大きなファイルは自動的に複数ページに分割されます
- 画像アップロードにはFTPまたはImgBBの設定が必要です
