"""
Project GOZEN - 御前会議オーケストレーター

海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、
最高のエンジニアリング決定を導くマルチエージェントシステム。
"""

import asyncio
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

# 各モジュールのインポート
from gozen.kaigun_sanbou import create_proposal as kaigun_create_proposal
from gozen.rikugun_sanbou import create_objection as rikugun_create_objection


class GozenOrchestrator:
    """
    御前会議統括クラス
    
    国家元首（人間）の裁定の下、
    海軍参謀と陸軍参謀の対立を調停する。
    """
    
    def __init__(
        self,
        default_mode: Literal['sequential', 'parallel'] = 'sequential',
        plan: Literal['pro', 'max5x', 'max20x'] = 'pro'
    ):
        self.mode = default_mode
        self.plan = plan
        self.queue_dir = Path(__file__).parent.parent / 'queue'
        self.status_dir = Path(__file__).parent.parent / 'status'
        
        # キューディレクトリの確認
        for subdir in ['proposal', 'objection', 'decision', 'execution']:
            (self.queue_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    async def execute_full_cycle(self, task: dict) -> dict:
        """
        御前会議の完全サイクルを実行
        
        1. 国家元首からのタスク受領
        2. 海軍参謀が提案作成
        3. 陸軍参謀が異議申し立て
        4. 国家元首の裁定待ち
        5. 実行部隊への指令
        """
        task_id = task.get('task_id', f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        print(f"\n🏯 御前会議開始: {task_id}")
        print("=" * 60)
        
        # Step 1: 海軍参謀の提案
        print("\n🌊 [海軍参謀] 提案作成中...")
        proposal = await kaigun_create_proposal(task)
        self._save_to_queue('proposal', task_id, proposal)
        print(f"   提案完了: {proposal.get('title', 'N/A')}")
        
        # Step 2: 陸軍参謀の異議
        print("\n🪖 [陸軍参謀] 異議検討中...")
        objection = await rikugun_create_objection(task, proposal)
        self._save_to_queue('objection', task_id, objection)
        print(f"   異議完了: {objection.get('title', 'N/A')}")
        
        # Step 3: 国家元首の裁定待ち
        print("\n👑 [国家元首] 裁定をお待ちしています...")
        print("-" * 60)
        print("【海軍の主張】")
        print(f"  {proposal.get('summary', 'N/A')}")
        print("\n【陸軍の異議】")
        print(f"  {objection.get('summary', 'N/A')}")
        print("-" * 60)
        
        # 裁定の入力
        decision = await self._wait_for_decision(task_id, proposal, objection)
        self._save_to_queue('decision', task_id, decision)
        
        # Step 4: 実行指令
        if decision.get('approved'):
            print("\n⚔️ [実行部隊] 指令開始...")
            execution_result = await self._execute_orders(decision, task)
            self._save_to_queue('execution', task_id, execution_result)
            return {
                'status': 'completed',
                'task_id': task_id,
                'decision': decision,
                'result': execution_result
            }
        else:
            return {
                'status': 'rejected',
                'task_id': task_id,
                'decision': decision,
                'result': None
            }
    
    async def _wait_for_decision(
        self,
        task_id: str,
        proposal: dict,
        objection: dict
    ) -> dict:
        """国家元首の裁定を待つ"""
        print("\n選択肢:")
        print("  [1] 海軍案を採択")
        print("  [2] 陸軍案を採択")
        print("  [3] 統合案を作成")
        print("  [4] 却下")
        
        # 実際の運用ではinput()を使用
        # ここではデモ用にデフォルト値を返す
        choice = input("\n裁定を入力 (1-4): ").strip()
        
        decision_map = {
            '1': {'approved': True, 'adopted': 'kaigun', 'content': proposal},
            '2': {'approved': True, 'adopted': 'rikugun', 'content': objection},
            '3': {'approved': True, 'adopted': 'integrated', 'content': self._integrate(proposal, objection)},
            '4': {'approved': False, 'adopted': None, 'content': None}
        }
        
        decision = decision_map.get(choice, decision_map['4'])
        decision['task_id'] = task_id
        decision['timestamp'] = datetime.now().isoformat()
        
        return decision
    
    def _integrate(self, proposal: dict, objection: dict) -> dict:
        """海軍案と陸軍案の統合"""
        return {
            'title': '統合案',
            'kaigun_elements': proposal.get('key_points', []),
            'rikugun_elements': objection.get('key_points', []),
            'summary': '海軍の理想と陸軍の現実を統合した折衷案'
        }
    
    async def _execute_orders(self, decision: dict, task: dict) -> dict:
        """実行部隊への指令"""
        adopted = decision.get('adopted')
        
        if adopted == 'kaigun':
            # 海軍ルート: 提督 → 艦長 → 水兵
            from gozen.kaigun_sanbou.teitoku import teitoku_main
            return await teitoku_main.execute(decision, task, mode=self.mode)
        
        elif adopted == 'rikugun':
            # 陸軍ルート: 士官 → 歩兵
            from gozen.rikugun_sanbou.shikan import shikan_main
            return await shikan_main.execute(decision, task, mode=self.mode)
        
        else:
            # 統合案: 両ルート並列
            from gozen.kaigun_sanbou.teitoku import teitoku_main
            from gozen.rikugun_sanbou.shikan import shikan_main
            
            kaigun_result, rikugun_result = await asyncio.gather(
                teitoku_main.execute(decision, task, mode=self.mode),
                shikan_main.execute(decision, task, mode=self.mode)
            )
            
            return {
                'kaigun_result': kaigun_result,
                'rikugun_result': rikugun_result
            }
    
    def _save_to_queue(self, queue_type: str, task_id: str, content: dict):
        """キューにYAMLで保存"""
        filepath = self.queue_dir / queue_type / f"{task_id}.yaml"
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False)


# === 順次実行と並列実行 ===

async def execute_suihei_sequential(tasks: list) -> list:
    """
    水兵の順次実行（Pro推奨）
    
    デバッグしやすく、API消費を最小化
    """
    from gozen.kaigun_sanbou.teitoku.kancho.suihei import suihei_main
    
    results = []
    for i, task in enumerate(tasks):
        print(f"[順次] 水兵{i+1} 実行中...")
        result = await suihei_main.execute(i, task)
        results.append(result)
    return results


async def execute_hohei_parallel(tasks: list) -> list:
    """
    歩兵の並列実行（Max 5x推奨）
    
    asyncio.gatherで高速化
    """
    from gozen.rikugun_sanbou.shikan.hohei import hohei_main
    
    print(f"[並列] 歩兵×{len(tasks)} 同時実行（Gemini API）...")
    coros = [
        hohei_main.execute(i, task) 
        for i, task in enumerate(tasks)
    ]
    return await asyncio.gather(*coros)


if __name__ == '__main__':
    # テスト用
    orchestrator = GozenOrchestrator()
    
    test_task = {
        'task_id': 'TEST-001',
        'mission': 'Minecraftサーバーのインフラ構築',
        'requirements': ['k3s', 'MinIO', '自動化']
    }
    
    asyncio.run(orchestrator.execute_full_cycle(test_task))
