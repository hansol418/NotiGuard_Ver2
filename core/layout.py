import base64
import mimetypes
from typing import Optional, List, Tuple
import streamlit as st


PORTAL_PRIMARY = "#139fb0"
PORTAL_BG = "#f5f7fb"
CARD_BORDER = "rgba(17,24,39,0.10)"

def apply_portal_theme(*, hide_pages_sidebar_nav: bool, hide_sidebar: bool, active_menu: Optional[str] = None):
    active_menu = active_menu or ""
    st.markdown(
        f"""
        <style>
        body {{ background: {PORTAL_BG}; }}
        .block-container {{
            padding-top: 0.8rem;
            padding-bottom: 1.2rem;
            max-width: 1600px;
        }}

        {"div[data-testid='stSidebarNav']{display:none !important;}" if hide_pages_sidebar_nav else ""}
        {"section[data-testid='stSidebar']{display:none !important;}" if hide_sidebar else ""}

        section[data-testid="stSidebar"] > div {{
            background: {PORTAL_PRIMARY};
            color: #fff;
            padding-top: 5px;
        }}

        section[data-testid="stSidebar"] h2 {{
            margin-top: 0 !important;
            padding-top: 10px !important;
            color: #fff !important;
        }}

        section[data-testid="stSidebar"] .stButton button {{
            width: 100%;
            border-radius: 0px;
            border: none;
            padding: 10px 12px;
            font-weight: 900;
            margin-bottom: 8px;
            background: transparent;
            color: #fff;
            height: 44px;
            box-shadow: none;

            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            text-align: left !important;
            padding-left: 16px !important;
        }}

        section[data-testid="stSidebar"] .stButton button > div {{
            width: 100% !important;
            display: flex !important;
            justify-content: flex-start !important;
        }}

        section[data-testid="stSidebar"] .stButton button:hover {{
            background: rgba(255,255,255,0.10);
            border-radius: 12px;
        }}

        section[data-testid="stSidebar"] .stButton button.hs-active {{
            background: rgba(255,255,255,0.18) !important;
            border-radius: 12px !important;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.30);
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {CARD_BORDER};
            border-radius: 14px;
            background: #fff;
            box-shadow: 0 10px 26px rgba(0,0,0,0.06);
        }}

        .stButton button[kind="primary"] {{
            background: {PORTAL_PRIMARY};
            border: 1px solid {PORTAL_PRIMARY};
            font-weight: 900;
            border-radius: 12px;
            height: 42px;
        }}

        .hs-card {{
            min-height: 230px;
            height: 230px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        </style>

        <script>
        (function () {{
          const active = {active_menu!r};
          const doc = window.parent.document;
          const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
          if (!sidebar) return;

          const btns = sidebar.querySelectorAll('button');
          btns.forEach((b) => {{
            const t = (b.innerText || '').trim();
            if (!t) return;
            if (t === active) b.classList.add('hs-active');
            else b.classList.remove('hs-active');
          }});
        }})();
        </script>
        """,
        unsafe_allow_html=True,
    )

PORTAL_PRIMARY = "#139fb0"
PORTAL_BG = "#f5f7fb"
CARD_BORDER = "rgba(17,24,39,0.10)"

