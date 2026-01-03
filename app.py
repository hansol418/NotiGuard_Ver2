import streamlit as st
from core.db import init_db
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="그룹웨어 데모", layout="wide")

init_db()

# 세션 기본값
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)              # "ADMIN" | "EMPLOYEE"
st.session_state.setdefault("employee_id", None)
st.session_state.setdefault("employee_info", None)

# 무조건 로그인 페이지로 시작
st.switch_page("pages/0_Login.py")
