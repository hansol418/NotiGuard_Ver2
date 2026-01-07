# STREAMLIT/pages/admin.py
import streamlit as st
from datetime import datetime
import time
import service
import pandas as pd
from core.layout import (
    apply_portal_theme,
    render_topbar,
    info_card,
    app_links_card,
    portal_sidebar,
    remove_floating_widget,
)

st.set_page_config(page_title="Admin", layout="wide")

# 로그인 체크
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("role", None)

if (not st.session_state.logged_in) or (st.session_state.role != "ADMIN"):
    st.switch_page("pages/0_Login.py")

def fmt_dt(ms: int) -> str:
    if not ms:
        return ""
    dt = datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d %H:%M")


# -------------------------
# 상태값
# -------------------------
st.session_state.setdefault("admin_menu", "홈")
st.session_state.setdefault("selected_post_id", None)
st.session_state.setdefault("last_saved_post", None)

# [추가] 상세 진입 1회만 조회수 증가용
st.session_state.setdefault("last_viewed_post_id", None)

# 팝업 대상 선택 모달 상태
st.session_state.setdefault("open_target_dialog", False)
st.session_state.setdefault("target_selected_departments", set())
st.session_state.setdefault("target_selected_teams", set())

# 예약 전송 시간(라디오) 상태값
st.session_state.setdefault("popup_expected_send_time", "오전 10시")

# 문의관리 상태
st.session_state.setdefault("selected_inquiry_id", None)
st.session_state.setdefault("inquiry_filter_status", "전체")
st.session_state.setdefault("inquiry_filter_dept", "전체")

apply_portal_theme(hide_pages_sidebar_nav=True, hide_sidebar=False, active_menu=st.session_state.admin_menu)
remove_floating_widget()

DEPARTMENTS = [
    "미래전략실",
    "기술고문실",
    "감사팀",
    "비서팀",
    "연구개발본부",
    "운영본부",
    "경영관리본부",
]
TEAMS_BY_DEPT = {
    "연구개발본부": ["연구1팀", "연구2팀", "신사업팀", "연구지원팀", "특수모터팀"],
    "운영본부": ["PM팀", "글로벌영업팀", "생산팀", "구매팀", "생산기술팀", "품질팀"],
    "경영관리본부": ["경영관리팀", "재경팀", "인사팀", "정보화팀"],
}


# -------------------------
# 유틸
# -------------------------
def reset_targets():
    st.session_state.target_selected_departments = set()
    st.session_state.target_selected_teams = set()

    # 위젯 상태도 같이 초기화(경고 방지 + 다음 오픈 시 깨끗하게)
    for dept in DEPARTMENTS:
        k = f"dlg_dept_{dept}"
        if k in st.session_state:
            del st.session_state[k]
    for dept, teams in TEAMS_BY_DEPT.items():
        for t in teams:
            k = f"dlg_team_{dept}_{t}"
            if k in st.session_state:
                del st.session_state[k]


def select_all_targets():
    """
    중요 공지일 때, 대상 선택 모달을 '전체 선택' 상태로 시작
    - set + 위젯 session_state를 같은 소스로 맞춤 (value= 미사용)
    """
    st.session_state.target_selected_departments = set(DEPARTMENTS)

    all_teams = []
    for dept, teams in TEAMS_BY_DEPT.items():
        for t in teams:
            all_teams.append(t)
            st.session_state[f"dlg_team_{dept}_{t}"] = True  # ✅ 위젯 상태 직접 세팅

    st.session_state.target_selected_teams = set(all_teams)

    for dept in DEPARTMENTS:
        st.session_state[f"dlg_dept_{dept}"] = True  # ✅ 위젯 상태 직접 세팅


def apply_dept_autoselect(dept: str, checked: bool):
    """
        본부 체크/해제 시:
      - target_selected_teams set 업데이트
      - 팀 체크박스(st.session_state) 값까지 강제 동기화
    """
    teams = TEAMS_BY_DEPT.get(dept, [])
    for t in teams:
        team_key = f"dlg_team_{dept}_{t}"
        st.session_state[team_key] = bool(checked)  # ✅ 위젯 상태 동기화
        if checked:
            st.session_state.target_selected_teams.add(t)
        else:
            st.session_state.target_selected_teams.discard(t)


