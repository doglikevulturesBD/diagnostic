import streamlit as st
from utils.loaders import load_module
from engine.inference import initialise_scores, apply_answer
from engine.normalise import normalise
from ui.components import section, result_bar, disclaimer


# --- Page config ---
st.set_page_config(
    page_title="Physio Diagnostic Assistant",
    layout="centered"
)

# --- Load CSS ---
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# --- App title ---
st.title("Physio Diagnostic Assistant")
st.caption("Clinical decision support • Rule-based • Bayesian-ready")

# --- Body part selection ---
body_part = st.selectbox(
    "Where is the primary pain?",
    ["knee"]  # expand later
)

module = load_module(body_part)
conditions = module["conditions"]

# --- Initialise inference ---
scores = initialise_scores(conditions)

# --- Questions ---
for q in module["questions"]:
    section(q["question"])

    if q["type"] == "single_choice":
        answer = st.radio(
            label="",
            options=list(q["answers"].keys()),
            key=q["id"]
        )
        scores = apply_answer(scores, q["answers"][answer])

    elif q["type"] == "multi_choice":
        answers = st.multiselect(
            label="",
            options=list(q["answers"].keys()),
            key=q["id"]
        )
        for a in answers:
            scores = apply_answer(scores, q["answers"][a])

# --- Results ---
section("Most Likely Conditions")

results = normalise(scores)

for condition, probability in sorted(
    results.items(), key=lambda x: -x[1]
):
    result_bar(condition, probability)

disclaimer()


