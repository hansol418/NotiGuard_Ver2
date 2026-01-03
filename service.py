from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

from core.db import get_conn

# 관리자 계정 (데모)
ADMIN_ID = "admin"
ADMIN_PW = "1234"

def now_ms() -> int:
    return int(time.time() * 1000)

# -------------------------
# B방식: 공통 로그인 함수 1개
# -------------------------
from core.auth import verify_password

def login_account(login_id: str, pw: str) -> Optional[Dict]:
    """
    공통 로그인(ADMIN/EMPLOYEE 모두 비밀번호 검증):
      1) accounts에서 login_id 조회
      2) verify_password로 pw 검증
      3) role에 따라 세션 정보 반환
    """
    login_id = (login_id or "").strip()
    pw = (pw or "").strip()

    if not login_id or not pw:
        return None

    with get_conn() as conn:
        cur = conn.execute(
            "SELECT login_id, password_hash, role, employee_id FROM accounts WHERE login_id = ?",
            (login_id,),
        )
        acc = cur.fetchone()

    if not acc:
        return None

    if not verify_password(pw, acc["password_hash"]):
        return None

    role = acc["role"]

    if role == "ADMIN":
        return {"role": "ADMIN"}

    if role == "EMPLOYEE":
        emp_id = acc["employee_id"]
        if not emp_id:
            return None

        emp = get_employee_info(emp_id)
        if not emp:
            return None

        return {"role": "EMPLOYEE", "employee": emp}

    return None


# -------------------------
# 첨부파일(저장 경로)
# -------------------------
UPLOAD_DIR = Path("uploads")

def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _safe_filename(name: str) -> str:
    """
    파일명에 들어가면 위험한 문자 최소 제거
    """
    name = (name or "").strip()
    if not name:
        return "file"
    # 아주 기본적인 정리만(윈도우/리눅스 공통 문제 문자 제거)
    bad = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for b in bad:
        name = name.replace(b, "_")
    return name

def save_attachments(post_id: int, uploaded_files: List[Any]) -> None:
    """
    Streamlit UploadedFile 리스트를 받아서:
      1) 로컬(uploads/) 또는 R2에 저장 (환경 자동 감지)
      2) notice_files 테이블에 메타데이터 저장
    """
    if not uploaded_files:
        return

    from core.storage import save_file
    import io

    ts = now_ms()

    with get_conn() as conn:
        for uf in uploaded_files:
            # uf: streamlit.runtime.uploaded_file_manager.UploadedFile
            orig_name = _safe_filename(getattr(uf, "name", "") or "file")
            mime = getattr(uf, "type", "") or ""
            data = uf.getbuffer()
            size = int(len(data))

            # 저장 파일명: postid_timestamp_originalname
            save_name = f"{int(post_id)}_{ts}_{orig_name}"

            # BytesIO로 변환
            file_io = io.BytesIO(data)

            # 환경에 따라 로컬 또는 R2에 저장
            # 반환값: 로컬 경로 또는 R2 URL
            file_path_or_url = save_file(
                file_data=file_io,
                filename=save_name,
                folder="uploads",
                content_type=mime
            )

            # DB 저장
            conn.execute(
                """
                INSERT INTO notice_files(post_id, filename, mime_type, file_path, file_size, uploaded_at)
                VALUES(?,?,?,?,?,?)
                """,
                (int(post_id), orig_name, mime, file_path_or_url, size, ts),
            )

