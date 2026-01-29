"""
士官（shikan）- Gemini API

陸軍参謀の下で、監査とリスク分析を担当する。
歩兵に指令を下し、検証作業を統括する。
"""

import asyncio
from datetime import datetime
from typing import Literal


class Shikan:
    """
    士官クラス
    
    役割：
    - 陸軍参謀の決定を検証タスクに分解
    - 歩兵への指令書作成
    - リスク分析の監督
    """
    
    def __init__(self):
        self.role = "士官"
        self.superior = "陸軍参謀"
        self.subordinate = "歩兵"
    
    async def execute(
        self,
        decision: dict,
        task: dict,
        mode: Literal['sequential', 'parallel'] = 'sequential'
    ) -> dict:
        """
        決定を検証・実行
        """
        print(f"[士官] 指令受領。検証タスク開始...")
        
        # 検証タスク分解
        verification_tasks = self._create_verification_tasks(decision, task)
        
        # 歩兵に指令
        from gozen.rikugun_sanbou.shikan.hohei import hohei_main
        
        if mode == 'parallel':
            results = await asyncio.gather(*[
                hohei_main.execute(i, vtask)
                for i, vtask in enumerate(verification_tasks)
            ])
        else:
            results = []
            for i, vtask in enumerate(verification_tasks):
                result = await hohei_main.execute(i, vtask)
                results.append(result)
        
        return {
            'status': 'completed',
            'verification_count': len(verification_tasks),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_verification_tasks(self, decision: dict, task: dict) -> list:
        """検証タスクを作成"""
        return [
            {
                'id': 'VERIFY-001',
                'name': 'コスト検証',
                'type': 'cost_analysis'
            },
            {
                'id': 'VERIFY-002',
                'name': '運用負荷検証',
                'type': 'operational_load'
            },
            {
                'id': 'VERIFY-003',
                'name': 'リスク分析',
                'type': 'risk_analysis'
            },
            {
                'id': 'VERIFY-004',
                'name': '代替案評価',
                'type': 'alternative_evaluation'
            }
        ]


# モジュールレベル関数
async def execute(decision: dict, task: dict, mode: str = 'sequential') -> dict:
    """士官の実行（モジュールレベル関数）"""
    shikan = Shikan()
    return await shikan.execute(decision, task, mode=mode)
