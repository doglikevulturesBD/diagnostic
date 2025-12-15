from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class PatternScore:
    pattern_id: str
    name: str
    score: float
    primary_feature: Optional[str]


def build_feature_vector(feature_names: List[str]) -> Dict[str, float]:
    return {f: 0.0 for f in feature_names}


def add_feature_updates(vec: Dict[str, float], updates: Dict[str, float]) -> None:
    for k, v in updates.items():
        if k in vec:
            vec[k] += float(v)


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    dot = sum(a[k] * b.get(k, 0.0) for k in a)
    na = sum(v * v for v in a.values())
    nb = sum(v * v for v in b.values())
    if na == 0 or nb == 0:
        return 0.0
    return dot / ((na ** 0.5) * (nb ** 0.5))


def pattern_vector(pattern: dict, features: List[str]) -> Dict[str, float]:
    vec = {f: 0.0 for f in features}
    for src in ("core", "supporting"):
        for k, w in pattern.get(src, {}).items():
            if k in vec:
                vec[k] += float(w)
    return vec


def passes_required_any(pattern: dict, patient_vec: Dict[str, float]) -> bool:
    required = pattern.get("required_any", [])
    if not required:
        return True
    return any(patient_vec.get(f, 0.0) > 0 for f in required)


def exclusion_penalty(pattern: dict, patient_vec: Dict[str, float]) -> float:
    penalty = 0.0
    for feat, weight in pattern.get("exclusion", {}).items():
        if patient_vec.get(feat, 0.0) > 0:
            penalty += float(weight)
    return min(penalty, 0.8)


def score_group(module: dict, patient_vec: Dict[str, float], patterns: List[dict]) -> List[PatternScore]:
    features = list(module["mechanical_features"].keys())
    results: List[PatternScore] = []

    for p in patterns:
        if not passes_required_any(p, patient_vec):
            continue

        pv = pattern_vector(p, features)
        sim = cosine_similarity(patient_vec, pv)
        pen = exclusion_penalty(p, patient_vec)
        score = max(0.0, sim * (1.0 - pen))

        results.append(PatternScore(
            pattern_id=p["id"],
            name=p["name"],
            score=score,
            primary_feature=p.get("primary_feature"),
        ))

    results.sort(key=lambda x: -x.score)
    return results


def score_primary_and_contributors(module: dict, patient_vec: Dict[str, float]):
    primary = score_group(module, patient_vec, module["patterns"]["primary"])
    contributors = score_group(module, patient_vec, module["patterns"]["contributors"])
    return primary, contributors


def select_dominant(scores: List[PatternScore], ratio: float = 0.75, max_items: int = 3):
    if not scores:
        return None, []
    top = scores[0]
    others = [s for s in scores[1:] if s.score >= ratio * top.score][:max_items]
    return top, others


def pattern_strength(scores: List[PatternScore]) -> str:
    if len(scores) < 2:
        return "Pattern strength: Low (limited differentiation)"
    gap = scores[0].score - scores[1].score
    if scores[0].score >= 0.55 and gap >= 0.15:
        return "Pattern strength: Strong"
    if scores[0].score >= 0.40 and gap >= 0.10:
        return "Pattern strength: Moderate"
    return "Pattern strength: Overlapping / mixed"
