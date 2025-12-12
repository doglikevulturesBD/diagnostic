def normalise(scores: dict):
    total = sum(scores.values())
    if total == 0:
        return {k: 0 for k in scores}

    return {
        k: round((v / total) * 100, 1)
        for k, v in scores.items()
    }

