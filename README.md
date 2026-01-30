# Project GOZEN 御前会議

🏯 海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、最高のエンジニアリング決定を導くマルチエージェントシステム。

## コンセプト

> 「陸軍として海軍の提案に反対である」

意図的な敵対的協業（Adversarial Collaboration）でグループシンクを防止する。

- **海軍参謀（Claude）**: 理想・論理・スケーラビリティ重視
- **陸軍参謀（Gemini）**: 現実・実装・運用負荷重視
- **国家元首（人間）**: 最終裁定権を持つ

## 階級体系

### 海軍系統（Claude）

| 階級 | モデル | 課金方式 | 並列数 |
|------|--------|----------|--------|
| 海軍参謀 | Opus 4.5 | Pro $20/月 | 1 |
| 提督 | Sonnet 4.5 | API | 1 |
| 艦長 | Sonnet 4.5 | API | 1 |
| **海兵** | Haiku 4.5 | API | ×8 |

### 陸軍系統（Gemini）

| 階級 | モデル | 課金方式 | 並列数 |
|------|--------|----------|--------|
| 陸軍参謀 | Gemini Pro | GCP無料枠 | 1 |
| 士官 | Gemini 2.5 Flash | API | 1 |
| 歩兵 | Gemini 2.5 Flash | API | ×4 |

## インストール

```bash
pip install -r requirements.txt
```

## 使い方

### CLI実行

```bash
# 順次実行（Pro推奨）
python -m gozen.cli --mode sequential tasks/sample_arch001.yaml

# 並列実行（Max 5x推奨）
python -m gozen.cli --mode parallel --plan max5x tasks/sample_arch001.yaml

# インタラクティブモード
python -m gozen.cli --interactive
```

### Pythonから

```python
import asyncio
from gozen import GozenOrchestrator

orchestrator = GozenOrchestrator()
task = {
    "task_id": "TASK-001",
    "mission": "Minecraftサーバーのインフラ構築",
    "requirements": ["k3s", "MinIO", "自動化"]
}

result = asyncio.run(orchestrator.execute_full_cycle(task))
```

## ゼロトラスト原則

- 「検証なき信頼は敗北への道」（海軍）
- 「信用するな、検証せよ」（陸軍）
- 相互監査：海軍成果物 → 陸軍監査 / 陸軍成果物 → 海軍監査

## ディレクトリ構成

```
project-gozen/
├── gozen/
│   ├── __init__.py           # パッケージ初期化
│   ├── cli.py                # CLIエントリポイント
│   ├── config.py             # 階級×モデル設定
│   ├── character.py          # 口調テンプレート
│   ├── council_mode.py       # 会議ループ
│   ├── gozen_orchestrator.py # オーケストレータ
│   ├── api_client.py         # API呼び出し
│   ├── audit.py              # 監査モジュール
│   │
│   ├── kaigun_sanbou/        # 海軍系統
│   │   ├── __init__.py       # 海軍参謀
│   │   └── teitoku/          # 提督
│   │       └── kancho/       # 艦長
│   │           └── kaihei/   # 海兵×8
│   │
│   └── rikugun_sanbou/       # 陸軍系統
│       ├── __init__.py       # 陸軍参謀
│       └── shikan/           # 士官
│           └── hohei/        # 歩兵×4
│
├── queue/                    # YAMLキュー
│   ├── proposal/
│   ├── objection/
│   ├── decision/
│   └── execution/
│
├── tasks/                    # タスク定義
└── audit/                    # 監査レポート
```

## 月額コスト試算

- Pro サブスク: $20
- 提督/艦長 (Sonnet): $5〜10
- 海兵×8 (Haiku): $10〜20
- 歩兵×4 (Gemini Flash): $5〜10
- **合計: $35〜60/月**

## 哲学

> 「相互監視ではなく背中合わせの死闘」
> 「貴官の綺麗な制服に油染みをつけてやる」
> 「背中は任せたぞ、海軍」

理想と現実の統合・信頼関係・相補的対立を通じて、堅牢な設計が生まれる。

## ライセンス

MIT License

## 作者

tagomori (田籠) - Project GOZEN
