"""
노티가드 통합 챗봇 페이지
Streamlit 네이티브 채팅 UI
"""
import streamlit as st
from core.layout import apply_portal_theme, render_topbar, portal_sidebar
from core.chatbot_engine import ChatbotEngine
import service

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

            # 어시스턴트 메시지에 참조 공지 버튼 표시
            if msg["role"] == "assistant" and "notice_refs" in msg and msg["notice_refs"]:
                st.markdown("---")
                st.caption("📎 참조된 공지사항:")

                # 상세 정보(제목 포함) 사용, 없으면 기존 방식(ID만)
                notice_details = msg.get("notice_details", [])

                # 버튼을 가로로 배치
                display_count = min(3, len(msg["notice_refs"]))
                cols = st.columns(display_count)

                for i in range(display_count):
                    with cols[i]:
                        # notice_details가 있으면 제목 사용, 없으면 ID만
                        if i < len(notice_details):
                            detail = notice_details[i]
                            ref_id = detail["post_id"]
                            title = detail["title"]
                            # 제목이 너무 길면 자르기 (20자)
                            short_title = title[:20] + "..." if len(title) > 20 else title
                            button_label = f"📄 {short_title}"
                        else:
                            ref_id = msg["notice_refs"][i]
                            button_label = f"공지 #{ref_id} 보기"

                        if st.button(
                            button_label,
                            key=f"notice_history_{msg_idx}_{i}_{ref_id}",
                            use_container_width=True
                        ):
                            st.session_state.selected_post_id = ref_id
                            if st.session_state.role == "ADMIN":
                                st.session_state.admin_menu = "게시판"
                                st.switch_page("pages/admin.py")
                            else:
                                st.session_state.emp_menu = "게시판"
                                st.switch_page("pages/employee.py")

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

                # 참조 공지 바로가기
                if notice_refs:
                    st.markdown("---")
                    st.caption("📎 참조된 공지사항:")
                    display_count = min(3, len(notice_refs))
                    cols = st.columns(display_count)

                    for i in range(display_count):
                        with cols[i]:
                            # notice_details가 있으면 제목 사용, 없으면 ID만
                            if i < len(notice_details):
                                detail = notice_details[i]
                                ref_id = detail["post_id"]
                                title = detail["title"]
                                # 제목이 너무 길면 자르기 (20자)
                                short_title = title[:20] + "..." if len(title) > 20 else title
                                button_label = f"📄 {short_title}"
                            else:
                                ref_id = notice_refs[i]
                                button_label = f"공지 #{ref_id} 보기"

                            if st.button(
                                button_label,
                                key=f"notice_new_{ref_id}_{i}",
                                use_container_width=True
                            ):
                                st.session_state.selected_post_id = ref_id
                                if st.session_state.role == "ADMIN":
                                    st.session_state.admin_menu = "게시판"
                                    st.switch_page("pages/admin.py")
                                else:
                                    st.session_state.emp_menu = "게시판"
                                    st.switch_page("pages/employee.py")

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