def render_floating_widget(*, img_path: str, width_px: int = 200, bottom_px: int = 20, right_px: int = 20, on_click=None):
    """
    우측 하단 플로팅 '이미지 위젯' - 클릭 시 챗봇 모달 열기
    - width_px: 이미지 너비 기준(비율 유지)
    """
    import streamlit.components.v1 as components

    p = Path(img_path)
    if not p.exists():
        st.warning(f"Floating widget image not found: {p.resolve()}")
        return

    mime, _ = mimetypes.guess_type(str(p))
    mime = mime or "image/png"

    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    # 버튼 생성
    st.button("open", key="floating_chatbot_trigger", on_click=on_click)

    # 플로팅 위젯 생성 + 버튼 숨김 처리
    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;

            // 기존 요소 제거
            const old = doc.getElementById('floating-chatbot-widget');
            if (old) old.remove();
            const oldBubble = doc.getElementById('chatbot-bubble');
            if (oldBubble) oldBubble.remove();

            // 플로팅 위젯 생성
            const widget = doc.createElement('div');
            widget.id = 'floating-chatbot-widget';
            widget.style.cssText = `
                position: fixed;
                right: {right_px}px;
                bottom: {bottom_px}px;
                z-index: 999998;
                width: {width_px}px;
                height: {width_px}px;
                cursor: pointer;
                transition: transform 0.12s ease, filter 0.12s ease;
                background-image: url('{data_url}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
            `;

            // 말풍선 생성 ("질문해주세요! 💬")
            const bubble = doc.createElement('div');
            bubble.id = 'chatbot-bubble';
            bubble.innerHTML = '질문해주세요! 💬';
            bubble.style.cssText = `
                position: fixed;
                right: {right_px + width_px + 5}px;
                bottom: {bottom_px + int(width_px/2)}px;
                transform: translateY(50%);
                background-color: #f3f4f6;
                color: #111827;
                padding: 8px 14px;
                border-radius: 20px;
                border-bottom-right-radius: 4px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                font-size: 14px;
                font-weight: 800;
                z-index: 999999;
                pointer-events: none;
                white-space: nowrap;
                animation: floatBubbleLeft 2s ease-in-out infinite alternate;
                opacity: 1;
            `;
            
            // 애니메이션 키프레임 (이미 존재하면 생략)
            if (!doc.getElementById('chatbot-bubble-style')) {{
                const style = doc.createElement('style');
                style.id = 'chatbot-bubble-style';
                style.innerHTML = `
                    @keyframes floatBubbleLeft {{
                        0% {{ transform: translateY(50%); }}
                        100% {{ transform: translateY(calc(50% - 6px)); }}
                    }}
                `;
                doc.head.appendChild(style);
            }}

            widget.onmouseenter = () => {{
                widget.style.transform = 'translateY(-2px)';
                widget.style.filter = 'drop-shadow(0 22px 42px rgba(0,0,0,0.34))';
            }};
            widget.onmouseleave = () => {{
                widget.style.transform = '';
                widget.style.filter = '';
            }};
            widget.onclick = () => {{
                if (bubble) bubble.remove();
                
                const buttons = doc.querySelectorAll('button');
                for (let btn of buttons) {{
                    if ((btn.textContent || '').trim() === 'open') {{
                        btn.click();
                        break;
                    }}
                }}
            }};

            doc.body.appendChild(widget);
            doc.body.appendChild(bubble);

            // "open" 버튼 숨기기 - 여러 번 시도
            function hideOpenButton() {{
                const buttons = doc.querySelectorAll('button');
                buttons.forEach(btn => {{
                    if ((btn.textContent || '').trim() === 'open') {{
                        btn.style.display = 'none';
                        if (btn.parentElement) {{
                            btn.parentElement.style.display = 'none';
                        }}
                    }}
                }});
            }}

            // 즉시 실행 + 여러 번 재시도
            hideOpenButton();
            setTimeout(hideOpenButton, 50);
            setTimeout(hideOpenButton, 100);
            setTimeout(hideOpenButton, 200);
            setTimeout(hideOpenButton, 500);
        }})();
        </script>
        """,
        height=0,
    )


def remove_floating_widget():
    """
    강제로 플로팅 위젯 및 말풍선 제거 (챗봇 페이지 등에서 사용)
    """
    import streamlit.components.v1 as components
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const widget = doc.getElementById('floating-chatbot-widget');
            if (widget) widget.remove();
            const bubble = doc.getElementById('chatbot-bubble');
            if (bubble) bubble.remove();
        })();
        </script>
        """,
        height=0,
    )


