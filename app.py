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
        trig = rf.get("trigger", {})
        qid = trig.get("question_id")
        ans = trig.get("answer")
        if qid in answers_log and ans in answers_log[qid]:
            hits.append(rf)
    return hits

def collect_contradictions(module, answers_log):
    issues = []
    for rule in module.get("contradiction_rules", []):
        cond = rule.get("if", {})
        qid = cond.get("question_id")
        ans = cond.get("answer")
        if qid in answers_log and ans in answers_log[qid]:
            for conflict in rule.get("conflicts_with", []):
                cqid = conflict.get("question_id")
                cans = conflict.get("answer")
                if cqid in answers_log and cans in answers_log[cqid]:
                    issues.append(rule.get("message", "Some answers conflict."))
                    break
    return list(set(issues))

st.set_page_config(page_title="Knee Biomechanics Assistant", layout="centered")
st.title("Knee Biomechanics Assistant")
st.caption("Biomechanics-first reasoning • knee patterns + hip/ankle/foot contributors")

mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = (mode == "Clinician")
if clinician_mode:
    st.info("Clinician mode enabled — additional probing shown.")

module = load_json("modules/knee_mechanics.json")

feature_names = list(module["mechanical_features"].keys())
patient_vec = build_feature_vector(feature_names)
answers_log = {}

st.header("Questions")
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

st.header("Safety & Consistency")
contr = collect_contradictions(module, answers_log)
for m in contr:
    st.warning(m)

rf = collect_triggers(module, answers_log)
urgent = [x for x in rf if x.get("severity") == "urgent"]
priority = [x for x in rf if x.get("severity") == "priority"]
if urgent:
    st.error("⚠️ Red flags (urgent):\n\n" + "\n".join([f"• {x.get('message','')}" for x in urgent]))
if priority:
    st.warning("⚠️ Red flags (priority):\n\n" + "\n".join([f"• {x.get('message','')}" for x in priority]))

primary_scores, contributor_scores = score_primary_and_contributors(module, patient_vec)
primary, secondary = select_dominant(primary_scores, ratio=0.75, max_items=3)
contrib, contrib_secondary = select_dominant(contributor_scores, ratio=0.70, max_items=3)

st.header("Biomechanics Summary")

if not primary:
    st.info("Not enough information to identify a dominant mechanical knee pattern.")
else:
    st.subheader("Dominant knee mechanical pattern")
    st.write(f"**{primary.name}**")
    st.write(pattern_strength(primary_scores))

    if primary.primary_feature:
        mapping = module.get("tissue_mapping", {}).get(primary.primary_feature, {})
        if mapping:
            st.markdown("**Likely structures involved**")
            for s in mapping.get("likely_structures", []):
                st.write(f"• {s}")
            st.markdown("**Common clinical labels**")
            for lbl in mapping.get("common_labels", []):
                st.write(f"• {lbl}")

    if secondary:
        st.subheader("Other plausible knee patterns")
        for s in secondary:
            st.write(f"• {s.name}")

    st.subheader("Likely contributing mechanics (hip / ankle / foot)")
    if contrib and contrib.score > 0:
        st.write(f"**{contrib.name}**")
        cmap = module.get("contributor_mapping", {}).get(contrib.primary_feature, {})
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
        st.write("• No strong contributors identified from this questionnaire.")

    if clinician_mode:
        st.subheader("What would help differentiate further (clinician prompt)")
        patt = next((p for p in module["patterns"]["primary"] if p["id"] == primary.pattern_id), None)
        if patt:
            for d in patt.get("differentiators", []):
                st.write(f"• {d}")

st.info(
    "This tool supports biomechanics-based reasoning and self-management guidance. "
    "It does not provide a medical diagnosis. Seek professional assessment if symptoms are severe, worsening, or red flags are present."
)
