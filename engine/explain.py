def generate_explanation(condition: str, trace: dict):
    reasons = trace.get(condition, [])

    if not reasons:
        return "This condition remains a possibility based on general symptom patterns."

    explanation = (
        "This condition is suggested based on the following factors:\n"
    )

    for r in reasons:
        explanation += f"• {r}\n"

    return explanation
