import streamlit as st

from utils.loaders import load_module
from engine.inference import initialise_scores, apply_answer
from engine.normalise import normalise
from engine.explain import top_reasons
from engine.reasoning import rank_conditions, determine_contributors, dominance_label
from ui.components import section, disclaimer


def collect_triggers(module, answers_log):
    """Evaluate red flags from module.red_flags."""
    triggered = []
    for rf in module.get("red_flags", []):
        trig = rf.get("trigger", {})
        qid = trig.get("question_id")
        ans = trig.get("answer")
        if qid in answers_log and ans in answers_log[qid]:
            triggered.append(rf)
    return triggered


def collect_contradictions(module, answers_log):
    """Evaluate contradiction rules from module.contradiction_rules."""
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


st.set_page_config(page_title="Physio Diagnostic Assistant", layout="centered")

with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Physio Diagnostic Assistant")
st.caption("Clinical reasoning assistant • Explainable • Safety-aware • Bayesian-ready (internals)")

mode = st.radio("Select mode:", ["Patient", "Clinician"], horizontal=True)
clinician_mode = mode == "Clinician"
if clinician_mode:
    st.info("Clinician mode enabled — advanced questions and deeper probing shown.")

body_part = st.selectbox("Where is the primary pain?", ["knee"])
module = load_module(body_part)

scores, trace = initialise_scores(module["conditions"])

# Keep a log of selected answers for safety + contradiction logic
# values are stored as list to support multi_choice
answers_log = {}

section("Questions")

for q in module["questions"]:
    if q.get("clinician_only", False) and not clinician_mode:
        continue

    section(q["question"])

    qid = q["id"]
    answers_log[qid] = []

    if q["type"] == "single_choice":
        answer = st.radio("", list(q["answers"].keys()), key=qid)
        answers_log[qid].append(answer)

        weights = q["answers"].get(answer, {})
        scores, trace = apply_answer(
            scores=scores,
            trace=trace,
            question_id=qid,
            question_text=q["question"],
            answer_text=answer,
            answer_weights=weights
        )

    elif q["type"] == "multi_choice":
        selected = st.multiselect("", list(q["answers"].keys()), key=qid)
        answers_log[qid].extend(selected)

        for a in selected:
            weights = q["answers"].get(a, {})
            scores, trace = apply_answer(
                scores=scores,
                trace=trace,
                question_id=qid,
                question_text=q["question"],
                answer_text=a,
                answer_weights=weights
            )

# Safety / contradictions
red_flag_hits = collect_triggers(module, answers_log)
contradictions = collect_contradictions(module, answers_log)

section("Safety & Consistency")

if contradictions:
    st.warning("Some answers appear inconsistent. Please double-check:\n\n" + "\n".join([f"• {m}" for m in contradictions]))

if red_flag_hits:
    urgent = [x for x in red_flag_hits if x.get("severity") == "urgent"]
    priority = [x for x in red_flag_hits if x.get("severity") == "priority"]

    if urgent:
        st.error("⚠️ Potential red flags detected (urgent):\n\n" + "\n".join([f"• {x.get('message','')}" for x in urgent]))
    if priority:
        st.warning("⚠️ Red flag considerations (priority):\n\n" + "\n".join([f"• {x.get('message','')}" for x in priority]))

# Reasoning-based results (no probabilities shown)
norm = normalise(scores)
ranked = rank_conditions(norm)
primary, secondary = determine_contributors(ranked, secondary_ratio=0.70, max_secondary=3)

section("Clinical Reasoning Summary")

if primary[0] == "":
    st.info("Not enough information to generate a shortlist.")
else:
    st.subheader("Most likely primary contributor")
    st.write(f"**{primary[0]}**")

    # Pattern strength label (case-level)
    st.write(dominance_label(ranked))

    # Secondary contributors
    if secondary:
        st.subheader("Other possible contributors")
        for cond, _ in secondary:
            st.write(f"• {cond}")
    else:
        st.subheader("Other possible contributors")
        st.write("• None strongly suggested based on this pattern (differential appears narrower).")

    # Explanations
    st.subheader("Key features supporting this pattern")
    reasons = top_reasons(trace, primary[0], max_items=6)
    if reasons:
        for r in reasons:
            st.write(f"• {r}")
    else:
        st.write("• Pattern derived from combined symptom responses (no single dominant feature).")

    if clinician_mode and secondary:
        st.subheader("What would help differentiate further (clinician prompt)")
        st.write("• Consider targeted examination tests and symptom reproduction patterns.")
        st.write("• Re-check mechanical symptoms (true locking vs catching) and instability quality.")
        st.write("• Consider imaging if red flags present or symptoms persist/worsen.")

disclaimer(mode)


