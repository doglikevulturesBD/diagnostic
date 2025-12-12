def initialise_scores(conditions: dict):
    scores = {cond: 1.0 for cond in conditions}
    trace = {cond: [] for cond in conditions}
    return scores, trace


def apply_answer(scores: dict, trace: dict, question: str, answer: str, answer_weights: dict):
    for condition, weight in answer_weights.items():
        if condition in scores:
            scores[condition] *= weight
            trace[condition].append(
                f"{question} → '{answer}'"
            )
    return scores, trace
