# STREAMLIT/pages/chatbot.py
import streamlit as st
import service
from core.layout import (
    apply_portal_theme,
    render_topbar,
    portal_sidebar,
    remove_floating_widget,
)
from core.chatbot_engine import ChatbotEngine
from core.config import DEPARTMENT_EMAILS, ADMIN_EMAIL
from core.email_utils import send_email
import time

st.set_page_config(page_title="Chatbot", layout="wide")

# -------------------------
# 로그인 체크
# -------------------------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("employee_id", None)
st.session_state.setdefault("employee_info", None)

if not st.session_state.logged_in:
    st.switch_page("pages/0_Login.py")

# -------------------------
# 메뉴 변경 핸들러
# -------------------------
def on_menu_change(new_menu: str):
    if st.session_state.role == "ADMIN":
        st.session_state.admin_menu = new_menu
        st.switch_page("pages/admin.py")
    else:
        st.session_state.emp_menu = new_menu
        st.switch_page("pages/employee.py")

# -------------------------
# 상태값
# -------------------------
st.session_state.setdefault("emp_menu", "챗봇")

# -------------------------
# 테마/사이드바/상단바
# -------------------------
apply_portal_theme(
    hide_pages_sidebar_nav=True,
    hide_sidebar=False,
    active_menu="챗봇",
)

portal_sidebar(role=st.session_state.role, active_menu="챗봇", on_menu_change=on_menu_change)
render_topbar("전사 Portal")

# 챗봇 페이지에서는 플로팅 위젯 제거 (DOM에 남아있는 경우 삭제)
remove_floating_widget()

# -------------------------
# 챗봇 UI
# -------------------------

# 채팅 히스토리 초기화 (대화 세션)
st.session_state.setdefault("chatbot_sessions", {})  # {session_id: {name, messages, timestamp}}
st.session_state.setdefault("current_session_id", None)

# 엔진 초기화 - 관리자는 "admin", 직원은 employee_id 사용
if st.session_state.role == "ADMIN":
    user_id = "admin"
else:
    user_id = st.session_state.get("employee_id", "guest")
engine = ChatbotEngine(user_id=user_id)

# 세션 카운터 초기화
st.session_state.setdefault("session_counter", 0)

# 대화 히스토리 관리 함수
# 대화 히스토리 관리 함수
def create_new_session(initial_messages=None):
    """새 대화 세션 생성 (메모리)"""
    st.session_state.session_counter += 1
    session_id = f"session_{st.session_state.session_counter}"
    
    messages = initial_messages if initial_messages else []
    
    # AI로 세션 이름 생성 (첫 사용자 메시지가 있는 경우)
    session_name = f"새 대화 {st.session_state.session_counter}"
    if messages:
        # 첫 번째 사용자 메시지 찾기
        first_user_msg = None
        for msg in messages:
            if msg["role"] == "user":
                first_user_msg = msg["content"]
                break
        
        if first_user_msg:
            try:
                # AI로 요약 (짧게)
                session_name = engine.summarize_query(first_user_msg)
            except:
                pass
    
    # 세션 상태 생성
    st.session_state.chatbot_sessions[session_id] = {
        "name": session_name,
        "messages": messages,
        "timestamp": int(time.time() * 1000)
    }
    st.session_state.current_session_id = session_id
    
    return session_id

def delete_session(session_id):
    """대화 세션 삭제"""
    if session_id in st.session_state.chatbot_sessions:
        del st.session_state.chatbot_sessions[session_id]
        
        # 현재 세션이 삭제된 경우
        if st.session_state.current_session_id == session_id:
            # 남은 세션 중 가장 최근 것 선택
            remaining = list(st.session_state.chatbot_sessions.keys())
            if remaining:
                # timestamp 기준 정렬 (최신순)
                remaining.sort(key=lambda k: st.session_state.chatbot_sessions[k]["timestamp"], reverse=True)
                st.session_state.current_session_id = remaining[0]
            else:
                st.session_state.current_session_id = None

def update_session_name_if_needed(session_id):
    """세션 이름이 기본 형식이고 메시지가 있으면 AI로 업데이트"""
    session = st.session_state.chatbot_sessions.get(session_id)
    if not session:
        return
    
    # '새 대화'로 시작하거나 기본 이름일 때
    if session["name"].startswith("새 대화") and session["messages"]:
        first_user_msg = None
        for msg in session["messages"]:
            if msg["role"] == "user":
                first_user_msg = msg["content"]
                break
        
        if first_user_msg:
            try:
                new_name = engine.summarize_query(first_user_msg)
                # 상태 업데이트
                session["name"] = new_name
            except:
                pass



