def initialise_scores(conditions: dict):
    """
    Initialise condition scores.
    Priors are ignored for now, but structure supports them.
    """
    return {cond: 1.0 for cond in conditions}


def apply_answer(scores: dict, answer_weights: dict):
    """
    Multiply condition scores by answer weights.
    """
    for condition, weight in answer_weights.items():
        if condition in scores:
            scores[condition] *= weight
    return scores

