import streamlit as st
from utils.loaders import load_module
from engine.inference import initialise_scores, apply_answer
from engine.normalise import normalise

st.title("Physio Diagnostic Assistant")

body_part = st.selectbox(
    "Where is the pain?",
    ["Knee", "Ankle", "Shoulder"]
)

module = load_module(body_part.lower())
conditions = module["conditions"].keys()

scores = initialise_scores(conditions)

for q in module["questions"]:
    st.subheader(q["question"])

    if q["type"] == "single_choice":
        answer = st.radio("", list(q["answers"].keys()))
        scores = apply_answer(scores, q["answers"][answer])

    if q["type"] == "multi_choice":
        answers = st.multiselect("", list(q["answers"].keys()))
        for a in answers:
            scores = apply_answer(scores, q["answers"][a])

results = normalise(scores)

st.subheader("Most Likely Conditions")
for cond, prob in sorted(results.items(), key=lambda x: -x[1]):
    st.write(f"**{cond}**: {prob}%")