# -------------------------
# 담당자 문의 다이얼로그
# -------------------------
@st.dialog("📧 담당자에게 문의하기", width="large")
def email_dialog(user_query: str):
    """담당자 이메일 문의 다이얼로그"""
    
    # 세션 상태 초기화
    if "email_dialog_query" not in st.session_state or st.session_state.email_dialog_query != user_query:
        st.session_state.email_dialog_query = user_query
        
        # 직원 정보 가져오기
        emp_info = st.session_state.get("employee_info") or {}
        dept = emp_info.get("department", "")
        name = emp_info.get("name", "")
        user_info_str = f"\n\n[작성자 정보]\n소속: {dept}\n이름: {name}" if dept else ""
        
        # AI로 부서 자동 감지
        detected_dept = engine.detect_target_department(user_query)
        st.session_state.mail_dept = detected_dept if detected_dept in DEPARTMENT_EMAILS else list(DEPARTMENT_EMAILS.keys())[0]
        
        # AI로 내용 자동 다듬기
        with st.spinner("AI가 문의 내용을 작성하고 있습니다..."):
            initial_draft = f"질문 내용: {user_query}{user_info_str}\n\n[추가 문의 사항을 작성해주세요]"
            refined_content = engine.refine_email_content(
                st.session_state.mail_dept,
                user_query,
                initial_draft
            )
            st.session_state.mail_body = refined_content
    
    st.write("AI가 자동으로 담당 부서를 분석하고 공식적인 문의 내용을 작성했습니다.")
    st.info(f"💬 원본 질문: {user_query}")
    
    # 부서 선택 (AI 자동 선택됨)
    target_dept = st.selectbox(
        "문의할 부서 (AI 자동 선택됨)",
        options=list(DEPARTMENT_EMAILS.keys()),
        key="mail_dept",
        help="AI가 자동으로 선택한 부서입니다. 필요시 변경 가능합니다."
    )
    
    # 다듬어진 내용 표시 및 수정 가능
    content = st.text_area(
        "문의 내용 (AI가 공식 문서로 작성함)",
        key="mail_body",
        height=300,
        help="AI가 자동으로 공식적인 형식으로 작성했습니다. 필요시 수정 가능합니다."
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✨ AI로 다시 다듬기", use_container_width=True):
            with st.spinner("AI가 내용을 다시 다듬고 있습니다..."):
                refined = engine.refine_email_content(target_dept, user_query, content)
                st.session_state.mail_body = refined
                st.rerun()
    
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
            if "email_dialog_query" in st.session_state:
                del st.session_state.email_dialog_query
            time.sleep(2)
            st.rerun()


# -------------------------
# 모달 대화를 세션으로 가져오기
# -------------------------
# 모달에서 대화한 내용이 있으면 새 세션으로 저장
if "modal_chat_messages" in st.session_state and st.session_state.modal_chat_messages:
    # 첫 로딩 시에만 처리 (플래그 사용)
    if not st.session_state.get("_modal_imported", False):
        create_new_session(initial_messages=st.session_state.modal_chat_messages.copy())
        st.session_state.modal_chat_messages = []  # 모달 메시지 초기화
        st.session_state._modal_imported = True

# 첫 세션이 없으면 생성
if not st.session_state.chatbot_sessions:
    create_new_session()
else:
    # 페이지 로드 시 플래그 초기화 (다음 모달 import를 위해)
    st.session_state._modal_imported = False

# 현재 세션이 없으면 첫 세션으로 설정
if st.session_state.current_session_id is None and st.session_state.chatbot_sessions:
    st.session_state.current_session_id = list(st.session_state.chatbot_sessions.keys())[0]

# 레이아웃: 왼쪽 히스토리, 오른쪽 채팅
col_history, col_chat = st.columns([1, 3], gap="medium")

# -------------------------
# 왼쪽: 대화 히스토리
# -------------------------
with col_history:
    st.markdown("### 대화 히스토리")
    
    # 새 대화 버튼
    if st.button("➕ 새 대화", use_container_width=True, type="primary"):
        create_new_session()
        st.rerun()
    
    st.divider()
    
    # 세션 목록
    for session_id, session_data in st.session_state.chatbot_sessions.items():
        is_current = session_id == st.session_state.current_session_id
        
        # 세션 버튼 컨테이너
        session_container = st.container()
        with session_container:
            col_btn, col_del = st.columns([4, 1])
            
            with col_btn:
                button_type = "primary" if is_current else "secondary"
                if st.button(
                    session_data["name"],
                    key=f"session_{session_id}",
                    use_container_width=True,
                    type=button_type,
                ):
                    st.session_state.current_session_id = session_id
                    st.rerun()
            
            with col_del:
                if st.button("🗑️", key=f"delete_{session_id}", help="대화 삭제"):
                    delete_session(session_id)
                    st.rerun()

# -------------------------
# 오른쪽: 채팅
# -------------------------
with col_chat:
    st.markdown("### 🤖 노티가드 AI 챗봇")
    
    # 현재 세션 가져오기
    current_session = st.session_state.chatbot_sessions.get(st.session_state.current_session_id)
    
    if current_session:
        # 챗봇 인사말 및 안내
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 16px 20px; 
                    border-radius: 12px; 
                    margin-bottom: 16px;
                    color: white;">
            <h3 style="margin: 0 0 8px 0; color: white; font-size: 20px;">👋 안녕하세요!</h3>
            <p style="margin: 0; font-size: 15px; line-height: 1.5;">
                저는 노티가드 AI 챗봇입니다.<br>
                효성전기의 공지사항과 관련된 질문에 답변해 드립니다.<br>
                궁금한 점을 편하게 물어보세요!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 예시 질문 (대화가 없을 때만 표시)
        if len(current_session["messages"]) == 0:
            st.markdown("#### 💡 예시 질문")
            example_questions = [
                "이번 주 안전교육 일정 알려줘",
                "최근 공지사항 요약해줘",
                "휴가 신청 방법 알려줘",
                "복지 제도에 대해 알려줘"
            ]
            
            cols = st.columns(2)
            for i, question in enumerate(example_questions):
                with cols[i % 2]:
                    if st.button(f"💬 {question}", key=f"example_{i}", use_container_width=True):
                        # 예시 질문을 사용자 메시지로 추가
                        current_session["messages"].append({
                            "role": "user",
                            "content": question
                        })
                        

                        
                        # 첫 메시지인 경우 세션 이름 업데이트
                        if len(current_session["messages"]) == 1:
                            update_session_name_if_needed(st.session_state.current_session_id)
                        
                        # 챗봇 응답 생성
                        with st.spinner("답변 생성 중..."):
                            result = engine.ask(question)
                            response = result["response"]
                            notice_refs = result.get("notice_refs", [])
                            notice_details = result.get("notice_details", [])
                            
                            current_session["messages"].append({
                                "role": "assistant",
                                "content": response,
                                "notice_refs": notice_refs,
                                "notice_details": notice_details
                            })
                            

                        
                        st.rerun()
            
            st.markdown("")  # 약간의 여백
        
        # 채팅 입력창 (상단에 위치)
        prompt = st.chat_input("메시지를 입력하세요...", key="chatbot_input")
        
        if prompt:
            # 사용자 메시지 추가
            current_session["messages"].append({
                "role": "user",
                "content": prompt
            })
            

            
            # 첫 메시지인 경우 세션 이름 업데이트
            if len(current_session["messages"]) == 1:
                update_session_name_if_needed(st.session_state.current_session_id)
            
            # 챗봇 응답 생성
            with st.spinner("답변 생성 중..."):
                result = engine.ask(prompt)
                response = result["response"]
                notice_refs = result.get("notice_refs", [])
                notice_details = result.get("notice_details", [])
                
                current_session["messages"].append({
                    "role": "assistant",
                    "content": response,
                    "notice_refs": notice_refs,
                    "notice_details": notice_details
                })
                

            
            st.rerun()
        
        # 채팅 메시지 표시 (입력창 아래, border 없음)
        st.markdown("")  # 약간의 여백
        for msg_idx, msg in enumerate(current_session["messages"]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # 어시스턴트 메시지에 참조 공지 표시
                if msg["role"] == "assistant" and msg.get("notice_details"):
                    st.markdown("---")
                    notice_details = msg.get("notice_details", [])
                    
                    with st.expander(f"📚 참고한 공지사항 ({len(notice_details)}개)", expanded=False):
                        for i, detail in enumerate(notice_details):
                            ref_id = detail["post_id"]
                            title = detail["title"]
                            
                            # 공지 상세 정보 가져오기
                            post_info = service.get_post_by_id(ref_id)
                            
                            if post_info:
                                with st.container():
                                    st.markdown(f"**{i+1}. {title}**")
                                    
                                    # 작성일 표시
                                    from datetime import datetime
                                    ts = post_info.get('timestamp', 0)
                                    if ts:
                                        dt = datetime.fromtimestamp(ts / 1000.0)
                                        date_str = dt.strftime("%Y-%m-%d")
                                        st.caption(f"📅 작성일: {date_str}")
                                    
                                    # 공지 내용 표시 (접을 수 있게)
                                    content = post_info.get('content', '')
                                    if len(content) > 200:
                                        with st.expander("원문 보기", expanded=False):
                                            st.text(content)
                                    else:
                                        st.text(content)
                                    
                                    # 게시판에서 보기 버튼
                                    if st.button(f"📋 게시판에서 보기", key=f"view_ref_{msg_idx}_{i}_{ref_id}", use_container_width=True):
                                        st.session_state.selected_post_id = ref_id
                                        st.session_state.emp_menu = "게시판"
                                        st.switch_page("pages/employee.py")
                                    
                                    if i < len(notice_details) - 1:
                                        st.divider()

        
        # 하단 버튼
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 현재 대화 초기화", use_container_width=True):
                current_session["messages"] = []
                st.rerun()
        with col2:
            if st.button("📧 담당자에게 문의", use_container_width=True):
                # 가장 최근 사용자 질문 찾기
                user_query = None
                for msg in reversed(current_session["messages"]):
                    if msg["role"] == "user":
                        user_query = msg["content"]
                        break
                
                if user_query:
                    email_dialog(user_query)
                else:
                    st.warning("먼저 챗봇에게 질문을 해주세요.")
    else:
        st.warning("대화 세션을 선택하거나 새로 만들어주세요.")
