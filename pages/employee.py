# STREAMLIT/pages/employee.py
import time
import base64
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from html import escape as _escape
import service
from core.layout import (
    apply_portal_theme,
    render_topbar,
    info_card,
    app_links_card,
    portal_sidebar,
    render_floating_widget,
)
from core.summary import summarize_notice


st.set_page_config(page_title="Employee", layout="wide")

# -------------------------
# 로그인 체크
# -------------------------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("employee_id", None)
st.session_state.setdefault("employee_info", None)

st.session_state.setdefault("last_viewed_post_id", None)  # 상세 진입 1회만 조회수 증가용

# 팝업 2차확인용
st.session_state.setdefault("_popup_confirm_pending", False)
st.session_state.setdefault("_popup_confirm_pending_id", None)

if (not st.session_state.logged_in) or (st.session_state.role != "EMPLOYEE"):
    st.switch_page("pages/0_Login.py")

# -------------------------
# 공통 유틸
# -------------------------
def fmt_dt(ms: int) -> str:
    if not ms:
        return ""
    dt = datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d %H:%M")


def _clear_board_selection():
    if "emp_board_table" in st.session_state:
        try:
            st.session_state.emp_board_table["selection"]["rows"] = []
        except Exception:
            pass


def on_menu_change(new_menu: str):
    st.session_state.emp_menu = new_menu
    st.session_state.selected_post_id = None
    _clear_board_selection()


# -------------------------
# 상태값
# -------------------------
st.session_state.setdefault("emp_menu", "홈")
st.session_state.setdefault("selected_post_id", None)

# 팝업 상태
st.session_state.setdefault("_popup_modal_open", False)
st.session_state.setdefault("_popup_payload", None)
st.session_state.setdefault("_last_popup_id", None)

# -------------------------
# 테마/사이드바/상단바
# -------------------------
apply_portal_theme(
    hide_pages_sidebar_nav=True,
    hide_sidebar=False,
    active_menu=st.session_state.emp_menu,
)

portal_sidebar(role="EMPLOYEE", active_menu=st.session_state.emp_menu, on_menu_change=on_menu_change)
render_topbar("전사 Portal")
# 챗봇 모달 정의
@st.dialog("노티가드 AI 챗봇", width="large")
def chatbot_modal():
    from core.layout import render_chatbot_modal
    employee_id = st.session_state.get("employee_id", "guest")
    render_chatbot_modal(user_id=employee_id)

render_floating_widget(img_path="assets/chatimg_r.png", on_click=chatbot_modal)

menu = st.session_state.emp_menu

# -------------------------
# 홈 카드(요약)
# -------------------------
def render_home_cards():
    info = st.session_state.employee_info or {}
    a, b, c = st.columns([1.25, 3.25, 1.25], gap="large")

    with a:
        box = st.container(border=True)
        with box:
            info_card(
                title="사용자 정보",
                subtitle="직원 계정",
                lines=[
                    ("사번", info.get("employeeId", "-")),
                    ("이름", info.get("name", "-")),
                    ("본부", info.get("department", "-")),
                    ("팀", info.get("team", "-")),
                    ("무시횟수", f"{int(info.get('ignoreRemaining', 0) or 0)}회"),
                ],
                badge="USER",
            )

    with b:
        box = st.container(border=True)
        with box:
            info_card(
                title="전사게시판",
                subtitle="공지 목록/상세 확인",
                lines=[("기능", "공지 조회/상세"), ("권한", "관리자 작성 / 직원 조회")],
            )
            if st.button("게시판 바로가기", type="primary", key="go_board_emp"):
                on_menu_change("게시판")
                st.rerun()

    with c:
        box = st.container(border=True)
        with box:
            app_links_card("업무사이트 (데모)", ["e-Accounting", "JDE ERP", "HRM", "e-Procurement"], role="EMPLOYEE")


