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
    # Merge questions
    base["questions"].extend(addendum.get("questions", []))

    # Merge mechanical features
    base["mechanical_features"].update(
        addendum.get("mechanical_features", {})
    )

    # Merge contributor mappings
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
# Scoring
# -------------------------------------------------
primary_scores, contributor_scores = score_primary_and_contributors(
    module,
    patient_vec
)

primary, secondary = select_dominant(primary_scores, ratio=0.75, max_items=3)
contrib, contrib_secondary = select_dominant(contributor_scores, ratio=0.70, max_items=3)

# -------------------------------------------------
# Output
# -------------------------------------------------
st.header("Biomechanical Summary")

if not primary:
    st.info("Insufficient signal to identify a dominant knee pattern.")
else:
    st.subheader("Dominant knee mechanical pattern")
    st.write(f"**{primary.name}**")
    st.write(pattern_strength(primary_scores))

    # Contributors
    st.subheader("Likely contributing mechanics (upstream / downstream)")
    if contrib:
        st.write(f"**{contrib.name}**")

        cmap = module.get("contributor_mapping", {}).get(
            contrib.primary_feature, {}
        )
        if cmap:
            st.markdown("**Why it matters**")
            st.write(cmap.get("why_it_matters", ""))

            st.markdown("**Likely contributors**")
            for c in cmap.get("likely_contributors", []):
                st.write(f"• {c}")

        if contrib_secondary:
            st.markdown("**Other possible contributors**")
            for c in contrib_secondary:
                st.write(f"• {c.name}")
    else:
        st.write("No strong hip or ankle contributors identified.")

    # Clinician prompts
    if clinician_mode:
        st.subheader("What would help differentiate further")
        patt = next(
            (p for p in module["patterns"]["primary"]
             if p["id"] == primary.pattern_id),
            None
        )
        if patt:
            for d in patt.get("differentiators", []):
                st.write(f"• {d}")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.info(
    "This tool supports biomechanical reasoning and guided self-management. "
    "It does not provide a medical diagnosis. Seek professional assessment "
    "if symptoms are severe, progressive, or concerning."
)
