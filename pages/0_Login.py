import streamlit as st
import service
from core.layout import apply_portal_theme

st.set_page_config(page_title="Login", layout="wide", initial_sidebar_state="collapsed")

# 로그인 페이지는 왼쪽(기본 사이드바/Pages 목록) 숨김
apply_portal_theme(hide_pages_sidebar_nav=True, hide_sidebar=True, active_menu="")

# 세션 기본값
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)              # "ADMIN" | "EMPLOYEE"
st.session_state.setdefault("employee_id", None)
st.session_state.setdefault("employee_info", None)

# 이미 로그인 되어 있으면 바로 이동
if st.session_state.logged_in:
    if st.session_state.role == "ADMIN":
        st.switch_page("pages/admin.py")
    else:
        st.switch_page("pages/employee.py")

# "처음 접속하면 모달 자동 오픈" 플래그
st.session_state.setdefault("_login_modal_open", True)

# 배경(페이지 자체는 아무것도 안 보이게)
st.markdown(
    """
    <style>
    /* 상단 Streamlit 헤더/푸터 숨김 */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 본문 여백 최소화 + 흰 화면 유지 */
    .block-container { padding-top: 0.5rem; }

    /* 로그인 페이지는 본문 컨텐츠를 거의 비워두고 싶으면 아래처럼 */
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 중앙 모달: st.dialog 사용 ---
@st.dialog("로그인")
def login_modal():
    st.caption("아이디/비밀번호로 로그인 (관리자: admin, 직원: HS001~HS003)")

    login_id = st.text_input(
        "아이디",
        value="",
        placeholder="아이디 입력",
        key="login_id_input",
    )
    pw = st.text_input(
        "비밀번호",
        value="",
        type="password",
        placeholder="패스워드 입력",
        key="pw_input",
    )

    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        if st.button("로그인", type="primary", use_container_width=True):
            info = service.login_account((login_id or "").strip(), (pw or "").strip())
            if not info:
                st.error("로그인 정보가 올바르지 않습니다.")
                return

            st.session_state.logged_in = True
            st.session_state.role = info["role"]

            if info["role"] == "ADMIN":
                st.session_state.employee_id = None
                st.session_state.employee_info = None
                st.session_state._login_modal_open = False
                st.switch_page("pages/admin.py")
            else:
                emp = info["employee"]
                st.session_state.employee_id = emp["employeeId"]
                st.session_state.employee_info = emp
                st.session_state._login_modal_open = False
                st.switch_page("pages/employee.py")

    with c2:
        if st.button("초기화", use_container_width=True):
            st.session_state["login_id_input"] = ""
            st.session_state["pw_input"] = ""
            st.rerun()


# 페이지 로드시 모달을 “자동”으로 한번 띄우기
if st.session_state._login_modal_open:
    login_modal()

# 모달이 닫혀도 페이지에는 아무것도 안 보이도록(원하면 안내문 정도만)
st.write("")
