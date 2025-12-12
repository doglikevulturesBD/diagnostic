from typing import Dict, Tuple, List


def initialise_scores(conditions: Dict) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    scores = {cond: 1.0 for cond in conditions.keys()}
    trace = {cond: [] for cond in conditions.keys()}
    return scores, trace


def apply_answer(
    scores: Dict[str, float],
    trace: Dict[str, List[str]],
    question_id: str,
    question_text: str,
    answer_text: str,
    answer_weights: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    """
    Multiplicative update (Bayesian-ready).
    Stores human-readable evidence per condition for explainability.
    """
    for condition, weight in answer_weights.items():
        if condition in scores:
            scores[condition] *= float(weight)
            trace[condition].append(f"{question_text} → {answer_text}")
    return scores, trace

