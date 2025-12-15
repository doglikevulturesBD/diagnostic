import streamlit as st
from utils.loaders import load_json
from engine.mechanics import (
    build_feature_vector,
    add_feature_updates,
    score_primary_and_contributors,
    contributors,
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
                    issues.append(rule.get("message", "Some answers conflict. Please review."))
                    break
    return list(dict.fromkeys(issues))


st.set_page_config(page_title="Knee Mechanics Assistant v2", layout="centered")
st.title("Knee Mechanics Assistant (v2)")
st.caption("Mechanics-first reasoning • primary knee patterns + hip/ankle contributors")

mode = st.radio("Mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"
if clinician_mode:
    st.info("Clinician mode enabled — additional probing shown.")

module = load_json("modules/knee_mechanics_v2.json")

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

# Safety & consistency
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

# Score primary patterns + contributors separately
primary_scores, contributor_scores = score_primary_and_contributors(module, patient_vec)
primary, secondary = contributors(primary_scores, ratio=0.75, max_secondary=3)
top_contrib, secondary_contrib = contributors(contributor_scores, ratio=0.80, max_secondary=3)

st.markdown("## Mechanics Summary")

if not primary:
    st.info("Not enough information to identify a dominant knee mechanical pattern.")
else:
    st.subheader("Dominant knee mechanical pattern")
    st.write(f"**{primary.name}**")
    st.write(pattern_strength(primary_scores))

    # Map to tissues/labels
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

    # Contributors section (hip/ankle)
    st.subheader("Likely contributing mechanics (hip/ankle/foot)")
    if not top_contrib or top_contrib.score <= 0:
        st.write("• No strong contributors identified from this questionnaire.")
    else:
        st.write(f"**{top_contrib.name}**")
        if top_contrib.primary_feature:
            cmap = module.get("contributor_mapping", {}).get(top_contrib.primary_feature, {})
            if cmap:
                st.markdown("**Likely contributors**")
                for c in cmap.get("likely_contributors", []):
                    st.write(f"• {c}")
                st.markdown("**Why it matters**")
                st.write(cmap.get("why_it_matters", ""))

        if secondary_contrib:
            st.markdown("**Other possible contributors**")
            for c in secondary_contrib:
                st.write(f"• {c.name}")

    # Differentiators (clinician)
    if clinician_mode:
        st.subheader("What would help differentiate further (clinician prompt)")
        # Find the full pattern object by id
        patt = None
        for p in module.get("patterns", {}).get("primary", []):
            if p.get("id") == primary.pattern_id:
                patt = p
                break
        if patt:
            for d in patt.get("differentiators", []):
                st.write(f"• {d}")

st.info(
    "This tool supports reasoning and self-management guidance. It does not provide a medical diagnosis. "
    "Seek professional assessment if symptoms are severe, worsening, or red flags are present."
)
