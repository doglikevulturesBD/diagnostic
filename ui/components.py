import streamlit as st


def section(title: str):
    st.markdown(f"### {title}")


def result_bar(label: str, value: float):
    st.write(f"**{label}** — {value}%")
    st.progress(min(value / 100, 1.0))


def disclaimer():
    st.info(
        "This tool provides clinical decision support only and does not "
        "replace professional diagnosis or assessment."
    )