# -------------------------------------------------------
#    중요공지 모달 (목표 UI)
#  - "현재 떠있는 dialog 박스"를 JS로 찾아 크기/여백을 정확히 강제
#  - 본문만 스크롤 (스크롤바 보이게)
#  - 버튼 4개(확인/나중/요약/챗봇) 컬러/크기 고정
#  - 요약은 인라인이 아니라 "새 모달"로 띄움
# -------------------------------------------------------

def _inject_dialog_style():
    components.html(
        """
        <script>
        (function () {
          const doc = window.parent.document;
          const id = "hs-popup-style-v5";
          if (doc.getElementById(id)) return;

          const style = doc.createElement("style");
          style.id = id;
          style.innerHTML = `
            /* 팝업 사이즈: 보기 편한 카드 폭 */
            div[role="dialog"] > div {
              width: min(1200px, 92vw) !important;
              max-width: min(1200px, 92vw) !important;

              max-height: 90vh !important;
              border-radius: 18px !important;

              /* Dialog 전체에 스크롤 가능 (버튼이 잘리지 않도록) */
              overflow-y: auto !important;
              overflow-x: hidden !important;
            }

            /* dialog 내부 가운데 정렬 */
            [data-testid="stDialog"] .block-container{
              padding-top: 0px !important;
              padding-bottom: 0px !important;
              margin: 0 auto !important;
              max-width: 100% !important;
            }

            /* 닫기 버튼(X) 숨김 */
            div[role="dialog"] button[aria-label="Close"] {
              display: none !important;
            }
          `;
          doc.head.appendChild(style);
        })();
        </script>
        """,
        height=0,
    )


# -------------------------------------------------------
#  요약 모달 (중요공지 모달 밖에서만 호출되어야 함!)
# -------------------------------------------------------
@st.dialog("공지 요약", width="large")
def popup_summary_dialog(popup_id: int, title: str, content: str):
    # 캐시 준비
    st.session_state.setdefault("popup_summary_cache", {})  # {popup_id: summary}

    # 요약 생성(캐시 없을 때만)
    if popup_id not in st.session_state.popup_summary_cache:
        with st.spinner("공지 요약 중..."):
            st.session_state.popup_summary_cache[popup_id] = summarize_notice(
                title=title or "", content=content or ""
            )

    summary = st.session_state.popup_summary_cache.get(popup_id, "")

    st.markdown("#### 요약 결과")
    with st.container(height=320, border=True):
        st.write(summary or "요약 결과가 없습니다.")

    if st.button("닫기", use_container_width=True, key=f"summary_close_{popup_id}"):
        st.session_state["_popup_summary_modal_open"] = False
        st.session_state["_popup_summary_payload"] = None
        st.rerun()


