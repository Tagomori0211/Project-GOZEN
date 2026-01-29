"""
艦長（kancho）- Claude Code

提督の下で、戦術指揮と水兵の統制を担当する。
具体的な作業指示を水兵に与える。
"""

import asyncio
from datetime import datetime
from typing import Literal


class Kancho:
    """
    艦長クラス
    
    役割：
    - 提督からの指令を具体的作業に変換
    - 水兵への詳細指示
    - 品質管理
    """
    
    def __init__(self):
        self.role = "艦長"
        self.superior = "提督"
        self.subordinate = "水兵"
    
    async def execute(
        self,
        subtask: dict,
        mode: Literal['sequential', 'parallel'] = 'sequential'
    ) -> dict:
        """
        サブタスクを実行
        """
        print(f"[艦長] 指令受領: {subtask['name']}")
        
        # 水兵への指示作成
        work_items = self._create_work_items(subtask)
        
        # 水兵に実行させる
        from gozen.kaigun_sanbou.teitoku.kancho.suihei import suihei_main
        
        if mode == 'parallel':
            # 並列実行
            results = await asyncio.gather(*[
                suihei_main.execute(i, item)
                for i, item in enumerate(work_items)
            ])
        else:
            # 順次実行
            results = []
            for i, item in enumerate(work_items):
                result = await suihei_main.execute(i, item)
                results.append(result)
        
        return {
            'subtask_id': subtask['id'],
            'status': 'completed',
            'work_items_count': len(work_items),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_work_items(self, subtask: dict) -> list:
        """作業項目を作成"""
        # サブタスクを具体的な作業に分解
        return [
            {
                'id': f"{subtask['id']}-WORK-001",
                'description': f"{subtask['name']} - 実装",
                'estimated_time': '2h'
            },
            {
                'id': f"{subtask['id']}-WORK-002",
                'description': f"{subtask['name']} - テスト",
                'estimated_time': '1h'
            }
        ]


# モジュールレベル関数
async def execute(subtask: dict, mode: str = 'sequential') -> dict:
    """艦長の実行（モジュールレベル関数）"""
    kancho = Kancho()
    return await kancho.execute(subtask, mode=mode)
