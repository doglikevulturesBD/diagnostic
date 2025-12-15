import streamlit as st
from utils.loaders import load_json
from engine.mechanics import build_feature_vector, add_feature_updates, score_patterns, contributors, pattern_strength


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
                    issues.append(rule.get("message", "Some answers conflict. Please review."))
                    break
    return list(dict.fromkeys(issues))


st.set_page_config(page_title="Knee Mechanics Assistant", layout="centered")
st.title("Knee Mechanics Assistant")
st.caption("Mechanics-first reasoning • pattern-based • clinician-friendly")

mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"
if clinician_mode:
    st.info("Clinician mode enabled — additional probing shown.")

module = load_json("modules/knee_mechanics.json")

feature_names = list(module["mechanical_features"].keys())
patient_vec = build_feature_vector(feature_names)

answers_log = {}

st.markdown("## Questions")
for q in module["questions"]:
    if q.get("clinician_only", False) and not clinician_mode:
        continue

    st.markdown(f"### {q['question']}")
    qid = q["id"]
    answers_log[qid] = []

    if q["type"] == "single_choice":
        ans = st.radio("", list(q["answers"].keys()), key=qid)
        answers_log[qid].append(ans)
        add_feature_updates(patient_vec, q["answers"].get(ans, {}))

    elif q["type"] == "multi_choice":
        selected = st.multiselect("", list(q["answers"].keys()), key=qid)
        answers_log[qid].extend(selected)
        for a in selected:
            add_feature_updates(patient_vec, q["answers"].get(a, {}))

# Safety and consistency
st.markdown("## Safety & Consistency")
contr = collect_contradictions(module, answers_log)
if contr:
    st.warning("Some answers appear inconsistent:\n\n" + "\n".join([f"• {m}" for m in contr]))

rf = collect_triggers(module, answers_log)
if rf:
    urgent = [x for x in rf if x.get("severity") == "urgent"]
    priority = [x for x in rf if x.get("severity") == "priority"]
    if urgent:
        st.error("⚠️ Red flags (urgent):\n\n" + "\n".join([f"• {x.get('message','')}" for x in urgent]))
    if priority:
        st.warning("⚠️ Red flags (priority):\n\n" + "\n".join([f"• {x.get('message','')}" for x in priority]))

# Score patterns
scores = score_patterns(module, patient_vec)
primary, secondary = contributors(scores, ratio=0.75, max_secondary=3)

st.markdown("## Mechanics Summary")

if not primary:
    st.info("Not enough information to identify a dominant mechanical pattern.")
else:
    st.subheader("Most likely dominant mechanical pattern")
    st.write(f"**{primary.name}**")
    st.write(pattern_strength(scores))

    # Map to tissues/labels
    primary_feat = next((p for p in module["patterns"] if p["id"] == primary.pattern_id), None)
    if primary_feat:
        feat_key = primary_feat.get("primary_feature")
        mapping = module["tissue_mapping"].get(feat_key, {})
        st.markdown("**Likely structures involved**")
        for s in mapping.get("likely_structures", []):
            st.write(f"• {s}")
        st.markdown("**Common clinical labels**")
        for lbl in mapping.get("common_labels", []):
            st.write(f"• {lbl}")

    if secondary:
        st.subheader("Other plausible contributing patterns")
        for s in secondary:
            st.write(f"• {s.name}")

    # Differentiators (clinician prompt)
    if clinician_mode and primary_feat:
        st.subheader("What would help differentiate further")
        for d in primary_feat.get("differentiators", []):
            st.write(f"• {d}")

st.info(
    "This tool supports reasoning and self-management guidance. It does not provide a medical diagnosis. "
    "Seek professional assessment if symptoms are severe, worsening, or red flags are present."
)
