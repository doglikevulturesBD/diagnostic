import sys
from pathlib import Path
import streamlit as st

# -------------------------------------------------
# Ensure local imports always work (Streamlit-safe)
# -------------------------------------------------
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# -------------------------------------------------
# Load custom CSS
# -------------------------------------------------
def load_css(file_name):
    css_path = ROOT / file_name
    if css_path.exists():
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

from utils.loaders import load_json
from engine.mechanics import (
    build_feature_vector,
    add_feature_updates,
    score_primary_and_contributors,
    select_dominant,
    pattern_strength
)

# -------------------------------------------------
# App config
# -------------------------------------------------
st.set_page_config(
    page_title="Knee Biomechanics Assistant",
    layout="centered"
)

# =================================================
# HERO
# =================================================
st.markdown("""
<div class="hero">
<div class="hero-title">Knee Biomechanics Assistant</div>
<div class="hero-sub">
Mechanics-first reasoning • knee patterns with hip & ankle contributors
</div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Mode selection
# -------------------------------------------------
mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"

if clinician_mode:
    st.markdown("""
    <div class="info-tile">
    Clinician mode enabled — advanced probing active.
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# Load & compose modules
# -------------------------------------------------
knee_module = load_json("modules/knee_mechanics.json")
cross_joint = load_json("modules/knee_cross_joint_addendum.json")
def merge_modules(base, addendum):
    base["questions"].extend(addendum.get("questions", []))
    base["mechanical_features"].update(
        addendum.get("mechanical_features", {})
    )
    base.setdefault("contributor_mapping", {}).update(
        addendum.get("contributor_mapping", {})
    )
    return base

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

    st.markdown(f"""
    <div class="question-tile">
        <div class="question-title">{q["question"]}</div>
    </div>
    """, unsafe_allow_html=True)

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
# MOVEMENT CHECKS — EXERCISE PROBES
# =================================================
st.header("Movement Checks")

st.markdown("""
<p>
These movements help confirm or refine the mechanical findings.
Stop if pain is sharp, severe, or concerning.
</p>
""", unsafe_allow_html=True)

probes = load_json("modules/exercise_probes.json")["exercise_probes"]

for probe in probes:
    st.markdown(f"""
    <div class="question-tile">
    <div class="question-title">{probe["name"]}</div>
    <p>{probe["instructions"]}</p>
    </div>
    """, unsafe_allow_html=True)

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

# -------------------------------------------------
# Refined interpretation
# -------------------------------------------------
st.header("Refined Mechanical Interpretation")

if contrib:
    st.markdown(f"""
    <div class="result-tile">
    <p>
    After movement checks, <strong>{contrib.name}</strong>
    remains the most likely contributing factor.
    </p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="result-tile">
    Movement checks reduced confidence in major hip or ankle contributors.
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# Final biomechanical summary
# -------------------------------------------------
st.header("Final Biomechanical Summary")

if not primary:
    st.info(
        "Based on your responses and movement checks, there is not enough "
        "consistent signal to identify a dominant knee loading pattern."
    )
else:
    st.markdown(f"""
    <div class="result-tile">
    <div class="result-highlight">
    Dominant knee mechanical pattern
    </div>
    <p><strong>{primary.name}</strong></p>
    <p>{pattern_strength(primary_scores)}</p>
    </div>
    """, unsafe_allow_html=True)

    if contrib:
        st.markdown(f"""
        <div class="result-tile">
        <div class="result-highlight">
        Likely contributing mechanics
        </div>
        <p><strong>{contrib.name}</strong></p>
        </div>
        """, unsafe_allow_html=True)

        cmap = module.get("contributor_mapping", {}).get(
            contrib.primary_feature, {}
        )
        if cmap:
            st.markdown("""
            <div class="result-tile">
            <strong>Why this matters</strong>
            </div>
            """, unsafe_allow_html=True)

            st.write(cmap.get("why_it_matters", ""))

            st.markdown("""
            <div class="result-tile">
            <strong>Likely contributors</strong>
            </div>
            """, unsafe_allow_html=True)

            for c in cmap.get("likely_contributors", []):
                st.write(f"• {c}")

        if contrib_secondary:
            st.markdown("""
            <div class="result-tile">
            <strong>Other possible contributors</strong>
            </div>
            """, unsafe_allow_html=True)
            for c in contrib_secondary:
                st.write(f"• {c.name}")
    else:
        st.markdown("""
        <div class="result-tile">
        Movement checks did not strongly support hip or ankle contribution.
        The knee appears to be the primary driver of symptoms.
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("""
<div class="footer">
This tool supports biomechanical reasoning and guided self-management.<br>
It does not provide a medical diagnosis and does not replace professional assessment.
</div>
""", unsafe_allow_html=True)
