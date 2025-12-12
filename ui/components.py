import streamlit as st


def section(title: str):
    st.markdown(f"### {title}")


def disclaimer(mode: str):
    if mode == "Patient":
        st.info(
            "This tool supports clinical reasoning and does not provide a medical diagnosis. "
            "If symptoms are severe, worsening, or concerning, seek professional assessment."
        )
    else:
        st.info(
            "Clinical decision support only. Not a diagnosis. Use alongside examination, "
            "clinical judgement, and investigations where indicated."
        )
