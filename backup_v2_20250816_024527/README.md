# Notion Markdown Uploader

MarkdownファイルをNotionにアップロードするPythonツールです。フロントマター、画像、数式、コードブロック、Obsidianスタイルのコールアウトなど、様々なMarkdown要素をサポートしています。

## 🎯 特徴

### 基本機能
- **フロントマター対応**: YAMLフロントマターからタイトルや要約を抽出
- **画像アップロード**: FTPサーバーやImgBBへの画像アップロード機能
- **数式サポート**: LaTeX形式の数式をNotionの数式ブロックに変換
- **リンク処理**: Markdownリンクを見出し付きブックマークとして変換
- **大容量対応**: 大きなファイルを複数ページに自動分割
- **柔軟な設定**: 環境変数による設定管理

### 拡張機能（v2.0新機能）
- **remote-claude形式対応**: `remote-claude`関数で生成されたマークダウンファイルを最適化して処理
- **Obsidianコールアウト対応**: `> [!NOTE]`などのObsidianスタイルのコールアウトをNotionブロックに変換
- **実行記録メタデータ**: 実行時刻、接続先、プロンプトファイル情報を自動抽出
- **視覚的な区別**: エモジとカラーを使用して、プロンプトと結果を見やすく表示

## 📦 インストール

```bash
pip install -r requirements.txt
```

## ⚙️ 設定

### 1. Notion認証情報

以下のファイルを作成してください：

- `~/.config/.terminal_memo_id`: NotionデータベースID
- `~/.config/.terminal_memo_token`: Notion APIトークン

### 2. 画像アップロード設定（オプション）

環境変数で設定：

```bash
# FTPサーバー設定
export FTP_USER="your_ftp_username"
export FTP_PASS="your_ftp_password"

# ImgBB設定
export IMGBB_API_KEY="your_imgbb_api_key"
```

## 🚀 使用方法

### 基本的な使用方法

```bash
python main.py your_markdown_file.md

# 詳細ログ表示
python main.py -v your_markdown_file.md
```

### remote-claude形式のファイルアップロード

```bash
# remote-claude関数で生成されたファイルをアップロード
python main.py 20250816_155518_prompt.md

# 複数のClaude実行記録を一括アップロード
for file in *_prompt.md; do
    python main.py "$file"
done
```

## 📁 プロジェクト構造

```
.
├── main.py                 # エントリーポイント
├── src/
│   ├── __init__.py
│   ├── config.py          # 設定管理
│   ├── uploader.py        # メインアップローダー（remote-claude対応）
│   ├── markdown_parser.py # Markdownパーサー（コールアウト対応）
│   ├── notion_block_converter.py # Notionブロック変換（拡張）
│   ├── notion_client.py   # Notionクライアント（callout対応）
│   └── image_uploader.py  # 画像アップロード
├── requirements.txt
├── setup.py
└── README.md
```

## 📋 サポートされる機能

### Markdown要素

- 見出し（H1-H6）
- 段落
- リスト（箇条書き・番号付き）
- コードブロック
- 引用
- 水平線
- 画像
- リンク
- テーブル

### Obsidianスタイルの要素

#### コールアウト
```markdown
> [!NOTE] メモ
> これは重要な情報です。

> [!WARNING] 警告
> 注意が必要な内容です。

> [!TIP] ヒント
> 便利な情報をお伝えします。
```

サポートされるコールアウトタイプ：
- NOTE (📝), TIP (💡), INFO (ℹ️), TODO (☑️)
- IMPORTANT (❗), WARNING (⚠️), CAUTION (⚠️)
- ERROR (❌), DANGER (🚨), EXAMPLE (📋)
- QUOTE (💬), ABSTRACT (📄), SUCCESS (✅)
- QUESTION (❓), FAILURE (❌), BUG (🐛), FAQ (❔)

### remote-claude形式

`remote-claude`関数で生成されるファイル形式を自動認識し、以下を最適化：

```markdown
---
## 実行記録: 2025-08-16 01:55:18
**接続先:** zeus  
**プロンプトファイル:** test.txt
### プロンプト
> [!NOTE]
> **入力プロンプト**
> 
> 質問内容...
### 結果
回答内容...
```

自動処理される項目：
- 📊 実行記録のメタデータを専用セクションに整理
- 💬 プロンプトを視覚的に区別（青背景のコールアウト）
- ✨ 結果セクションを見やすく表示
- 🖥️ 接続先、⏰ 実行時刻、📝 プロンプトファイルをメタデータとして表示

### 特殊機能

- **数式**: `$...$` または言語指定 `math`/`latex`/`tex` のコードブロック
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

## 🧪 開発

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

## 📜 ライセンス

MIT License

## 🤝 貢献

プルリクエストやイシューは歓迎です。

## ⚠️ 注意事項

- Notion APIの制限により、1ページあたり100ブロックまでです
- 大きなファイルは自動的に複数ページに分割されます
- 画像アップロードにはFTPまたはImgBBの設定が必要です
- calloutブロックがNotionでサポートされていない場合は、自動的にquoteブロックに変換されます

## 🔄 更新履歴

### v2.0.0 (2025-08-16)
- remote-claude形式のファイルサポート追加
- Obsidianスタイルのコールアウト対応
- 実行記録メタデータの自動抽出と整理
- プロンプトと結果の視覚的区別機能
- calloutブロックのフォールバック処理

### v1.0.0
- 初回リリース
- 基本的なMarkdown → Notion変換機能
