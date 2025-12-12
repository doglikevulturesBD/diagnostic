from typing import Dict, List


def top_reasons(trace: Dict[str, List[str]], condition: str, max_items: int = 5) -> List[str]:
    reasons = trace.get(condition, [])
    # show latest/high-impact reasons first (simple heuristic)
    return reasons[:max_items] if reasons else []

