import streamlit as st

from utils.loaders import load_module
from engine.inference import initialise_scores, apply_answer
from engine.normalise import normalise
from engine.explain import generate_explanation
from ui.components import section, result_bar, disclaimer


# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Physio Diagnostic Assistant",
    layout="centered"
)

# -------------------------------------------------
# Load global styles (I-TYPE compatible)
# -------------------------------------------------
with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.title("Physio Diagnostic Assistant")
st.caption("Clinical decision support • Explainable • Bayesian-ready")

# -------------------------------------------------
# Body part selection (expand later)
# -------------------------------------------------
body_part = st.selectbox(
    "Where is the primary pain?",
    ["knee"]
)

module = load_module(body_part)
conditions = module["conditions"]

# -------------------------------------------------
# Initialise inference engine
# -------------------------------------------------
scores, trace = initialise_scores(conditions)

# -------------------------------------------------
# Question loop
# -------------------------------------------------
for q in module["questions"]:
    section(q["question"])

    if q["type"] == "single_choice":
        answer = st.radio(
            label="",
            options=list(q["answers"].keys()),
            key=q["id"]
        )

        scores, trace = apply_answer(
            scores=scores,
            trace=trace,
            question=q["question"],
            answer=answer,
            answer_weights=q["answers"][answer]
        )

    elif q["type"] == "multi_choice":
        answers = st.multiselect(
            label="",
            options=list(q["answers"].keys()),
            key=q["id"]
        )

        for a in answers:
            scores, trace = apply_answer(
                scores=scores,
                trace=trace,
                question=q["question"],
                answer=a,
                answer_weights=q["answers"][a]
            )

# -------------------------------------------------
# Normalise results
# -------------------------------------------------
results = normalise(scores)

# -------------------------------------------------
# Confidence band helper
# -------------------------------------------------
def confidence_band(probability: float) -> str:
    if probability >= 70:
        return "High confidence"
    elif probability >= 40:
        return "Moderate confidence"
    else:
        return "Low confidence"


# -------------------------------------------------
# Results display
# -------------------------------------------------
section("Most Likely Conditions")

sorted_results = sorted(
    results.items(),
    key=lambda x: -x[1]
)

for condition, probability in sorted_results:
    band = confidence_band(probability)

    # Result bar
    result_bar(condition, probability)

    # Confidence label
    if band == "High confidence":
        st.success(band)
    elif band == "Moderate confidence":
        st.warning(band)
    else:
        st.info(band)

    # Explanation
    with st.expander("Why this result?"):
        st.write(generate_explanation(condition, trace))

# -------------------------------------------------
# Disclaimer
# -------------------------------------------------
disclaimer()
