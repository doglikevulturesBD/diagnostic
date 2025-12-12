from typing import Dict, List, Tuple


def rank_conditions(norm_scores: Dict[str, float]) -> List[Tuple[str, float]]:
    return sorted(norm_scores.items(), key=lambda x: -x[1])


def determine_contributors(
    ranked: List[Tuple[str, float]],
    secondary_ratio: float = 0.70,
    max_secondary: int = 3
) -> Tuple[Tuple[str, float], List[Tuple[str, float]]]:
    """
    Primary = top ranked.
    Secondary = those within `secondary_ratio` of top score.
    """
    if not ranked:
        return ("", 0.0), []

    primary = ranked[0]
    top_score = primary[1]

    secondary = []
    for cond, score in ranked[1:]:
        if top_score > 0 and score >= secondary_ratio * top_score:
            secondary.append((cond, score))
        if len(secondary) >= max_secondary:
            break

    return primary, secondary


def dominance_label(ranked: List[Tuple[str, float]]) -> str:
    """
    Case-level strength of pattern (NOT per-condition).
    Uses dominance gap + top share; designed for multi-condition differentials.
    """
    if len(ranked) < 2:
        return "Pattern strength: Low (insufficient information)"

    top = ranked[0][1]
    second = ranked[1][1]
    gap = top - second

    # tuned for clinical “shortlist” behaviour
    if top >= 0.45 and gap >= 0.15:
        return "Pattern strength: Strong"
    if top >= 0.35 and gap >= 0.10:
        return "Pattern strength: Moderate"
    return "Pattern strength: Overlapping / Broad differential"