# -------------------------------------------------------
#    중요공지 모달
#  - 버튼 4개: 확인함 / 나중에 확인 / 요약 보기 / 챗봇 바로가기
#  - 요약보기는 dialog 중첩 금지 때문에 state만 켜고, 바깥에서 모달 호출
# -------------------------------------------------------
@st.dialog("중요공지", width="large")
def popup_banner_dialog(payload: dict):
    _inject_dialog_style()

    title = payload.get("title", "")
    content = payload.get("content", "")
    remaining = int(payload.get("ignoreRemaining", 0) or 0)

    emp_id = st.session_state.employee_id
    popup_id = int(payload["popupId"])

    # 요약 모달 state 준비
    st.session_state.setdefault("_popup_summary_modal_open", False)
    st.session_state.setdefault("_popup_summary_payload", None)
    
    # 팝업 뷰 상태 (content / chatbot)
    st.session_state.setdefault("_popup_view", "content")
    
    # 버튼 색상 CSS - 최우선 주입
    st.markdown(
        """
        <style>
        /* 팝업 버튼 색상 - 매우 높은 우선순위 */
        div[data-testid="stDialog"] button[data-testid="baseButton-secondary"] {
            font-weight: 500 !important;
        }
        
        /* 너비 100% 버튼에만 적용 */
        div[data-testid="stDialog"] button[data-testid="baseButton-secondary"][style*="width: 100%"],
        div[data-testid="stDialog"] button[style*="width"][style*="100%"] {
            border: 2px solid !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    def _force_close_dialog_dom():
        components.html(
            """
            <script>
            (function () {
              const doc = window.parent.document;
              const dlg = doc.querySelector('div[role="dialog"]');
              if (!dlg) return;
              const closeBtn = dlg.querySelector('button[aria-label="Close"]');
              if (closeBtn) closeBtn.click();
            })();
            </script>
            """,
            height=0,
        )

    def close_popup_now_hard():
        st.session_state._popup_modal_open = False
        st.session_state._popup_payload = None
        st.session_state._last_popup_id = popup_id
        st.session_state._popup_confirm_pending = False
        st.session_state._popup_confirm_pending_id = None
        _force_close_dialog_dom()
        st.stop()

    # 2차 확인 단계 여부
    is_pending = (
        st.session_state.get("_popup_confirm_pending", False)
        and st.session_state.get("_popup_confirm_pending_id", None) == popup_id
    )

    # ----------------------------
    # 스타일 (버튼 간격만 최소화)
    # ----------------------------
    st.markdown(
        """
        <style>
        .hs-wrap{
          padding: 10px 16px 14px 16px;
          margin: 0;
        }
        .hs-toplabel{
          font-size: 15px;
          font-weight: 800;
          opacity: 0.85;
          margin: 0 0 2px 0;
        }
        .hs-title{
          font-size: 30px;
          font-weight: 900;
          margin: 0;
          line-height: 1.25;
        }
        .hs-line{
          height: 1px;
          background: rgba(0,0,0,0.20);
          margin: 6px 0 8px 0;
        }
        .hs-instruction{
          font-size: 13px;
          font-weight: 700;
          opacity: 0.85;
          margin: 0 0 8px 0;
        }
        .hs-content{
          font-size: 20px;
          line-height: 1.6;
          white-space: pre-wrap;
          margin: 0;
          opacity: 0.92;
        }

        /* 버튼 */
        .hs-btn-confirm div > button{
          width: 100%;
          height: 44px;
          border-radius: 8px;
          border: none;
          background: #d9534f;
          color: #fff;
          font-weight: 900;
          font-size: 15px;
        }
        .hs-btn-later div > button{
          width: 100%;
          height: 44px;
          border-radius: 8px;
          border: none;
          background: #0b74d1;
          color: #fff;
          font-weight: 900;
          font-size: 15px;
        }
        .hs-btn-summary div > button{
          width: 100%;
          height: 44px;
          border-radius: 8px;
          border: none;
          background: #41b04a;
          color: #fff;
          font-weight: 900;
          font-size: 15px;
        }
        .hs-btn-chat div > button{
          width: 100%;
          height: 44px;
          border-radius: 8px;
          border: none;
          background: #f59e0b;
          color: #fff;
          font-weight: 900;
          font-size: 15px;
        }

        /* 버튼 간격(더 좁게) */
        .hs-gap{ margin-top: 3px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------
    # 내용 렌더
    # ----------------------------
    st.markdown('<div class="hs-wrap">', unsafe_allow_html=True)

    st.markdown('<div class="hs-toplabel">전체공지</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hs-title">{title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hs-line"></div>', unsafe_allow_html=True)
    st.markdown('<div class="hs-instruction">해당 공지에 대한 처리 방식을 선택하세요.</div>', unsafe_allow_html=True)

    # ========== 챗봇 뷰 ==========
    if st.session_state._popup_view == "chatbot":
        from core.chatbot_engine import ChatbotEngine
        
        st.markdown("### 🤖 AI 챗봇에게 질문하기")
        st.caption(f"공지: {title}")
        
        # 채팅 메시지 초기화
        st.session_state.setdefault("_popup_chat_messages", [])
        
        # 엔진 초기화
        engine = ChatbotEngine(user_id=emp_id)
        
        # (초기 질문 자동 처리 제거됨)
        
        # 채팅 히스토리 표시
        chat_container = st.container(height=400)
        with chat_container:
            if len(st.session_state._popup_chat_messages) == 0:
                st.info("👋 안녕하세요! 이 공지에 대해 궁금한 점을 물어보세요!")
            
            for msg in st.session_state._popup_chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 입력창
        prompt = st.chat_input("질문을 입력하세요...", key="popup_chat_input")
        
        if prompt:
            st.session_state._popup_chat_messages.append({
                "role": "user",
                "content": prompt
            })
            
            with st.spinner("답변 생성 중..."):
                result = engine.ask(prompt)
                response = result["response"]
                
                st.session_state._popup_chat_messages.append({
                    "role": "assistant",
                    "content": response
                })
            
            st.rerun()
        
        # 하단 버튼
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅ 공지로 돌아가기", use_container_width=True, key="popup_chat_back"):
                st.session_state._popup_view = "content"
                st.session_state._popup_chat_messages = []
                st.rerun()
        with col2:
            if st.button("📧 담당자 문의", use_container_width=True, key="popup_chat_email"):
                st.session_state._popup_view = "email"
                st.rerun()
        with col3:
            if st.button("✅ 확인 완료", type="primary", use_container_width=True, key="popup_chat_confirm"):
                st.session_state._popup_confirm_pending = True
                st.session_state._popup_confirm_pending_id = popup_id
                st.rerun()
        
        st.stop()
    
    # ========== 담당자 문의 뷰 ==========
    if st.session_state._popup_view == "email":
        from core.chatbot_engine import ChatbotEngine
        from core.config import DEPARTMENT_EMAILS, ADMIN_EMAIL
        from core.email_utils import send_email
        import time
        
        st.markdown("#### 📧 담당자에게 문의하기")
        st.caption(f"공지: {title}")
        
        # 마지막 유저 질문 찾기 (챗봇 대화에서)
        last_query = ""
        for msg in reversed(st.session_state.get("_popup_chat_messages", [])):
            if msg["role"] == "user":
                last_query = msg["content"]
                break
        
        # 첫 진입시 AI 작성
        if "_popup_email_draft" not in st.session_state:
            engine = ChatbotEngine(user_id=emp_id)
            emp_info = st.session_state.get("employee_info") or {}
            dept = emp_info.get("department", "")
            name = emp_info.get("name", "")
            user_info_str = f"\n\n[작성자 정보]\n소속: {dept}\n이름: {name}" if dept else ""
            
            # 질문이 없으면 공지 내용으로
            query_for_email = last_query if last_query else f"{title}에 대한 문의"
            
            # 부서 감지
            detected = engine.detect_target_department(query_for_email)
            st.session_state._popup_mail_dept = detected if detected in DEPARTMENT_EMAILS else list(DEPARTMENT_EMAILS.keys())[0]
            
            with st.spinner("AI가 문의 내용을 작성 중입니다..."):
                initial_draft = f"질문 내용: {query_for_email}{user_info_str}\n\n[추가 문의 사항을 작성해주세요]"
                refined = engine.refine_email_content(st.session_state._popup_mail_dept, query_for_email, initial_draft)
                st.session_state._popup_email_draft = refined
        
        # UI
        if last_query:
            st.info(f"원본 질문: {last_query}")
        else:
            st.info(f"공지 '{title}'에 대한 문의")
        
        target_dept = st.selectbox(
            "문의할 부서 (AI 자동 선택됨)",
            options=list(DEPARTMENT_EMAILS.keys()),
            key="_popup_mail_dept",
            help="AI가 자동으로 선택한 부서입니다. 필요시 변경 가능합니다."
        )
        
        content_text = st.text_area(
            "문의 내용 (AI가 공식 문서로 작성함)",
            key="_popup_email_draft",
            height=250,
            help="AI가 자동으로 공식적인 형식으로 작성했습니다. 필요시 수정 가능합니다."
        )
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬅ 챗봇으로", use_container_width=True, key="_popup_email_back"):
                del st.session_state._popup_email_draft
                if "_popup_mail_dept" in st.session_state:
                    del st.session_state._popup_mail_dept
                st.session_state._popup_view = "chatbot"
                st.rerun()
        
        with c2:
            if st.button("✨ AI 재작성", use_container_width=True, key="_popup_email_refine"):
                engine = ChatbotEngine(user_id=emp_id)
                query_for_email = last_query if last_query else f"{title}에 대한 문의"
                with st.spinner("AI가 내용을 다시 다듬고 있습니다..."):
                    refined = engine.refine_email_content(target_dept, query_for_email, content_text)
                    st.session_state._popup_email_draft = refined
                    st.rerun()
        
        with c3:
            if st.button("📤 메일 발송", type="primary", use_container_width=True, key="_popup_email_send"):
                manager_email = DEPARTMENT_EMAILS.get(target_dept, ADMIN_EMAIL)
                query_for_subject = last_query if last_query else title
                subject = f"[노티가드 문의] {query_for_subject[:20]}..."
                
                with st.spinner(f"{target_dept} 담당자에게 발송 중..."):
                    success = send_email(manager_email, subject, content_text)
                    time.sleep(0.5)
                
                # DB 저장
                query_for_db = last_query if last_query else f"{title}에 대한 문의"
                service.save_inquiry(emp_id, target_dept, query_for_db, content_text)
                
                if success:
                    st.success(f"✅ 전송 완료! ({manager_email})")
                else:
                    st.warning("⚠️ 발송 실패 (SMTP 설정을 확인하세요)")
                
                time.sleep(2)
                del st.session_state._popup_email_draft
                if "_popup_mail_dept" in st.session_state:
                    del st.session_state._popup_mail_dept
                st.session_state._popup_view = "content"
                st.rerun()
        
        st.stop()
    
    # ========== 확인 대기 뷰 ==========
    if is_pending:
        st.warning("정말로 확인 처리하시겠습니까? (되돌릴 수 없습니다)")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("네", type="primary", use_container_width=True, key=f"popup_confirm_yes_{popup_id}"):
                service.confirm_popup_action(emp_id, popup_id)
                # 챗봇/이메일 상태 초기화
                st.session_state._popup_chat_messages = []
                st.session_state._popup_view = "content"
                if "_popup_email_draft" in st.session_state:
                    del st.session_state._popup_email_draft
                if "_popup_mail_dept" in st.session_state:
                    del st.session_state._popup_mail_dept
                close_popup_now_hard()
        with c2:
            if st.button("아니오", use_container_width=True, key=f"popup_confirm_no_{popup_id}"):
                st.session_state._popup_confirm_pending = False
                st.session_state._popup_confirm_pending_id = None
                st.rerun()
        st.stop()
    
    # ========== 기본 콘텐츠 뷰 ==========

    # 이미지는 본문 판단을 위해 먼저 확인
    img_url = payload.get("imageUrl") or payload.get("image_url")
    img_path = payload.get("imagePath") or payload.get("image_path")
    img_b64  = payload.get("imageBase64") or payload.get("image_base64")

    has_image = bool(img_url or img_path or img_b64)
    
    # 본문 텍스트 준비
    safe_html = _escape(content).replace("\n", "<br>")

    # 레이아웃 분기: 이미지가 있으면 좌우 배치, 없으면 전체 배치
    CONTENT_HEIGHT = 400  # 한 화면에 적절히 들어오도록 높이 설정

    if has_image:
        # 1:1 비율로 텍스트/이미지 배치
        c_text, c_img = st.columns([1, 1], gap="medium")
        
        # [좌측] 텍스트
        with c_text:
            with st.container(height=CONTENT_HEIGHT, border=False):
                st.markdown(f'<div class="hs-content">{safe_html}</div>', unsafe_allow_html=True)
        
        # [우측] 이미지
        with c_img:
            # 이미지 컨테이너 (스크롤 가능하게 하여 너무 긴 이미지 대응)
            with st.container(height=CONTENT_HEIGHT, border=False):
                try:
                    if img_url:
                        from core.storage import get_file
                        try:
                            img_bytes = get_file(img_url)
                            st.image(img_bytes, use_container_width=True)
                        except Exception as download_error:
                            st.warning(f"이미지 로드 중 오류: {str(download_error)}")
                            st.caption(f"이미지 URL: {img_url}")

                    elif img_path:
                        with open(img_path, "rb") as f:
                            img_bytes = f.read()
                        st.image(img_bytes, use_container_width=True)

                    elif img_b64:
                        if "," in img_b64:
                            img_b64 = img_b64.split(",", 1)[1]
                        img_bytes = base64.b64decode(img_b64)
                        st.image(img_bytes, use_container_width=True)

                except FileNotFoundError as e:
                    st.warning(f"첨부 이미지를 찾을 수 없습니다: {str(e)}")
                except Exception as e:
                    st.warning(f"첨부 이미지 표시 중 오류가 발생했습니다: {str(e)}")

    else:
        # 이미지가 없으면 텍스트만 넓게 표시
        with st.container(height=CONTENT_HEIGHT, border=False):
            st.markdown(f'<div class="hs-content">{safe_html}</div>', unsafe_allow_html=True)


    st.markdown('<div class="hs-line"></div>', unsafe_allow_html=True)

    # 버튼들을 2x2 그리드로 배치하여 한 화면에 잘 보이게 함
    # 1행: 확인함 / 나중에 확인
    # 2행: 요약 보기 / 챗봇으로 바로가기
    
    r1_c1, r1_c2 = st.columns(2, gap="small")
    r2_c1, r2_c2 = st.columns(2, gap="small")

    # [1행 1열] 버튼 1: 확인함 - 빨강
    with r1_c1:
        if st.button("1. 확인함", use_container_width=True, key=f"popup_confirm_{popup_id}"):
            st.session_state._popup_confirm_pending = True
            st.session_state._popup_confirm_pending_id = popup_id
            st.rerun()

    # [1행 2열] 버튼 2: 나중에 확인 - 파랑
    with r1_c2:
        btn_label = f"2. 나중에 확인 ({remaining}회)"
        if st.button(btn_label, use_container_width=True, key=f"popup_later_{popup_id}"):
            res = service.ignore_popup_action(emp_id, popup_id)
            if not res.get("ok"):
                st.error("횟수 초과")
            else:
                st.session_state.employee_info = service.get_employee_info(emp_id)
                close_popup_now_hard()

    # [2행 1열] 버튼 3: 요약 보기 - 초록
    with r2_c1:
        if st.button("3. AI 요약 보기", use_container_width=True, key=f"popup_summary_{popup_id}"):
            st.session_state["_popup_summary_modal_open"] = True
            st.session_state["_popup_summary_payload"] = {
                "popup_id": popup_id,
                "title": title,
                "content": content,
            }
            st.rerun()

    # [2행 2열] 버튼 4: 챗봇으로 바로가기 - 노랑
    with r2_c2:
        if st.button("4. AI 챗봇에게 질문", use_container_width=True, key=f"popup_chatbot_{popup_id}"):
            service.log_chatbot_move(emp_id, popup_id)
            st.session_state._popup_view = "chatbot"
            st.rerun()

    # 버튼 색상 강제 적용 - MutationObserver 사용
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            
            const COLORS = {
                '1. 확인함': { bg: '#d9534f', border: '#d9534f', text: 'white' },
                '2. 나중에 확인': { bg: '#0b74d1', border: '#0b74d1', text: 'white' },
                '3. AI 요약 보기': { bg: '#41b04a', border: '#41b04a', text: 'white' },
                '4. AI 챗봇에게 질문': { bg: '#f59e0b', border: '#f59e0b', text: 'black' }
            };
            
            function colorButton(btn) {
                const txt = (btn.textContent || '').trim();
                
                for (const [key, colors] of Object.entries(COLORS)) {
                    if (txt.includes(key)) {
                        btn.style.cssText = `
                            background: ${colors.bg} !important;
                            background-color: ${colors.bg} !important;
                            border: 2px solid ${colors.border} !important;
                            border-color: ${colors.border} !important;
                            color: ${colors.text} !important;
                        `;
                        const p = btn.querySelector('p');
                        if (p) {
                            p.style.cssText = `color: ${colors.text} !important;`;
                        }
                        return true;
                    }
                }
                return false;
            }
            
            function colorAllButtons() {
                const buttons = doc.querySelectorAll('button');
                let count = 0;
                buttons.forEach(btn => {
                    if (colorButton(btn)) count++;
                });
                return count;
            }
            
            // 즉시 실행
            colorAllButtons();
            setTimeout(colorAllButtons, 10);
            setTimeout(colorAllButtons, 50);
            setTimeout(colorAllButtons, 100);
            setTimeout(colorAllButtons, 200);
            setTimeout(colorAllButtons, 500);
            
            // MutationObserver로 DOM 변경 감지
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    // 새로 추가된 노드 확인
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element 노드
                            if (node.tagName === 'BUTTON') {
                                colorButton(node);
                            } else {
                                // 자식 중 버튼 찾기
                                const buttons = node.querySelectorAll ? node.querySelectorAll('button') : [];
                                buttons.forEach(colorButton);
                            }
                        }
                    });
                    
                    // 속성 변경된 버튼 재적용
                    if (mutation.type === 'attributes' && mutation.target.tagName === 'BUTTON') {
                        colorButton(mutation.target);
                    }
                });
            });
            
            // body 전체 관찰
            observer.observe(doc.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class']
            });
            
            // 주기적으로도 실행 (이중 안전장치)
            let attempts = 0;
            const interval = setInterval(() => {
                const count = colorAllButtons();
                attempts++;
                if (count >= 4 || attempts >= 50) {
                    clearInterval(interval);
                }
            }, 100);
            
            // 10초 후 정리
            setTimeout(() => {
                clearInterval(interval);
                observer.disconnect();
            }, 10000);
        })();
        </script>
        """,
        height=0
    )



# =========================================================
#   요약 모달 트리거 (중요공지 dialog 밖에서 호출)
# =========================================================
if st.session_state.get("_popup_summary_modal_open", False):
    payload = st.session_state.get("_popup_summary_payload") or {}
    if payload:
        popup_summary_dialog(
            popup_id=payload["popup_id"],
            title=payload.get("title", ""),
            content=payload.get("content", ""),
        )
        st.stop() # 중복으로 열려서 발생한 에러 해당 st.dialog는 하나만 열려야함

# -------------------------
# 메뉴별 화면
# -------------------------
if menu == "홈":
    render_home_cards()
    st.write("")
    st.divider()

    st.subheader("직원 홈")
    st.caption("※ 5초마다 중요공지(팝업)를 조회합니다.")

    emp_id = st.session_state.employee_id
    popup = service.get_latest_popup_for_employee(emp_id)

    if popup:
        popup_id = int(popup.get("popupId"))
        if (st.session_state._last_popup_id != popup_id) and (not st.session_state._popup_modal_open):
            st.session_state._popup_payload = popup
            st.session_state._popup_modal_open = True
            st.session_state._last_popup_id = popup_id

    if st.session_state.get("_popup_summary_modal_open", False): # 요약이 열려있으면 해당 run파일은 배너를 열지 않음
        st.stop()

    if st.session_state._popup_modal_open and st.session_state._popup_payload:
        popup_banner_dialog(st.session_state._popup_payload)
        st.stop()

    if not popup:
        st.success("현재 수신한 중요공지가 없습니다.")

    # time.sleep(5)
    # st.rerun()

elif menu == "게시판":

    def _clear_emp_board_selection():
        if "emp_board_table" in st.session_state:
            try:
                st.session_state.emp_board_table["selection"]["rows"] = []
            except Exception:
                pass

    # =========================================================
    #  상세 화면
    # =========================================================
    if st.session_state.selected_post_id:
        st.subheader("게시글 상세")
        pid = int(st.session_state.selected_post_id)

        # 핵심: 상세 진입 '최초 1회'만 조회수 +1
        if st.session_state.last_viewed_post_id != pid:
            service.increment_views(pid)
            st.session_state.last_viewed_post_id = pid

        post = service.get_post_by_id(pid)

        box = st.container(border=True)
        with box:
            if not post:
                st.error("게시글을 찾을 수 없습니다.")
            else:
                badge = "중요공지" if post["type"] == "중요" else "일반공지"
                st.markdown(f"**[{badge}] {post['title']}**")
                st.caption(
                    f"작성자: {post['author']} | 작성일: {fmt_dt(post['timestamp'])} | 조회: {post['views']}"
                )
                st.text(post["content"])

                attachments = post.get("attachments", []) if post else []
                if attachments:
                    st.markdown("**첨부파일**")
                    for a in attachments:
                        path = a.get("filePath", "")
                        name = a.get("filename", "file")
                        mime = (a.get("mimeType", "") or "").lower()

                        try:
                            from core.storage import get_file
                            data = get_file(path)

                            if mime.startswith("image/"):
                                st.image(data, caption=name)

                            st.download_button(
                                label=f"다운로드: {name}",
                                data=data,
                                file_name=name,
                                mime=a.get("mimeType", "") or None,
                                key=f"dl_emp_{a['fileId']}",
                            )
                        except Exception as e:
                            st.warning(f"파일을 찾을 수 없습니다: {name} ({str(e)})")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("목록으로", type="primary", use_container_width=True, key="emp_back_to_list"):
                #  목록으로 돌아갈 때: 상세 상태/선택/조회 게이트 초기화
                st.session_state.selected_post_id = None
                st.session_state.last_viewed_post_id = None
                _clear_emp_board_selection()
                st.rerun()

        with c2:
            if st.button("홈으로", use_container_width=True, key="emp_back_home"):
                #  홈으로 갈 때도: 조회 게이트 초기화 (다시 들어오면 1회 증가)
                st.session_state.last_viewed_post_id = None
                on_menu_change("홈")
                st.rerun()

    # =========================================================
    #  목록 화면
    # =========================================================
    else:
        st.subheader("게시판 홈")

        box = st.container(border=True)
        with box:
            st.markdown("**전사 공지**")
            posts = service.list_posts()

            if not posts:
                st.info("등록된 게시글이 없습니다.")
            else:
                # 테이블 헤더
                h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([0.8, 4, 1.5, 2, 1])
                h_col1.markdown("**:gray[번호]**")
                h_col2.markdown("**:gray[제목 (클릭하여 확인)]**")
                h_col3.markdown("**:gray[작성자]**")
                h_col4.markdown("**:gray[작성일]**")
                h_col5.markdown("**:gray[조회]**")
                st.divider()

                # 게시글 목록 반복
                for p in posts:
                    row_c1, row_c2, row_c3, row_c4, row_c5 = st.columns([0.8, 4, 1.5, 2, 1])
                    
                    # 번호
                    row_c1.text(str(p["postId"]))
                    
                    # 제목 (버튼으로 구현하여 클릭 가능하게)
                    if row_c2.button(
                        p["title"], 
                        key=f"post_title_btn_{p['postId']}", 
                        use_container_width=True,
                    ):
                        st.session_state.selected_post_id = int(p["postId"])
                        st.rerun()
                    
                    # 작성자
                    row_c3.text(p["author"])
                    
                    # 작성일
                    row_c4.text(fmt_dt(p["timestamp"]))
                    
                    # 조회수
                    row_c5.text(str(p["views"]))
                    
                    # 구분선
                    st.markdown("<hr style='margin: 0.2rem 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
                    
else:
    st.info("준비 중인 메뉴입니다.")