# -------------------------
# 팝업 대상 선택 모달
# -------------------------
@st.dialog("팝업 발송 대상 선택", width="large")
def target_dialog():
    # 예약 전송 시간 기본값
    st.session_state.setdefault("popup_expected_send_time", "오전 10시")

    # 헤더 라인 오른쪽 라디오 (CSS/디자인 수정 없음)
    h1, h2 = st.columns([3.2, 1.8], gap="small")
    with h1:
        st.markdown("### 예약 전송 시간 선택")
    with h2:
        st.radio(
            "",
            ["오전 10시", "오후 2시"],
            horizontal=True,
            key="popup_expected_send_time",
        )

    left, right = st.columns([1, 1], gap="large")

    # -------------------------
    # 본부 선택 (value= 미사용 / session_state 키 단일화)
    # -------------------------
    with left:
        st.markdown("### 본부 선택")
        dept_box = st.container(border=True, height=420)
        with dept_box:
            for dept in DEPARTMENTS:
                dept_key = f"dlg_dept_{dept}"

                # set 기준 초기값을 위젯 상태로 넣어줌 (딱 1번)
                prev = dept in st.session_state.target_selected_departments
                st.session_state.setdefault(dept_key, prev)

                checked = st.checkbox(dept, key=dept_key)

                # 변경 감지
                if checked != prev:
                    if checked:
                        st.session_state.target_selected_departments.add(dept)
                    else:
                        st.session_state.target_selected_departments.discard(dept)

                    # 본부 → 하위 팀 전체 동기화 (rerun 없이 유지)
                    apply_dept_autoselect(dept, checked)

    # -------------------------
    # 팀 선택 (value= 미사용 / session_state 키 단일화)
    # -------------------------
    with right:
        st.markdown("### 팀 선택")
        team_box = st.container(border=True, height=420)
        with team_box:
            for dept, teams in TEAMS_BY_DEPT.items():
                st.markdown(f"**{dept}**")
                for t in teams:
                    team_key = f"dlg_team_{dept}_{t}"

                    prev = (t in st.session_state.target_selected_teams)
                    st.session_state.setdefault(team_key, prev)

                    checked = st.checkbox(t, key=team_key)

                    if checked:
                        st.session_state.target_selected_teams.add(t)
                    else:
                        st.session_state.target_selected_teams.discard(t)

                st.divider()

    st.divider()
    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("취소", use_container_width=True):
            reset_targets()
            st.session_state.open_target_dialog = False
            st.rerun()

    with c2:
        if st.button("선택한 대상에게 팝업 발송", type="primary", use_container_width=True):
            post = st.session_state.last_saved_post
            expected_send_time = st.session_state.get("popup_expected_send_time", "오전 10시")

            service.create_popup(
                post,
                sorted(st.session_state.target_selected_departments),
                sorted(st.session_state.target_selected_teams),
                expected_send_time=expected_send_time,
            )

            reset_targets()
            st.session_state.last_saved_post = None
            st.session_state.open_target_dialog = False
            st.session_state.admin_menu = "게시판"
            st.success("중요공지 등록 및 팝업 발송 완료")
            st.rerun()


def on_menu_change(new_menu: str):
    st.session_state.admin_menu = new_menu
    st.session_state.selected_post_id = None


# 왼쪽 네비
portal_sidebar(role="ADMIN", active_menu=st.session_state.admin_menu, on_menu_change=on_menu_change)

# 상단바
render_topbar("전사 Portal")

menu = st.session_state.admin_menu


# -------------------------
# 홈 카드
# -------------------------
def render_home_cards():
    a, b, c = st.columns([1.25, 3.25, 1.25], gap="large")

    with a:
        box = st.container(border=True)
        with box:
            info_card(
                title="사용자 정보",
                subtitle="관리자 계정",
                lines=[("권한", "ADMIN"), ("상태", "로그인")],
                badge="ADMIN",
            )

    with b:
        box = st.container(border=True)
        with box:
            info_card(
                title="전사게시판",
                subtitle="공지 목록/상세 확인",
                lines=[("기능", "공지 조회/상세"), ("권한", "관리자 작성 / 직원 조회")],
            )
            if st.button("게시판 바로가기", type="primary", key="go_board_admin"):
                on_menu_change("게시판")
                st.rerun()

    with c:
        box = st.container(border=True)
        with box:
            app_links_card("업무사이트 (데모)", ["e-Accounting", "JDE ERP", "HRM", "e-Procurement"], role="ADMIN")