def list_attachments(post_id: int) -> List[Dict]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT file_id, post_id, filename, mime_type, file_path, file_size, uploaded_at
            FROM notice_files
            WHERE post_id = ?
            ORDER BY file_id ASC
            """,
            (int(post_id),),
        )
        rows = cur.fetchall()

    res: List[Dict] = []
    for r in rows:
        res.append({
            "fileId": int(r["file_id"]),
            "postId": int(r["post_id"]),
            "filename": r["filename"],
            "mimeType": r["mime_type"],
            "filePath": r["file_path"],
            "fileSize": int(r["file_size"] or 0),
            "uploadedAt": int(r["uploaded_at"] or 0),
        })
    return res

def get_first_image_attachment(post_id: int) -> Optional[Dict]:
    """
    해당 post_id의 첨부파일 중 첫 번째 이미지 파일 1개 반환
    """
    files = list_attachments(int(post_id))
    for f in files:
        mime = (f.get("mimeType", "") or "").lower()
        if mime.startswith("image/"):
            return f
    return None


# -------------------------
# 공지(Notice)
# -------------------------
def save_post(title: str, content: str, ntype: str, uploaded_files: Optional[List[Any]] = None) -> Dict:
    ts = now_ms()
    post_id = ts
    author = "관리자"
    safe_type = "중요" if ntype == "중요" else "일반"

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notices(post_id, created_at, type, title, content, author, views)
            VALUES(?,?,?,?,?,?,0)
            """,
            (post_id, ts, safe_type, title, content, author),
        )

    #  첨부 저장
    if uploaded_files:
        save_attachments(post_id, uploaded_files)

    return {
        "postId": post_id,
        "popupId": post_id,
        "title": title,
        "content": content,
        "type": safe_type,
        "author": author,
        "timestamp": ts,
    }

def list_posts() -> List[Dict]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM notices ORDER BY post_id DESC")
        rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "postId": r["post_id"],
            "timestamp": r["created_at"],
            "type": r["type"],
            "title": r["title"],
            "content": r["content"],
            "author": r["author"],
            "views": int(r["views"] or 0),
        })
    return result