def render_topbar(title: str):
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
          <div style="font-size:22px;font-weight:950;color:#111827;">{title}</div>
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="min-width:320px;">
        """,
        unsafe_allow_html=True,
    )
    st.text_input("통합검색", placeholder="통합검색 (데모)", label_visibility="collapsed", key="global_search")
    st.markdown("</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        st.button("🔔", key="topbell")
    with c2:
        st.button("👤", key="topuser")
    st.markdown("</div></div>", unsafe_allow_html=True)

def info_card(title: str, subtitle: str, lines: List[Tuple[str, str]], badge: Optional[str] = None):
    badge_html = ""
    if badge:
        badge_html = f"""
        <span style="
          background: rgba(19,159,176,0.15);
          color: #0b7f8e;
          font-weight: 950;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          border: 1px solid rgba(19,159,176,0.25);
          white-space: nowrap;
        ">{badge}</span>
        """

    kv_html = "".join([
        f'<div style="color:rgba(0,0,0,0.55);font-weight:850;">{k}</div>'
        f'<div style="color:#111827;font-weight:950;">{v}</div>'
        for k, v in lines
    ])

    st.markdown(
        f"""
        <div class="hs-card">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div>
              <div style="font-weight:950;font-size:15px;color:#111827;">{title}</div>
              <div style="margin-top:2px;color:rgba(0,0,0,0.55);font-size:13px;">{subtitle}</div>
            </div>
            {badge_html}
          </div>

          <div style="display:grid;grid-template-columns:92px 1fr;row-gap:8px;column-gap:12px;font-size:13px;margin-top:10px;flex:1;">
            {kv_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def app_links_card(title: str, links: list[str], role: str):
    st.markdown(f"**{title}**")
    for i, name in enumerate(links):
        st.button(name, use_container_width=True, key=f"link_{role}_{name}_{i}")

def render_chatbot_modal(user_id: str):
    """
    챗봇 모달 다이얼로그
    - 플로팅 위젯 또는 사이드바에서 호출
    """
    import streamlit.components.v1 as components
    from core.chatbot_engine import ChatbotEngine

    # 채팅 히스토리 초기화
    st.session_state.setdefault("modal_chat_messages", [])

    # 엔진 초기화
    engine = ChatbotEngine(user_id=user_id)

    # 챗봇 모달 전용 스타일 (JS로 고유 ID 추가)
    components.html(
        """
        <script>
        (function () {
          const doc = window.parent.document;
          const id = "chatbot-modal-style";
          if (doc.getElementById(id)) return;

          // 챗봇 모달에 고유 클래스 추가
          const dialogs = doc.querySelectorAll('div[role="dialog"]');
          dialogs.forEach(dlg => {
            const title = dlg.querySelector('h2');
            if (title && title.textContent.includes('노티가드 AI 챗봇')) {
              dlg.classList.add('chatbot-modal');
            }
          });

          // 챗봇 모달 전용 스타일
          const style = doc.createElement("style");
          style.id = id;
          style.innerHTML = `
            div[role="dialog"].chatbot-modal > div {
              width: min(700px, 90vw) !important;
              max-width: min(700px, 90vw) !important;
              max-height: 85vh !important;
            }

            /* 챗봇 모달 내부 여백 조정 */
            div[role="dialog"].chatbot-modal .block-container {
              padding-left: 1rem !important;
              padding-right: 1rem !important;
              max-width: 100% !important;
            }

            /* chat_input 너비 조정 */
            div[role="dialog"].chatbot-modal [data-testid="stChatInput"] {
              max-width: 100% !important;
            }
          `;
          doc.head.appendChild(style);
        })();
        </script>
        """,
        height=0,
    )

    st.markdown("### 🤖 노티가드 AI 챗봇")
    st.caption("효성전기 공지사항에 대해 무엇이든 물어보세요!")

    # 초기 질문 처리 (팝업에서 넘어온 경우)
    initial_query = st.session_state.get("_chatbot_initial_query")
    if initial_query and len(st.session_state.modal_chat_messages) == 0:
        # 자동으로 질문 처리
        st.session_state.modal_chat_messages.append({
            "role": "user",
            "content": initial_query
        })

        # 챗봇 응답 생성
        with st.spinner("답변 생성 중..."):
            result = engine.ask(initial_query)
            response = result["response"]

            st.session_state.modal_chat_messages.append({
                "role": "assistant",
                "content": response
            })

        # 초기 질문 초기화 (재사용 방지)
        st.session_state["_chatbot_initial_query"] = None

    # 채팅 히스토리 표시 (높이 축소)
    chat_container = st.container(height=350)
    with chat_container:
        if len(st.session_state.modal_chat_messages) == 0:
            st.info("👋 안녕하세요! 저는 노티가드입니다.\n\n효성전기의 공지사항에 대해 궁금한 점을 물어보세요!")

        for msg in st.session_state.modal_chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 입력창
    prompt = st.chat_input("예: 이번 주 안전교육 일정 알려줘", key="modal_chat_input")

    if prompt:
        # 사용자 메시지 추가
        st.session_state.modal_chat_messages.append({
            "role": "user",
            "content": prompt
        })

        # 챗봇 응답
        with st.spinner("답변 생성 중..."):
            result = engine.ask(prompt)
            response = result["response"]

            # 봇 메시지 추가
            st.session_state.modal_chat_messages.append({
                "role": "assistant",
                "content": response
            })

        # 새 메시지를 즉시 표시
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                st.markdown(response)

    # 하단 버튼
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 대화 초기화", use_container_width=True, key="modal_reset"):
            st.session_state.modal_chat_messages = []
            st.session_state["_chatbot_initial_query"] = None
            st.rerun()
    with col2:
        if st.button("📧 담당자 문의", use_container_width=True, key="modal_email"):
            # 챗봇 페이지로 이동
            st.session_state._chatbot_modal_open = False
            st.switch_page("pages/chatbot.py")


def portal_sidebar(*, role: str, active_menu: str, on_menu_change):
    st.sidebar.markdown("## HS HYOSEONG")

    # 메뉴 구성 (챗봇, 문의관리 추가)
    menus = ["홈", "게시판"] + (["글쓰기", "문의관리"] if role == "ADMIN" else []) + ["챗봇", "문서관리","커뮤니티","보고"]

    for m in menus:
        if st.sidebar.button(m, key=f"nav_{role}_{m}", use_container_width=True):
            # 챗봇 메뉴는 페이지 전환
            if m == "챗봇":
                st.switch_page("pages/chatbot.py")
            else:
                on_menu_change(m)
                st.rerun()

    st.sidebar.markdown("---")

    if st.sidebar.button("로그아웃", key=f"logout_{role}", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.employee_id = None
        st.session_state.employee_info = None
        st.session_state._login_modal_open = True
        
        # 로그아웃 플래그 설정 (Login 페이지에서 쿠키 삭제 처리)
        st.session_state["logout_clicked"] = True
        
        st.switch_page("pages/0_Login.py")
