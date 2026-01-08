import streamlit as st
import service
from core.layout import apply_portal_theme
import extra_streamlit_components as stx
import datetime

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
cookie_manager = stx.CookieManager(key="login_cookie_manager")

# 로그아웃 처리 (다른 페이지에서 넘어온 경우)
if st.session_state.get("logout_clicked"):
    try:
        cookie_manager.delete("user_token")
    except KeyError:
        pass
    st.session_state["logout_clicked"] = False
    import time
    time.sleep(0.5)
    st.rerun()

@st.dialog("로그인")
def login_modal():
    st.caption("아이디/비밀번호로 로그인 (관리자: admin, 직원: HS001~HS003)")
    
    # 초기화
    st.session_state.setdefault("login_error", None)
    
    # 에러 메시지 표시
    if st.session_state.login_error:
        st.error(st.session_state.login_error)
    
    # Form 사용으로 엔터키 지원
    with st.form(key="login_form", clear_on_submit=False):
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
            placeholder="패스워드 입력 후 Enter",
            key="pw_input",
        )
        
        col1, col2 = st.columns([1, 1], gap="small")
        
        with col1:
            submit = st.form_submit_button("로그인", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("초기화", use_container_width=True):
                st.session_state["login_id_input"] = ""
                st.session_state["pw_input"] = ""
                st.session_state.login_error = None
                st.rerun()
        
        # 로그인 처리
        if submit:
            login_id = login_id.strip()
            pw = pw.strip()
            
            if not login_id or not pw:
                st.session_state.login_error = "아이디와 비밀번호를 입력해주세요."
                st.rerun()
            else:
                info = service.login_account(login_id, pw)
                if not info:
                    st.session_state.login_error = "로그인 정보가 올바르지 않습니다."
                    st.rerun()
                else:
                    expires = datetime.datetime.now() + datetime.timedelta(days=7)
                    cookie_manager.set("user_token", info["loginId"], expires_at=expires)
                    
                    st.session_state.logged_in = True
                    st.session_state.role = info["role"]
                    st.session_state.login_error = None
                    
                    import time
                    time.sleep(0.5) # 쿠키 저장 대기
                    
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


# 페이지 로드시 모달을 “자동”으로 한번 띄우기
if st.session_state._login_modal_open:
    login_modal()

# 모달이 닫혀도 페이지에는 아무것도 안 보이도록(원하면 안내문 정도만)
st.write("")
