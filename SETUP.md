# Project GOZEN セットアップガイド

本ガイドでは、Project GOZEN の開発環境をゼロから構築する手順を説明します。
システム全体への影響を避けるため、Node.js は `nvm` を、Python は `venv` を使用してプロジェクトローカル（またはユーザーローカル）に環境を構築します。

## 1. 前提パッケージのインストール (Ubuntu/Debian)

まず、基本的なツールをインストールします。

```bash
sudo apt update
sudo apt install -y curl git build-essential python3-venv python3-dev
```

## 2. Node.js のセットアップ (nvm使用)

Node.js のバージョン管理ツール `nvm` を使用して、Node.js をインストールします。

### 2-1. nvm のインストール

```bash
# インストールスクリプトの実行
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 設定の反映（シェルを再起動するか、以下を実行）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

### 2-2. Node.js (LTS) のインストール

```bash
# 最新のLTS（Long Term Support）バージョンをインストール
nvm install --lts

# インストール確認
node -v
npm -v
```

## 3. Python 環境のセットアップ

Python の仮想環境 (`venv`) を作成し、依存パッケージをインストールします。

### 3-1. リポジトリのクローン（未実施の場合）

```bash
git clone https://github.com/Tagomori0211/Project-GOZEN.git
cd Project-GOZEN
```

### 3-2. 仮想環境の作成と有効化

```bash
# .venv ディレクトリに仮想環境を作成
python3 -m venv .venv

# 仮想環境の有効化
source .venv/bin/activate
```
※ 以降のコマンドは、仮想環境が有効（プロンプトに `(.venv)` が表示されている状態）で実行してください。

### 3-3. 依存パッケージのインストール

```bash
# pip のアップグレード
pip install --upgrade pip

# 依存関係のインストール
pip install -r requirements.txt
```

## 4. フロントエンドのビルド

WebUIを使用するには、フロントエンドアセットのビルドが必要です。

```bash
cd frontend
npm install
npm run build
cd ..
```

## 5. 環境変数の設定

`.env` ファイルを作成し、必要な設定を行います。

```bash
# サンプルからコピー
cp .env.example .env

# .env を編集（任意のエディタで）
nano .env
```

### .env の主な設定項目
- `GOOGLE_API_KEY` / `GEMINI_API_KEY`: Gemini APIキー（陸軍参謀・書記用）
- `ANTHROPIC_API_KEY`: Anthropic APIキー（海軍参謀用）
- `SERVER_PORT`: サーバーポート（デフォルト: 9000）

**検証用（MOCKモード）の場合**
APIキーがない場合でも、検証スクリプトは `security_level="mock"` を使用することで動作します。

## 5. サーバーの起動

サーバーを起動します。

```bash
# サーバー起動 (ホットリロード有効: --reload)
uvicorn gozen.server:app --host 127.0.0.1 --port 9000 --reload
```

## 6. 動作確認

別のターミナルを開き（必要なら `source .venv/bin/activate` で仮想環境に入り）、以下を実行して動作を確認します。

### 6-1. ヘルスチェック

```bash
curl http://localhost:9000/api/v1/health
# {"status":"ok", ...} が返ればOK
```

### 6-2. フロー全体の自動検証

付属の検証スクリプトを実行して、御前会議フロー全体（セッション開始〜提案〜裁定〜公文書作成）が動作することを確認します。
このスクリプトは MOCK モードで動作するため、APIキーは不要です。

```bash
python verify_flow.py
```

成功すると `SUCCESS: Full flow verified.` と表示されます。

以上でセットアップは完了です。
