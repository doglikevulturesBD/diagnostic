from typing import Dict


def normalise(scores: Dict[str, float]) -> Dict[str, float]:
    total = sum(scores.values())
    if total <= 0:
        return {k: 0.0 for k in scores}
    return {k: (v / total) for k, v in scores.items()}