def get_post_by_id(post_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM notices WHERE post_id = ?", (int(post_id),))
        r = cur.fetchone()
    if not r:
        return None

    # 첨부 목록 포함해서 반환
    attachments = list_attachments(int(post_id))

    return {
        "postId": r["post_id"],
        "timestamp": r["created_at"],
        "type": r["type"],
        "title": r["title"],
        "content": r["content"],
        "author": r["author"],
        "views": int(r["views"] or 0),
        "attachments": attachments,
    }

def increment_views(post_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("UPDATE notices SET views = views + 1 WHERE post_id = ?", (int(post_id),))
        return cur.rowcount > 0

def update_post(post_id: int, title: str, content: str, ntype: str, uploaded_files: Optional[List[Any]] = None) -> bool:
    """
    게시글 수정

    Args:
        post_id: 게시글 ID
        title: 수정할 제목
        content: 수정할 내용
        ntype: 수정할 공지 유형 ("중요" | "일반")
        uploaded_files: 추가할 첨부파일 (기존 파일은 유지)

    Returns:
        성공 여부
    """
    safe_type = "중요" if ntype == "중요" else "일반"

    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE notices
            SET title = ?, content = ?, type = ?
            WHERE post_id = ?
            """,
            (title, content, safe_type, int(post_id)),
        )
        success = cur.rowcount > 0

    # 새 첨부파일 추가 (기존 파일은 유지)
    if success and uploaded_files:
        save_attachments(int(post_id), uploaded_files)

    return success

def delete_post(post_id: int) -> bool:
    """
    게시글 삭제 (첨부파일 및 연관된 팝업도 CASCADE로 삭제됨)

    Args:
        post_id: 삭제할 게시글 ID

    Returns:
        성공 여부
    """
    # 첨부파일 물리적 삭제
    attachments = list_attachments(int(post_id))
    for att in attachments:
        file_path = att.get("filePath", "")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    # DB 삭제 (FK CASCADE로 notice_files, popups, popup_logs도 자동 삭제)
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notices WHERE post_id = ?", (int(post_id),))
        return cur.rowcount > 0

# -------------------------
# 팝업(Popup)
# -------------------------
def create_popup(post_info: Dict, selected_departments: List[str], selected_teams: List[str], expected_send_time: str = "") -> bool:
    popup_id = int(post_info["popupId"])
    post_id = int(post_info["postId"])
    title = str(post_info["title"])
    content = str(post_info["content"])
    dept_csv = ",".join(selected_departments or [])
    team_csv = ",".join(selected_teams or [])
    ts = now_ms()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO popups(popup_id, post_id, title, content, target_departments, target_teams, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (popup_id, post_id, title, content, dept_csv, team_csv, ts),
        )
    return True


# -------------------------
# 직원(Employee)
# -------------------------
def get_employee_info(employee_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        r = cur.fetchone()
    if not r:
        return None
    return {
        "employeeId": r["employee_id"],
        "name": r["name"],
        "department": r["department"],
        "team": r["team"],
        "ignoreRemaining": int(r["ignore_remaining"] or 0),
    }

def _parse_csv(csv: str) -> List[str]:
    csv = (csv or "").strip()
    if not csv:
        return []
    return [s.strip() for s in csv.split(",") if s.strip()]

def _has_responded(employee_id: str, popup_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT 1 FROM popup_logs
            WHERE employee_id = ? AND popup_id = ?
            LIMIT 1
            """,
            (employee_id, int(popup_id)),
        )
        return cur.fetchone() is not None

def get_latest_popup_for_employee(employee_id: str) -> Optional[Dict]:
    emp = get_employee_info(employee_id)
    if not emp:
        return None

    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM popups ORDER BY created_at DESC")
        popups = cur.fetchall()

    for p in popups:
        popup_id = int(p["popup_id"])
        if _has_responded(employee_id, popup_id):
            continue

        dept_targets = _parse_csv(p["target_departments"])
        team_targets = _parse_csv(p["target_teams"])

        # 최종 룰:
        # 1) 팀 지정 -> 팀 기준
        # 2) 팀 없음 + 본부 지정 -> 본부 기준
        # 3) 둘 다 없음 -> 발송 안 함
        if team_targets:
            matches = (emp["team"] in team_targets)
        elif dept_targets:
            matches = (emp["department"] in dept_targets)
        else:
            matches = False

        if matches:
            post_id = int(p["post_id"])
            img = get_first_image_attachment(post_id)

            payload = {
                "popupId": popup_id,
                "title": p["title"],
                "content": p["content"],
                "ignoreRemaining": emp["ignoreRemaining"],
            }

            # 이미지가 있으면 같이 내려줌 (없으면 필드 자체가 없어도 됨)
            if img:
                payload["imagePath"] = img.get("filePath")  # employee.py가 이걸 읽어서 st.image로 출력

            return payload
    return None


# -------------------------
# 로그(Log)
# -------------------------
def record_popup_action(employee_id: str, popup_id: int, action: str, confirmed: str = "") -> None:
    ts = now_ms()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO popup_logs(created_at, employee_id, popup_id, action, confirmed)
            VALUES(?,?,?,?,?)
            """,
            (ts, employee_id, int(popup_id), action, confirmed or ""),
        )

def confirm_popup_action(employee_id: str, popup_id: int) -> bool:
    record_popup_action(employee_id, popup_id, "확인함", "예")
    return True

def ignore_popup_action(employee_id: str, popup_id: int) -> Dict:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT ignore_remaining FROM employees WHERE employee_id = ?",
            (employee_id,),
        )
        r = cur.fetchone()
        if not r:
            return {"ok": False, "remaining": 0}

        remaining = int(r["ignore_remaining"] or 0)
        if remaining <= 0:
            return {"ok": False, "remaining": 0}

        remaining -= 1
        conn.execute(
            "UPDATE employees SET ignore_remaining = ? WHERE employee_id = ?",
            (remaining, employee_id),
        )

    record_popup_action(employee_id, popup_id, "확인하지 않음", "")
    return {"ok": True, "remaining": remaining}

def log_chatbot_move(employee_id: str, popup_id: int) -> bool:
    record_popup_action(employee_id, popup_id, "챗봇이동", "")
    return True
