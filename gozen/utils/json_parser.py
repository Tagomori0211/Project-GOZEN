"""
Project GOZEN - Robust JSON/YAML Parser Utility

Provides a multi-stage parser to extract structured data from LLM outputs,
even when they contain conversational text, markdown blocks, or minor syntax errors.
"""

import json
import re
import yaml
from typing import Any, Optional, Dict

def parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """
    LLMの出力から構造化データを極めて堅牢に抽出する。
    
    1. Markdownコードブロック (json, yaml)
    2. ブレースマッチング ({ ... })
    3. YAMLとして全体をパース
    4. Regexによる個別フィールド抽出 (fallback)
    """
    if not text:
        return None

    # 1. Markdownブロック抽出
    for lang in ['json', 'yaml', 'yml', '']:
        pattern = rf"```{lang}\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # JSON試行
            try:
                return json.loads(content)
            except:
                pass
            # YAML試行
            try:
                y = yaml.safe_load(content)
                if isinstance(y, dict): return y
            except:
                pass

    # 2. ブレースマッチング
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        content = brace_match.group(1).strip()
        try:
            return json.loads(content)
        except:
            # ブレース内がYAMLの可能性
            try:
                y = yaml.safe_load(content)
                if isinstance(y, dict): return y
            except:
                pass

    # 3. 全体をYAMLとしてパース
    try:
        # 不要なプレフィックス除去
        cleaned = text.strip()
        for prefix in ["json", "yaml", "result:", "output:"]:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        y = yaml.safe_load(cleaned)
        if isinstance(y, dict): return y
    except:
        pass

    # 4. Regexによる個別フィールド抽出 (最悪のフォールバック)
    result = {}
    fields = ["title", "summary", "decision", "content"]
    for field in fields:
        f_match = re.search(rf'"{field}"\s*:\s*"(.*?)"', text, re.DOTALL)
        if f_match:
            result[field] = f_match.group(1).strip()
    
    return result if result else None
