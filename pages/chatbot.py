"""
노티가드 통합 챗봇 페이지
Streamlit 네이티브 채팅 UI
"""
import streamlit as st
from core.layout import apply_portal_theme, render_topbar, portal_sidebar
from core.chatbot_engine import ChatbotEngine
from core.config import DEPARTMENT_EMAILS, ADMIN_EMAIL
from core.email_utils import send_email
import service
import time
from datetime import datetime

st.set_page_config(
    page_title="노티가드 챗봇",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# 로그인 체크
# -------------------------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("employee_id", None)

if not st.session_state.get("logged_in"):
    st.switch_page("pages/0_Login.py")

# -------------------------
# 헬퍼 함수
# -------------------------
def format_timestamp(ts):
    """밀리초 타임스탬프를 읽기 쉬운 날짜 형식으로 변환"""
    try:
        if isinstance(ts, int):
            dt = datetime.fromtimestamp(ts / 1000)
            return dt.strftime("%Y-%m-%d")
        return str(ts)
    except:
        return ""

# -------------------------
# 담당자 문의 다이얼로그
# -------------------------
@st.dialog("📧 담당자에게 문의하기", width="large")
def email_dialog(user_query: str):
    """담당자 이메일 문의 다이얼로그"""
    user_id = st.session_state.get("employee_id") or "guest"
    engine = ChatbotEngine(user_id=user_id)

    # 세션 상태 초기화
    if "active_mail_query" not in st.session_state or st.session_state.active_mail_query != user_query:
        st.session_state.active_mail_query = user_query

        # 직원 정보 가져오기
        emp_info = st.session_state.get("employee_info", {})
        dept = emp_info.get("department", "")
        name = emp_info.get("name", "")
        user_info_str = f"\n\n[작성자 정보]\n소속: {dept}\n이름: {name}" if dept else ""

        # 초기 내용 구성
        initial_body = f"질문 내용: {user_query}{user_info_str}\n\n[추가 문의 사항을 작성해주세요]"
        st.session_state.mail_body = initial_body

        # 부서 자동 감지
        detected_dept = engine.detect_target_department(user_query)
        st.session_state.mail_dept = detected_dept if detected_dept in DEPARTMENT_EMAILS else list(DEPARTMENT_EMAILS.keys())[0]

    st.write("해당 질문에 대해 담당 부서 관리자에게 직접 이메일로 문의합니다.")
    st.info(f"💬 질문: {user_query}")

    # AI 다듬기 콜백
    def handle_refine():
        current_content = st.session_state.mail_body
        target_dept = st.session_state.mail_dept

        if not current_content.strip():
            st.warning("내용을 입력해주세요.")
            return

        with st.spinner("AI가 내용을 다듬고 있습니다..."):
            refined = engine.refine_email_content(target_dept, user_query, current_content)
            st.session_state.mail_body = refined

    # 레이아웃
    with st.container():
        # 부서 선택
        target_dept = st.selectbox(
            "문의할 부서 선택",
            options=list(DEPARTMENT_EMAILS.keys()),
            key="mail_dept",
            help="질문과 관련된 담당 부서를 선택해주세요."
        )

        # 내용 작성
        content = st.text_area(
            "문의 내용 (AI가 다듬어 드립니다 ✨)",
            key="mail_body",
            height=300,
            placeholder="관리자에게 전달할 내용을 자유롭게 작성하세요.\n작성 후 'AI로 내용 다듬기'를 누르면 격식 있는 이메일로 변환됩니다."
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            st.button(
                "✨ AI로 내용 다듬기",
                use_container_width=True,
                on_click=handle_refine,
                help="내용을 작성한 뒤 클릭하면 전문가 톤으로 다듬어줍니다."
            )

        with col2:
            if st.button("📤 이메일 발송", type="primary", use_container_width=True):
                manager_email = DEPARTMENT_EMAILS.get(target_dept, ADMIN_EMAIL)
                subject = f"[노티가드 문의] {user_query[:30]}..."

                with st.spinner(f"{target_dept} 담당자에게 메일 발송 중..."):
                    # 이메일 발송 시도
                    success = send_email(manager_email, subject, content)
                    time.sleep(0.5)

                # DB 저장
                save_success = service.save_inquiry(user_id, target_dept, user_query, content)

                if success:
                    st.success(f"✅ 전송 완료! {target_dept} 담당자에게 문의 내용이 전달되었습니다.")
                    st.info(f"수신자: {manager_email}")
                else:
                    st.warning("⚠️ SMTP 설정이 없어 실제 메일 발송은 되지 않았습니다.")
                    st.info(f"""
                        [전송 시뮬레이션]
                        수신자: {manager_email}
                        제목: {subject}

                        *실제 발송을 위해서는 .env 파일의 SMTP 설정을 확인해주세요.*
                    """)

                if save_success:
                    st.success("📝 관리자 페이지에 문의가 접수되었습니다.")

                # 상태 정리
                if "active_mail_query" in st.session_state:
                    del st.session_state.active_mail_query
                time.sleep(2)
                st.rerun()


# -------------------------
# 메뉴 핸들러
# -------------------------
def on_menu_change(menu):
    """메뉴 변경 핸들러"""
    if menu == "홈":
        if st.session_state.role == "ADMIN":
            st.switch_page("pages/admin.py")
        else:
            st.switch_page("pages/employee.py")
    elif menu == "게시판":
        if st.session_state.role == "ADMIN":
            st.session_state.admin_menu = "게시판"
            st.switch_page("pages/admin.py")
        else:
            st.session_state.emp_menu = "게시판"
            st.switch_page("pages/employee.py")
    elif menu == "글쓰기" and st.session_state.role == "ADMIN":
        st.session_state.admin_menu = "글쓰기"
        st.switch_page("pages/admin.py")

# -------------------------
# 테마/사이드바/상단바
# -------------------------
apply_portal_theme(
    hide_pages_sidebar_nav=True,
    hide_sidebar=False,
    active_menu="챗봇"
)

portal_sidebar(
    role=st.session_state.role,
    active_menu="챗봇",
    on_menu_change=on_menu_change
)

render_topbar("노티가드 AI 챗봇")

# -------------------------
# 챗봇 엔진 초기화
# -------------------------
user_id = st.session_state.get("employee_id") or "guest"

# -------------------------
# 미확인 팝업 알림 (직원만)
# -------------------------
if st.session_state.role == "EMPLOYEE":
    engine = ChatbotEngine(user_id=user_id)
    pending_popup = engine.check_pending_popups()

    if pending_popup:
        with st.container():
            st.warning(f"⚠️ **미확인 중요공지**: {pending_popup['title']}")

            col1, col2, col3 = st.columns([1, 2, 2])

            with col1:
                if st.button("✅ 지금 확인", type="primary", key="confirm_popup_btn", use_container_width=True):
                    if engine.confirm_popup_from_chat(pending_popup['popupId']):
                        st.success("✅ 확인 완료!")
                        st.rerun()

            with col2:
                if st.button("🤖 챗봇에게 물어보기", key="ask_chatbot_btn", use_container_width=True):
                    # 팝업 내용을 자동 질문
                    auto_query = f"{pending_popup['title']}에 대해 자세히 알려줘"
                    if "chat_messages" not in st.session_state:
                        st.session_state.chat_messages = []
                    st.session_state.chat_messages.append({
                        "role": "user",
                        "content": auto_query
                    })
                    st.rerun()

            with col3:
                if st.button("📋 게시판에서 보기", key="view_board_btn", use_container_width=True):
                    st.session_state.selected_post_id = pending_popup['popupId']
                    st.session_state.emp_menu = "게시판"
                    st.switch_page("pages/employee.py")

            st.markdown("---")

# -------------------------
# 챗봇 세션 관리
# -------------------------
# 세션 스토리지 초기화
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = []  # [{id, summary, messages, created_at}]

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# 현재 세션이 없으면 새로 생성
if st.session_state.current_session_id is None:
    import time
    session_id = int(time.time() * 1000)
    st.session_state.chat_sessions.append({
        "id": session_id,
        "summary": "새 대화",
        "messages": [],
        "created_at": session_id
    })
    st.session_state.current_session_id = session_id

# 현재 세션 가져오기
current_session = next(
    (s for s in st.session_state.chat_sessions if s["id"] == st.session_state.current_session_id),
    None
)

# 세션이 없으면 새로 생성 (안전장치)
if current_session is None:
    import time
    session_id = int(time.time() * 1000)
    current_session = {
        "id": session_id,
        "summary": "새 대화",
        "messages": [],
        "created_at": session_id
    }
    st.session_state.chat_sessions.append(current_session)
    st.session_state.current_session_id = session_id

# 하위 호환성을 위해 chat_messages 유지
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = current_session["messages"]
else:
    # 현재 세션의 메시지와 동기화
    current_session["messages"] = st.session_state.chat_messages

# -------------------------
# 챗봇 UI (탭 방식)
# -------------------------
st.markdown("### 🤖 공지사항 AI 도우미")

# 탭 생성: 현재 대화 | 지난 대화 기록
tab1, tab2 = st.tabs(["💬 현재 대화", f"🕒 지난 대화 기록 (최근 20개)"])

with tab1:
    # 새 대화 버튼
    if st.button("➕ 새 대화 시작", type="primary", key="new_chat_main"):
        import time
        session_id = int(time.time() * 1000)
        st.session_state.chat_sessions.append({
            "id": session_id,
            "summary": "새 대화",
            "messages": [],
            "created_at": session_id
        })
        st.session_state.current_session_id = session_id
        st.session_state.chat_messages = []
        st.rerun()

    st.caption("효성전기 공지사항에 대해 무엇이든 물어보세요!")

    # -------------------------
    # 채팅 메시지 표시
    # -------------------------
    for msg_idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # 어시스턴트 메시지에 참조 공지 펼침/줄임 표시
            if msg["role"] == "assistant" and "notice_refs" in msg and msg["notice_refs"]:
                st.markdown("---")

                # 상세 정보(제목 포함) 사용
                notice_details = msg.get("notice_details", [])

                if notice_details:
                    with st.expander(f"📚 참고한 공지사항 원문 보기 ({len(notice_details)}개)"):
                        for i, detail in enumerate(notice_details):
                            ref_id = detail["post_id"]
                            title = detail["title"]

                            # 공지 상세 정보 가져오기
                            post_info = service.get_post_by_id(ref_id)

                            if post_info:
                                with st.container():
                                    c1, c2 = st.columns([4, 1])
                                    with c1:
                                        st.markdown(f"**📄 {title}**")
                                        date_str = format_timestamp(post_info.get('timestamp', 0))
                                        st.caption(f"📅 {date_str} | 내용: {post_info.get('content', '')[:80]}...")
                                    with c2:
                                        if st.button("보기", key=f"view_hist_ref_{msg_idx}_{i}_{ref_id}", use_container_width=True):
                                            st.session_state.selected_post_id = ref_id
                                            if st.session_state.role == "ADMIN":
                                                st.session_state.admin_menu = "게시판"
                                                st.switch_page("pages/admin.py")
                                            else:
                                                st.session_state.emp_menu = "게시판"
                                                st.switch_page("pages/employee.py")
                                    st.divider()

            # 어시스턴트 메시지에 담당자 문의 버튼 추가
            if msg["role"] == "assistant":
                # 이전 사용자 메시지 가져오기 (원본 질문)
                user_query = ""
                if msg_idx > 0 and st.session_state.chat_messages[msg_idx - 1]["role"] == "user":
                    user_query = st.session_state.chat_messages[msg_idx - 1]["content"]

                if user_query:
                    if st.button("📧 담당자에게 문의하기", key=f"email_btn_history_{msg_idx}", use_container_width=False):
                        email_dialog(user_query)

    # -------------------------
    # 사용자 입력
    # -------------------------
    if prompt := st.chat_input("예: 이번 주 안전교육 일정 알려줘"):
        # 사용자 메시지 추가
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # 챗봇 응답
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                engine = ChatbotEngine(user_id=user_id)

                # 첫 질문인 경우 세션 요약 업데이트
                if len(st.session_state.chat_messages) == 1:
                    summary = engine.summarize_query(prompt)
                    current_session["summary"] = summary

                result = engine.ask(prompt)

                response = result["response"]
                response_type = result["response_type"]
                notice_refs = result.get("notice_refs", [])
                notice_details = result.get("notice_details", [])

                # 응답 타입별 스타일 적용
                if response_type == "MISSING":
                    st.warning(f"🔍 {response}")
                elif response_type == "IRRELEVANT":
                    st.info(f"💬 {response}")
                else:
                    st.markdown(response)

                # 참조 공지 펼침/줄임 (새 응답)
                if notice_refs and notice_details:
                    st.markdown("---")
                    with st.expander(f"📚 참고한 공지사항 원문 보기 ({len(notice_details)}개)"):
                        for i, detail in enumerate(notice_details):
                            ref_id = detail["post_id"]
                            title = detail["title"]

                            # 공지 상세 정보 가져오기
                            post_info = service.get_post_by_id(ref_id)

                            if post_info:
                                with st.container():
                                    c1, c2 = st.columns([4, 1])
                                    with c1:
                                        st.markdown(f"**📄 {title}**")
                                        date_str = format_timestamp(post_info.get('timestamp', 0))
                                        st.caption(f"📅 {date_str} | 내용: {post_info.get('content', '')[:80]}...")
                                    with c2:
                                        if st.button("보기", key=f"view_new_ref_{i}_{ref_id}", use_container_width=True):
                                            st.session_state.selected_post_id = ref_id
                                            if st.session_state.role == "ADMIN":
                                                st.session_state.admin_menu = "게시판"
                                                st.switch_page("pages/admin.py")
                                            else:
                                                st.session_state.emp_menu = "게시판"
                                                st.switch_page("pages/employee.py")
                                    st.divider()

                # 담당자 문의 버튼 추가 (새 응답)
                st.markdown("---")
                if st.button("📧 담당자에게 문의하기", key="email_btn_new", use_container_width=False):
                    email_dialog(prompt)

                # 봇 메시지 저장 (참조 정보 포함)
                import time
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response,
                    "notice_refs": notice_refs,
                    "notice_details": notice_details,  # 제목 정보 포함
                    "timestamp": int(time.time() * 1000)  # 고유 키를 위한 타임스탬프
                })

    # -------------------------
    # 사이드바 정보
    # -------------------------
    with st.sidebar:
        st.markdown("---")

        st.markdown("### 💡 사용 팁")
        st.markdown("""
        **질문 예시:**
        - "이번 주 교육 일정은?"
        - "인사팀 공지사항 보여줘"
        - "연차 신청 방법 알려줘"
        - "안전교육 언제야?"
        """)

        st.markdown("---")

        # 대화 초기화 버튼
        if st.button("🗑️ 현재 대화 삭제", use_container_width=True, key="delete_chat"):
            # 현재 세션 삭제
            st.session_state.chat_sessions = [
                s for s in st.session_state.chat_sessions
                if s["id"] != st.session_state.current_session_id
            ]

            # 새 세션 생성
            if len(st.session_state.chat_sessions) == 0:
                import time
                session_id = int(time.time() * 1000)
                st.session_state.chat_sessions.append({
                    "id": session_id,
                    "summary": "새 대화",
                    "messages": [],
                    "created_at": session_id
                })
                st.session_state.current_session_id = session_id
            else:
                # 가장 최근 세션으로 전환
                st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]

            st.session_state.chat_messages = []
            st.rerun()

        # 통계 정보 (관리자만)
        if st.session_state.role == "ADMIN":
            st.markdown("---")
            st.markdown("### 📊 챗봇 통계")

            from core.db import get_conn
            import time

            with get_conn() as conn:
                # 오늘 질문 수
                today_start = int(time.mktime(time.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d'))) * 1000
                cur = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM chat_logs
                    WHERE created_at >= %s
                """, (today_start,))
                row = cur.fetchone()
                today_count = row['count'] if row else 0

                st.metric("오늘 질문", f"{today_count}개")

                # 전체 질문 수
                cur = conn.execute("SELECT COUNT(*) as count FROM chat_logs")
                row = cur.fetchone()
                total_count = row['count'] if row else 0

                st.metric("전체 질문", f"{total_count}개")

    # -------------------------
    # 초기 안내 메시지
    # -------------------------
    if len(st.session_state.chat_messages) == 0:
        with st.chat_message("assistant"):
            st.markdown("""
    👋 안녕하세요! 저는 **노티가드**입니다.

    효성전기의 공지사항에 대해 궁금한 점을 물어보세요!

    **이런 걸 도와드릴 수 있어요:**
    - 📅 교육 일정 확인
    - 📢 최신 공지사항 검색
    - 🏢 부서별 공지 조회
    - 📝 연차/휴가 관련 안내

    아래 채팅창에 질문을 입력해보세요!
            """)

with tab2:
    st.markdown("#### 🕒 지난 대화 기록 (최근 20개)")
    
    # 최근 20개 세션 정렬
    sorted_sessions = sorted(
        st.session_state.chat_sessions,
        key=lambda x: x["created_at"],
        reverse=True
    )[:20]
    
    if len(sorted_sessions) == 0:
        st.info("아직 대화 기록이 없습니다.")
    else:
        for idx, session in enumerate(sorted_sessions, 1):
            session_id = session["id"]
            summary = session["summary"]
            msg_count = len(session["messages"]) // 2
            is_current = (session_id == st.session_state.current_session_id)
            
            # 현재 대화 표시
            with st.container():
                col1, col2, col3 = st.columns([1, 6, 2])
                
                with col1:
                    if is_current:
                        st.markdown("**💬**")
                    else:
                        st.markdown(f"**{idx}**")
                
                with col2:
                    st.markdown(f"**{summary}**")
                    st.caption(f"{msg_count}개 메시지")
                
                with col3:
                    if st.button(
                        "열기" if not is_current else "현재",
                        key=f"open_session_{session_id}",
                        use_container_width=True,
                        disabled=is_current,
                        type="secondary"
                    ):
                        # 세션 전환
                        st.session_state.current_session_id = session_id
                        st.session_state.chat_messages = session["messages"]
                        st.rerun()
                
                st.markdown("---")

# -------------------------
# 사이드바 정보
# -------------------------