if menu == "홈":
    render_home_cards()
    st.write("")
    st.divider()


# -------------------------
# 실제 기능 영역
# -------------------------
if menu == "홈":
    st.subheader("관리자 홈")
    st.write("좌측 메뉴에서 게시판/글쓰기를 선택하세요.")

elif menu == "게시판":

    def _clear_admin_board_selection():
        if "admin_board_table" in st.session_state:
            try:
                st.session_state.admin_board_table["selection"]["rows"] = []
            except Exception:
                pass

    if st.session_state.selected_post_id:
        st.subheader("게시글 상세")
        pid = int(st.session_state.selected_post_id)

        # 최초 1회만 조회수 증가
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
                # 첨부 표시
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

                            # 이미지면 미리보기
                            if mime.startswith("image/"):
                                st.image(data, caption=name)

                            st.download_button(
                                label=f"다운로드: {name}",
                                data=data,
                                file_name=name,
                                mime=a.get("mimeType", "") or None,
                                key=f"dl_admin_{a['fileId']}",
                            )
                        except Exception as e:
                            st.warning(f"파일을 찾을 수 없습니다: {name} ({str(e)})")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("목록으로", type="primary", use_container_width=True, key="admin_back_to_list"):
                st.session_state.selected_post_id = None
                _clear_admin_board_selection()
                st.rerun()
        with c2:
            if st.button("수정", use_container_width=True, key="admin_edit_post"):
                st.session_state.admin_menu = "수정"
                st.rerun()
        with c3:
            if st.button("삭제", use_container_width=True, key="admin_delete_post"):
                if service.delete_post(pid):
                    st.success("게시글이 삭제되었습니다.")
                    st.session_state.selected_post_id = None
                    _clear_admin_board_selection()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("삭제 실패")
        with c4:
            if st.button("새글쓰기", use_container_width=True, key="admin_go_write"):
                on_menu_change("글쓰기")
                st.rerun()

    else:
        head_l, head_r = st.columns([6, 1.2])
        with head_l:
            st.subheader("게시판 홈")
        with head_r:
            if st.button("새글쓰기", type="primary", use_container_width=True, key="admin_write_btn"):
                on_menu_change("글쓰기")
                st.rerun()

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
                    
                    # 제목 (버튼으로 구현)
                    if row_c2.button(
                        p["title"], 
                        key=f"admin_post_title_{p['postId']}", 
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
                    
                    st.markdown("<hr style='margin: 0.2rem 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)

elif menu == "글쓰기":
    st.subheader("새글쓰기")

    ntype = st.radio("공지 유형", ["중요", "일반"], index=0, horizontal=True)
    title = st.text_input("제목", value="", key="w_title")
    content = st.text_area("내용", value="", height=220, key="w_content")
    files = st.file_uploader("첨부파일(이미지/파일)", accept_multiple_files=True, key="w_files")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("등록", type="primary", use_container_width=True):
            if not title.strip() or not content.strip():
                st.error("제목과 내용을 입력해주세요.")
            else:
                post_info = service.save_post(title.strip(), content.strip(), ntype, uploaded_files=files)
                st.session_state.last_saved_post = post_info

                if ntype == "중요":
                    select_all_targets()
                    st.session_state.open_target_dialog = True
                else:
                    st.success("일반 공지 등록 완료")
                    on_menu_change("게시판")
                st.rerun()

    with c2:
        if st.button("취소", use_container_width=True):
            on_menu_change("게시판")
            st.rerun()

    if st.session_state.open_target_dialog:
        st.session_state.open_target_dialog = False
        target_dialog()

elif menu == "수정":
    st.subheader("게시글 수정")

    # 선택된 게시글 ID 가져오기
    post_id = st.session_state.selected_post_id
    if not post_id:
        st.error("수정할 게시글을 선택해주세요.")
        if st.button("게시판으로 돌아가기"):
            on_menu_change("게시판")
            st.rerun()
    else:
        # 기존 게시글 데이터 로드
        post = service.get_post_by_id(post_id)
        if not post:
            st.error("게시글을 찾을 수 없습니다.")
            if st.button("게시판으로 돌아가기"):
                on_menu_change("게시판")
                st.rerun()
        else:
            # 기존 데이터로 초기화
            current_type_idx = 0 if post["type"] == "중요" else 1
            ntype = st.radio("공지 유형", ["중요", "일반"], index=current_type_idx, horizontal=True, key="edit_type")
            title = st.text_input("제목", value=post["title"], key="edit_title")
            content = st.text_area("내용", value=post["content"], height=220, key="edit_content")

            # 기존 첨부파일 표시
            existing_attachments = post.get("attachments", [])
            if existing_attachments:
                st.markdown("**기존 첨부파일**")
                for att in existing_attachments:
                    st.caption(f"📎 {att['filename']} ({att['fileSize']} bytes)")

            # 새 첨부파일 업로드 (기존 파일에 추가)
            files = st.file_uploader("추가 첨부파일(이미지/파일)", accept_multiple_files=True, key="edit_files")

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("수정 완료", type="primary", use_container_width=True, key="edit_submit"):
                    if not title.strip() or not content.strip():
                        st.error("제목과 내용을 입력해주세요.")
                    else:
                        if service.update_post(post_id, title.strip(), content.strip(), ntype, uploaded_files=files):
                            st.success("게시글이 수정되었습니다.")
                            time.sleep(1)
                            st.session_state.admin_menu = "게시판"
                            st.rerun()
                        else:
                            st.error("수정 실패")

            with c2:
                if st.button("취소", use_container_width=True, key="edit_cancel"):
                    on_menu_change("게시판")
                    st.rerun()

elif menu == "문의관리":
    from core.config import DEPARTMENT_EMAILS

    def _clear_inquiry_selection():
        if "inquiry_table" in st.session_state:
            try:
                st.session_state.inquiry_table["selection"]["rows"] = []
            except Exception:
                pass

    if st.session_state.selected_inquiry_id:
        # 문의 상세 보기
        st.subheader("문의 상세")
        inquiry_id = int(st.session_state.selected_inquiry_id)
        inquiry = service.get_inquiry_by_id(inquiry_id)

        box = st.container(border=True)
        with box:
            if not inquiry:
                st.error("문의를 찾을 수 없습니다.")
            else:
                # 상태 배지
                status_badge = "🟢 처리완료" if inquiry["status"] == "completed" else "🔴 대기중"
                st.markdown(f"### {status_badge}")
                st.divider()

                # 문의자 정보
                st.markdown("**📋 문의자 정보**")
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    st.caption("이름")
                    st.write(inquiry["employeeName"])
                with col2:
                    st.caption("직원 ID")
                    st.write(inquiry["employeeId"])
                with col3:
                    st.caption("소속")
                    st.write(inquiry["employeeTeam"] or "N/A")

                st.divider()

                # 문의 내용
                st.markdown("**💬 원본 질문**")
                st.info(inquiry["userQuery"])

                st.markdown("**📧 문의 대상 부서**")
                st.write(inquiry["department"])

                st.markdown("**📝 문의 내용**")
                content_box = st.container(border=True, height=300)
                with content_box:
                    st.write(inquiry["content"])

                st.caption(f"접수일시: {fmt_dt(inquiry['createdAt'])}")

        # 버튼
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            if st.button("목록으로", type="primary", use_container_width=True, key="inquiry_back"):
                st.session_state.selected_inquiry_id = None
                _clear_inquiry_selection()
                st.rerun()

        with col2:
            if inquiry and inquiry["status"] == "pending":
                if st.button("✅ 처리완료로 변경", use_container_width=True, key="inquiry_complete"):
                    if service.update_inquiry_status(inquiry_id, "completed"):
                        st.success("처리완료로 변경되었습니다.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("상태 변경 실패")

        with col3:
            if inquiry and inquiry["status"] == "completed":
                if st.button("🔄 대기중으로 변경", use_container_width=True, key="inquiry_pending"):
                    if service.update_inquiry_status(inquiry_id, "pending"):
                        st.success("대기중으로 변경되었습니다.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("상태 변경 실패")

    else:
        # 문의 목록
        st.subheader("📧 문의관리")

        # 필터
        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 4])
        with filter_col1:
            status_filter = st.selectbox(
                "상태",
                ["전체", "대기중", "처리완료"],
                key="inquiry_status_select"
            )
            # 매핑
            status_map = {
                "전체": None,
                "대기중": "pending",
                "처리완료": "completed"
            }
            actual_status = status_map[status_filter]

        with filter_col2:
            dept_options = ["전체"] + list(DEPARTMENT_EMAILS.keys())
            dept_filter = st.selectbox(
                "부서",
                dept_options,
                key="inquiry_dept_select"
            )
            actual_dept = None if dept_filter == "전체" else dept_filter

        # 목록 조회
        inquiries = service.list_inquiries(status=actual_status, department=actual_dept)

        box = st.container(border=True)
        with box:
            st.markdown("**접수된 문의 목록**")

            if not inquiries:
                st.info("접수된 문의가 없습니다.")
            else:
                # 통계
                total = len(inquiries)
                pending = sum(1 for i in inquiries if i["status"] == "pending")
                completed = total - pending

                stat_col1, stat_col2, stat_col3 = st.columns([1, 1, 1])
                with stat_col1:
                    st.metric("전체", f"{total}건")
                with stat_col2:
                    st.metric("대기중", f"{pending}건", delta=None if pending == 0 else f"{pending}")
                with stat_col3:
                    st.metric("처리완료", f"{completed}건")

                st.divider()

                # 테이블
                table_rows = []
                for inq in inquiries:
                    status_label = "처리완료" if inq["status"] == "completed" else "대기중"
                    table_rows.append({
                        "번호": inq["id"],
                        "상태": status_label,
                        "부서": inq["department"],
                        "문의자": inq["employeeName"],
                        "질문": inq["userQuery"][:50] + "..." if len(inq["userQuery"]) > 50 else inq["userQuery"],
                        "접수일시": fmt_dt(inq["createdAt"]),
                    })

                event = st.dataframe(
                    table_rows,
                    width="stretch",
                    hide_index=True,
                    key="inquiry_table",
                    on_select="rerun",
                    selection_mode="single-row",
                )

                try:
                    if event is not None and event.selection.rows:
                        row_idx = event.selection.rows[0]
                        clicked_inquiry_id = int(table_rows[row_idx]["번호"])
                        st.session_state.selected_inquiry_id = clicked_inquiry_id
                        st.rerun()
                except Exception:
                    pass

        # -------------------------
        # 챗봇 질문 키워드 통계
        # -------------------------
        st.markdown("---")
        st.subheader("📊 챗봇 질문 키워드 통계")
        
        stats = service.get_chatbot_keyword_stats()
        
        if not stats or not stats.get("전체"):
            st.info("아직 수집된 챗봇 데이터가 없습니다. 직원이 챗봇에게 질문하면 데이터가 쌓입니다.")
        else:
            # 팀 목록 생성
            team_options = sorted([k for k in stats.keys() if k != "전체"])
            team_options.insert(0, "전체") # 전체를 맨 앞으로
            
            col_stat_1, col_stat_2 = st.columns([1, 3])
            
            with col_stat_1:
                selected_team = st.selectbox("통계를 확인할 부서/팀", team_options)
            
            # 선택된 팀의 데이터
            team_stat = stats.get(selected_team, {})
            
            if not team_stat:
                st.warning(f"{selected_team}의 데이터가 없습니다.")
            else:
                with col_stat_2:
                    st.caption(f"'{selected_team}'에서 주로 사용된 챗봇 키워드 Top 20")
                    
                    # 빈도수 기준 내림차순 정렬 (Top 20)
                    sorted_items = sorted(team_stat.items(), key=lambda x: x[1], reverse=True)[:20]
                    
                    # DataFrame 생성
                    df = pd.DataFrame(sorted_items, columns=["키워드", "빈도"])
                    
                    # 막대 그래프 (Chart)
                    st.bar_chart(df.set_index("키워드"), color="#FF4B4B")
                
                # 상세 데이터 (접기)
                with st.expander("📋 상세 데이터 보기"):
                    st.dataframe(df, use_container_width=True, hide_index=True)


