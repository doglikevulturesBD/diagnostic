import sys
from pathlib import Path
import streamlit as st

# -------------------------------------------------
# Ensure local imports always work (Streamlit-safe)
# -------------------------------------------------
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from utils.loaders import load_json
from engine.mechanics import (
    build_feature_vector,
    add_feature_updates,
    score_primary_and_contributors,
    select_dominant,
    pattern_strength
)

# -------------------------------------------------
# Helper: merge two biomechanical modules safely
# -------------------------------------------------
def merge_modules(base, addendum):
    base["questions"].extend(addendum.get("questions", []))
    base["mechanical_features"].update(
        addendum.get("mechanical_features", {})
    )
    base.setdefault("contributor_mapping", {}).update(
        addendum.get("contributor_mapping", {})
    )
    return base

# -------------------------------------------------
# App config
# -------------------------------------------------
st.set_page_config(
    page_title="Knee Biomechanics Assistant",
    layout="centered"
)

st.title("Knee Biomechanics Assistant")
st.caption("Mechanics-first reasoning • knee patterns with hip & ankle contributors")

mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"

if clinician_mode:
    st.info("Clinician mode enabled — advanced probing active.")

# -------------------------------------------------
# Load & compose modules
# -------------------------------------------------
knee_module = load_json("modules/knee_mechanics.json")
cross_joint = load_json("modules/knee_cross_joint_addendum.json")
module = merge_modules(knee_module, cross_joint)

# -------------------------------------------------
# Initialise state
# -------------------------------------------------
feature_names = list(module["mechanical_features"].keys())
patient_vec = build_feature_vector(feature_names)
answers_log = {}

# -------------------------------------------------
# Questionnaire
# -------------------------------------------------
st.header("Assessment Questions")

for q in module["questions"]:
    if q.get("clinician_only", False) and not clinician_mode:
        continue

    st.subheader(q["question"])
    qid = q["id"]
    answers_log[qid] = []

    if q["type"] == "single_choice":
        ans = st.radio("", list(q["answers"].keys()), key=qid)
        answers_log[qid].append(ans)
        add_feature_updates(patient_vec, q["answers"].get(ans, {}))

    elif q["type"] == "multi_choice":
        selected = st.multiselect("", list(q["answers"].keys()), key=qid)
        answers_log[qid] = selected
        for a in selected:
            add_feature_updates(patient_vec, q["answers"].get(a, {}))

# -------------------------------------------------
# Initial scoring
# -------------------------------------------------
primary_scores, contributor_scores = score_primary_and_contributors(
    module,
    patient_vec
)

primary, secondary = select_dominant(primary_scores, ratio=0.75, max_items=3)
contrib, contrib_secondary = select_dominant(contributor_scores, ratio=0.70, max_items=3)


# =================================================
# 🔍 NEW SECTION — EXERCISE AS PROBES (ONLY ADDITION)
# =================================================

st.header("Movement Checks (Exercise Probes)")
st.caption(
    "These movements help confirm or refine the mechanical findings. "
    "Stop if pain is sharp, severe, or concerning."
)

probes = load_json("modules/exercise_probes.json")["exercise_probes"]

for probe in probes:
    st.subheader(probe["name"])
    st.write(probe["instructions"])

    response = st.radio(
        "What best describes your experience?",
        list(probe["responses"].keys()),
        key=f"probe_{probe['id']}"
    )

    add_feature_updates(patient_vec, probe["responses"][response])


# -------------------------------------------------
# Re-score AFTER probes
# -------------------------------------------------
primary_scores, contributor_scores = score_primary_and_contributors(
    module,
    patient_vec
)

contrib, contrib_secondary = select_dominant(
    contributor_scores,
    ratio=0.70,
    max_items=3
)

st.subheader("Refined Mechanical Interpretation")
if contrib:
    st.write(
        f"After movement checks, **{contrib.name}** "
        "remains the most likely contributing factor."
    )
else:
    st.write(
        "Movement checks reduced confidence in major hip or ankle contributors."
    )


# -------------------------------------------------
# Final biomechanical summary (after probes)
# -------------------------------------------------
st.header("Final Biomechanical Summary")

if not primary:
    st.info(
        "Based on your responses and movement checks, there is not enough "
        "consistent signal to identify a dominant knee loading pattern."
    )
else:
    st.subheader("Dominant knee mechanical pattern")
    st.write(f"**{primary.name}**")
    st.write(pattern_strength(primary_scores))

    st.subheader("Likely contributing mechanics")
    if contrib:
        st.write(f"**{contrib.name}**")

        cmap = module.get("contributor_mapping", {}).get(
            contrib.primary_feature, {}
        )
        if cmap:
            st.markdown("**Why this matters**")
            st.write(cmap.get("why_it_matters", ""))

            st.markdown("**Likely contributors**")
            for c in cmap.get("likely_contributors", []):
                st.write(f"• {c}")

        if contrib_secondary:
            st.markdown("**Other possible contributors**")
            for c in contrib_secondary:
                st.write(f"• {c.name}")
    else:
        st.write(
            "Movement checks did not strongly support hip or ankle contribution. "
            "The knee appears to be the primary driver of symptoms."
        )


# -------------------------------------------------
# Footer
# -------------------------------------------------
st.info(
    "This tool supports biomechanical reasoning and guided self-management. "
    "It does not provide a medical diagnosis. Seek professional assessment "
    "if symptoms are severe, progressive, or concerning."
)
