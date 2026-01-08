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

    if is_pending:
        st.warning("정말로 확인 처리하시겠습니까? (되돌릴 수 없습니다)")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("네", type="primary", use_container_width=True, key=f"popup_confirm_yes_{popup_id}"):
                service.confirm_popup_action(emp_id, popup_id)
                close_popup_now_hard()
        with c2:
            if st.button("아니오", use_container_width=True, key=f"popup_confirm_no_{popup_id}"):
                st.session_state._popup_confirm_pending = False
                st.session_state._popup_confirm_pending_id = None
                st.rerun()
        st.stop()

    # 본문 먼저 표시
    BODY_H = 200
    with st.container(height=BODY_H, border=False):
        # 텍스트 렌더
        safe_html = _escape(content).replace("\n", "<br>")
        st.markdown(f'<div class="hs-content">{safe_html}</div>', unsafe_allow_html=True)

    # 이미지는 본문 아래에 표시
    img_url = payload.get("imageUrl") or payload.get("image_url")
    img_path = payload.get("imagePath") or payload.get("image_path")
    img_b64  = payload.get("imageBase64") or payload.get("image_base64")

    has_image = bool(img_url or img_path or img_b64)

    if has_image:
        st.markdown('<div style="margin: 12px 0;"></div>', unsafe_allow_html=True)

        try:
            if img_url:
                # R2 URL 이미지 - 다운로드해서 표시
                from core.storage import get_file

                try:
                    # R2에서 파일 다운로드
                    img_bytes = get_file(img_url)
                    st.image(img_bytes, use_container_width=True)
                except Exception as download_error:
                    # 다운로드 실패 시 직접 URL 시도
                    st.warning(f"이미지 로드 중 오류: {str(download_error)}")
                    st.caption(f"이미지 URL: {img_url}")

            elif img_path:
                # 로컬 파일 이미지
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                st.image(img_bytes, use_container_width=True)

            elif img_b64:
                # base64 이미지 (data:image/png;base64,... 형태도 처리)
                if "," in img_b64:
                    img_b64 = img_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(img_b64)
                st.image(img_bytes, use_container_width=True)

        except FileNotFoundError as e:
            st.warning(f"첨부 이미지를 찾을 수 없습니다: {str(e)}")
        except Exception as e:
            st.warning(f"첨부 이미지 표시 중 오류가 발생했습니다: {str(e)}")


    st.markdown('<div class="hs-line"></div>', unsafe_allow_html=True)

    # 버튼들을 2x2 그리드로 배치하여 한 화면에 잘 보이게 함
    # 1행: 확인함 / 나중에 확인
    # 2행: 요약 보기 / 챗봇으로 바로가기
    
    r1_c1, r1_c2 = st.columns(2, gap="small")
    r2_c1, r2_c2 = st.columns(2, gap="small")

    # [1행 1열] 버튼 1: 확인함
    with r1_c1:
        if st.button("1. 확인함", use_container_width=True, key=f"popup_confirm_{popup_id}"):
            st.session_state._popup_confirm_pending = True
            st.session_state._popup_confirm_pending_id = popup_id
            st.rerun()

    # [1행 2열] 버튼 2: 나중에 확인
    with r1_c2:
        # 텍스트 길이 줄임: "남은 횟수:" -> ""
        btn_label = f"2. 나중에 확인 ({remaining}회)"
        if st.button(btn_label, use_container_width=True, key=f"popup_later_{popup_id}"):
            res = service.ignore_popup_action(emp_id, popup_id)
            if not res.get("ok"):
                st.error("횟수 초과")
            else:
                st.session_state.employee_info = service.get_employee_info(emp_id)
                close_popup_now_hard()

    # [2행 1열] 버튼 3: 요약 보기
    with r2_c1:
        if st.button("3. 요약 보기", use_container_width=True, key=f"popup_summary_{popup_id}"):
            st.session_state["_popup_summary_modal_open"] = True
            st.session_state["_popup_summary_payload"] = {
                "popup_id": popup_id,
                "title": title,
                "content": content,
            }
            st.rerun()

    # [2행 2열] 버튼 4: 챗봇으로 바로가기
    with r2_c2:
        if st.button("4. 챗봇 질문", use_container_width=True, key=f"popup_chatbot_{popup_id}"):
            service.log_chatbot_move(emp_id, popup_id)

            # 챗봇 모달에 전달할 초기 질문 설정
            st.session_state["_chatbot_initial_query"] = f"{title}에 대해 알려줘"

            # 팝업 닫기
            st.session_state._popup_modal_open = False
            st.session_state._popup_payload = None
            st.session_state._last_popup_id = popup_id

            # 챗봇 모달 열기
            st.session_state._chatbot_modal_open = True
            st.rerun()

    # 버튼 색상 적용 스크립트
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const buttons = doc.querySelectorAll('button');
            buttons.forEach(btn => {
                const text = (btn.textContent || "").trim();
                if (text.includes("1. 확인함")) {
                    btn.style.backgroundColor = "#d9534f"; // Red
                    btn.style.borderColor = "#d9534f";
                    btn.style.color = "white";
                } else if (text.includes("2. 나중에 확인")) {
                    btn.style.backgroundColor = "#0b74d1"; // Blue
                    btn.style.borderColor = "#0b74d1";
                    btn.style.color = "white";
                } else if (text.includes("3. 요약 보기")) {
                    btn.style.backgroundColor = "#41b04a"; // Green
                    btn.style.borderColor = "#41b04a";
                    btn.style.color = "white";
                } else if (text.includes("4. 챗봇 질문")) {
                    btn.style.backgroundColor = "#f59e0b"; // Yellow
                    btn.style.borderColor = "#f59e0b";
                    btn.style.color = "white";
                }
            });
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

