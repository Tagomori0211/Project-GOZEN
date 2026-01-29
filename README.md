# CLAUDE.md - Project GOZEN Claude Code 設定

## プロジェクト概要

Project GOZEN（御前会議）は、海軍参謀（Claude）と陸軍参謀（Gemini）の
AI同士の対立を通じて、最高のエンジニアリング決定を導くマルチエージェントシステムです。

---
このプロジェクトは以下のリポジトリに触発されて開発されました。

偉大な先人に敬意を。

[yohey-w/multi-agent-shogun](https://github.com/yohey-w/multi-agent-shogun)

### zenn.dev記事

https://zenn.dev/shio_shoppaize/articles/5fee11d03a11a1
---

## 階級体系

```
国家元首（人間）
  │
  ├─ 海軍参謀（Claude） ← 理想・スケーラビリティ
  │   └─ 提督 → 艦長 → 水兵×N
  │
  └─ 陸軍参謀（Gemini） ← 現実・運用・制約
      └─ 士官 → 歩兵×N
```

---

## 対立フレーム

### 海軍参謀（Claude）の立場

- **重視**: 理想、論理、スケーラビリティ
- **傾向**: 完全自動化、将来を見据えた設計
- **リスク**: 過剰設計、コスト高

### 陸軍参謀（Gemini）の立場

- **重視**: 現実、運用、制約適応
- **傾向**: 段階的アプローチ、KISS原則
- **リスク**: 将来の拡張性不足

### 対立の目的

両者の対立から、単独AIでは生まれない「折衷案」を導出する。
グループシンク（全員Yes）を構造的に防ぐ。

---

## ディレクトリ構成

```
project-gozen/
├── gozen/
│   ├── kaigun_sanbou/     # 海軍参謀
│   │   └── teitoku/       # └─ 提督
│   │       └── kancho/    #     └─ 艦長
│   │           └── suihei/#         └─ 水兵
│   │
│   └── rikugun_sanbou/    # 陸軍参謀
│       └── shikan/        # └─ 士官
│           └── hohei/     #     └─ 歩兵
│
├── queue/                 # YAML通信キュー
│   ├── proposal/          # 海軍提案
│   ├── objection/         # 陸軍異議
│   ├── decision/          # 国家元首裁定
│   └── execution/         # 実行指令
│
└── status/                # 進捗ダッシュボード
```

---

## 実行モード

### 順次実行（Pro推奨）

```bash
python gozen/cli.py --mode sequential task.yaml
```

- API消費を最小化
- デバッグしやすい
- 開発時に推奨

### 並列実行（Max 5x推奨）

```bash
python gozen/cli.py --mode parallel --plan max5x task.yaml
```

- asyncio.gatherで高速化
- デッドライン迫る時に推奨
- 大量タスクに効果的

---

## 環境変数

```bash
# Gemini API（陸軍用）
export GCP_PROJECT_ID="your-project-id"
export GCP_LOCATION="us-central1"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

---

## 通信プロトコル

全てYAML形式でキューに保存:

1. `queue/proposal/` - 海軍参謀の提案
2. `queue/objection/` - 陸軍参謀の異議
3. `queue/decision/` - 国家元首の裁定
4. `queue/execution/` - 実行指令

---

## 重要な原則

1. **国家元首が最終決定** - AIは参謀に過ぎない
2. **対立は建設的** - 敵ではなく背中を任せる仲間
3. **記録は全てYAML** - 決定履歴を追跡可能
4. **段階的アプローチ** - 過剰設計を避ける

---

## 参考資料

- おしおさんの記事 [multi-agent-shogun](https://zenn.dev/shio_shoppaize/articles/5fee11d03a11a1)（tmux+YAML統制）
- Pixivミーム「陸軍として海軍の提案に反対である」
- https://dic.pixiv.net/a/陸軍として海軍の提案に反対である
