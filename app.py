import streamlit as st
from utils.loaders import load_json
from engine.mechanics import (
    build_feature_vector,
    add_feature_updates,
    score_primary_and_contributors,
    select_dominant,
    pattern_strength
)

def collect_triggers(module, answers_log):
    hits = []
    for rf in module.get("red_flags", []):
        trig = rf["trigger"]
        if trig["question_id"] in answers_log and trig["answer"] in answers_log[trig["question_id"]]:
            hits.append(rf)
    return hits


def collect_contradictions(module, answers_log):
    issues = []
    for rule in module.get("contradiction_rules", []):
        cond = rule["if"]
        if cond["question_id"] in answers_log and cond["answer"] in answers_log[cond["question_id"]]:
            for c in rule["conflicts_with"]:
                if c["question_id"] in answers_log and c["answer"] in answers_log[c["question_id"]]:
                    issues.append(rule["message"])
    return list(set(issues))


st.set_page_config("Knee Mechanics Assistant", layout="centered")
st.title("Knee Mechanics Assistant")
st.caption("Mechanics-first reasoning • knee patterns with hip/ankle contributors")

mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"

module = load_json("modules/knee_mechanics.json")

features = list(module["mechanical_features"].keys())
patient_vec = build_feature_vector(features)
answers_log = {}

st.header("Questions")
for q in module["questions"]:
    if q.get("clinician_only") and not clinician_mode:
        continue

    st.subheader(q["question"])
    answers_log[q["id"]] = []

    if q["type"] == "single_choice":
        ans = st.radio("", list(q["answers"].keys()), key=q["id"])
        answers_log[q["id"]].append(ans)
        add_feature_updates(patient_vec, q["answers"][ans])

    else:
        selected = st.multiselect("", list(q["answers"].keys()), key=q["id"])
        answers_log[q["id"]] = selected
        for a in selected:
            add_feature_updates(patient_vec, q["answers"][a])

# Safety
contr = collect_contradictions(module, answers_log)
if contr:
    st.warning("\n".join(contr))

rf = collect_triggers(module, answers_log)
for r in rf:
    st.error(r["message"])

# Scoring
primary_scores, contributor_scores = score_primary_and_contributors(module, patient_vec)
primary, secondary = select_dominant(primary_scores, 0.75, 3)
contrib, contrib_secondary = select_dominant(contributor_scores, 0.7, 3)

st.header("Mechanical Summary")

if primary:
    st.subheader(primary.name)
    st.write(pattern_strength(primary_scores))

    mapping = module["tissue_mapping"].get(primary.primary_feature, {})
    for s in mapping.get("likely_structures", []):
        st.write("•", s)

    if secondary:
        st.subheader("Other plausible knee patterns")
        for s in secondary:
            st.write("•", s.name)

    st.subheader("Likely contributors")
    if contrib:
        st.write(contrib.name)
    else:
        st.write("No strong contributors identified.")

st.info("This tool supports clinical reasoning and self-management guidance. It does not provide a diagnosis.")
