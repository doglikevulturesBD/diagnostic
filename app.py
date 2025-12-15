import streamlit as st
import sys
import os

st.write("Python executable:", sys.executable)
st.write("Working directory:", os.getcwd())
st.write("Files in cwd:", os.listdir())

st.write("Engine exists:", os.path.exists("engine"))
st.write("Engine contents:", os.listdir("engine") if os.path.exists("engine") else "NO ENGINE DIR")

st.write("Utils exists:", os.path.exists("utils"))
st.write("Utils contents:", os.listdir("utils") if os.path.exists("utils") else "NO UTILS DIR")

st.stop()

)

