from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class PatternScore:
    pattern_id: str
    name: str
    score: float
    matched_features: List[Tuple[str, float]]


def build_feature_vector(feature_names: List[str]) -> Dict[str, float]:
    return {f: 0.0 for f in feature_names}


def add_feature_updates(vec: Dict[str, float], updates: Dict[str, float]) -> None:
    for k, v in (updates or {}).items():
        if k in vec:
            vec[k] += float(v)


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    # cosine sim on sparse dicts
    dot = 0.0
    na = 0.0
    nb = 0.0
    for k, av in a.items():
        bv = b.get(k, 0.0)
        dot += av * bv
        na += av * av
    for bv in b.values():
        nb += bv * bv
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / ((na ** 0.5) * (nb ** 0.5))


def pattern_vector(pattern: dict, feature_names: List[str]) -> Dict[str, float]:
    v = {f: 0.0 for f in feature_names}
    for k, w in (pattern.get("core", {}) or {}).items():
        if k in v:
            v[k] += float(w)
    for k, w in (pattern.get("supporting", {}) or {}).items():
        if k in v:
            v[k] += float(w)
    # exclusion is handled separately as penalty
    return v


def passes_required_any(pattern: dict, patient_vec: Dict[str, float]) -> bool:
    req = pattern.get("required_any", []) or []
    if not req:
        return True
    return any(patient_vec.get(f, 0.0) > 0 for f in req)


def exclusion_penalty(pattern: dict, patient_vec: Dict[str, float]) -> float:
    pen = 0.0
    for feat, w in (pattern.get("exclusion", {}) or {}).items():
        if patient_vec.get(feat, 0.0) > 0:
            pen += float(w)
    # clamp to keep sane
    return min(pen, 0.8)


def score_patterns(module: dict, patient_vec: Dict[str, float]) -> List[PatternScore]:
    feats = list(module["mechanical_features"].keys())
    out: List[PatternScore] = []

    for p in module.get("patterns", []):
        if not passes_required_any(p, patient_vec):
            continue

        pv = pattern_vector(p, feats)
        sim = cosine_similarity(patient_vec, pv)
        pen = exclusion_penalty(p, patient_vec)
        final = max(0.0, sim * (1.0 - pen))

        matched = [(f, patient_vec.get(f, 0.0)) for f in feats if patient_vec.get(f, 0.0) > 0]
        out.append(PatternScore(
            pattern_id=p["id"],
            name=p["name"],
            score=final,
            matched_features=matched
        ))

    out.sort(key=lambda x: -x.score)
    return out


def contributors(scores: List[PatternScore], ratio: float = 0.75, max_secondary: int = 3) -> Tuple[PatternScore | None, List[PatternScore]]:
    if not scores:
        return None, []
    primary = scores[0]
    secondaries: List[PatternScore] = []
    for s in scores[1:]:
        if primary.score > 0 and s.score >= ratio * primary.score:
            secondaries.append(s)
        if len(secondaries) >= max_secondary:
            break
    return primary, secondaries


def pattern_strength(scores: List[PatternScore]) -> str:
    if len(scores) < 2:
        return "Pattern strength: Low (insufficient separation)"
    top = scores[0].score
    second = scores[1].score
    gap = top - second
    if top >= 0.55 and gap >= 0.15:
        return "Pattern strength: Strong"
    if top >= 0.40 and gap >= 0.10:
        return "Pattern strength: Moderate"
    return "Pattern strength: Overlapping / broad differential"
