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
    파일명을 안전한 형식으로 변환 (한글 제거, 영문/숫자만 허용)

    Args:
        name: 원본 파일명

    Returns:
        안전한 파일명 (영문, 숫자, 언더스코어, 하이픈, 점만 포함)
    """
    import re
    from pathlib import Path

    name = (name or "").strip()
    if not name:
        return "file"

    # 파일명과 확장자 분리
    p = Path(name)
    stem = p.stem  # 확장자 제외한 파일명
    ext = p.suffix  # 확장자 (.png, .jpg 등)

    # 영문, 숫자, 언더스코어, 하이픈만 허용 (한글 및 특수문자 제거)
    safe_stem = re.sub(r'[^a-zA-Z0-9_-]', '_', stem)

    # 연속된 언더스코어 제거
    safe_stem = re.sub(r'_+', '_', safe_stem)

    # 앞뒤 언더스코어 제거
    safe_stem = safe_stem.strip('_')

    # 빈 문자열이면 기본값
    if not safe_stem:
        safe_stem = "file"

    # 확장자도 소문자로 정리
    safe_ext = ext.lower()

    return f"{safe_stem}{safe_ext}"

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
        
        # target_users (개별 사용자 타겟팅)
        # 키가 없을 수 있으므로 get 사용
        user_targets = _parse_csv(str(p.get("target_users") or ""))

        # 최종 룰:
        # 1) 유저 지정 -> 유저 매칭 (최우선)
        # 2) 팀 지정 -> 팀 기준
        # 3) 팀 없음 + 본부 지정 -> 본부 기준
        # 4) 모두 없음 -> 발송 안 함 (또는 전체? 현재는 안 함)
        
        matches = False
        
        if user_targets:
            if employee_id in user_targets:
                matches = True
            else:
                matches = False # 다른 사람 타겟팅임
        elif team_targets:
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
                file_path = img.get("filePath", "")
                # URL인지 로컬 경로인지 구분하여 올바른 키로 전달
                if file_path.startswith("http://") or file_path.startswith("https://"):
                    payload["imageUrl"] = file_path  # R2 URL
                else:
                    payload["imagePath"] = file_path  # 로컬 파일 경로

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


# -------------------------
# 문의(Inquiry)
# -------------------------
def save_inquiry(employee_id: str, department: str, user_query: str, content: str) -> bool:
    """
    담당자 문의 저장

    Args:
        employee_id: 직원 ID
        department: 문의 대상 부서
        user_query: 원본 질문
        content: 문의 내용

    Returns:
        성공 여부
    """
    ts = now_ms()

    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO inquiries(employee_id, department, user_query, content, status, created_at)
                VALUES(?,?,?,?,?,?)
                """,
                (employee_id, department, user_query, content, "pending", ts),
            )
        return True
    except Exception as e:
        print(f"문의 저장 실패: {e}")
        return False

def list_inquiries(status: Optional[str] = None, department: Optional[str] = None) -> List[Dict]:
    """
    문의 목록 조회

    Args:
        status: 상태 필터 ('pending' | 'completed' | None=전체)
        department: 부서 필터 (None=전체)

    Returns:
        문의 목록 (최신순)
    """
    with get_conn() as conn:
        query = """
            SELECT i.id, i.employee_id, i.department, i.user_query, i.content,
                   i.status, i.created_at, e.name as employee_name
            FROM inquiries i
            LEFT JOIN employees e ON i.employee_id = e.employee_id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND i.status = ?"
            params.append(status)

        if department:
            query += " AND i.department = ?"
            params.append(department)

        query += " ORDER BY i.created_at DESC"

        cur = conn.execute(query, params)
        rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "id": int(r["id"]),
            "employeeId": r["employee_id"] or "guest",
            "employeeName": r["employee_name"] or "게스트",
            "department": r["department"],
            "userQuery": r["user_query"],
            "content": r["content"],
            "status": r["status"],
            "createdAt": int(r["created_at"]),
        })
    return result

def get_inquiry_by_id(inquiry_id: int) -> Optional[Dict]:
    """
    특정 문의 상세 조회

    Args:
        inquiry_id: 문의 ID

    Returns:
        문의 상세 정보
    """
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT i.id, i.employee_id, i.department, i.user_query, i.content,
                   i.status, i.created_at, i.answer, i.answered_at,
                   e.name as employee_name, e.team as employee_team
            FROM inquiries i
            LEFT JOIN employees e ON i.employee_id = e.employee_id
            WHERE i.id = ?
            """,
            (int(inquiry_id),),
        )
        r = cur.fetchone()

    if not r:
        return None

    return {
        "id": int(r["id"]),
        "employeeId": r["employee_id"] or "guest",
        "employeeName": r["employee_name"] or "게스트",
        "employeeTeam": r["employee_team"] or "",
        "department": r["department"],
        "userQuery": r["user_query"],
        "content": r["content"],
        "status": r["status"],
        "createdAt": int(r["created_at"]),
        "answer": r["answer"],
        "answeredAt": int(r["answered_at"] or 0),
    }

def update_inquiry_status(inquiry_id: int, new_status: str) -> bool:
    """
    문의 상태 업데이트

    Args:
        inquiry_id: 문의 ID
        new_status: 새 상태 ('pending' | 'completed')

    Returns:
        성공 여부
    """
    if new_status not in ["pending", "completed"]:
        return False

    try:
        with get_conn() as conn:
            cur = conn.execute(
                "UPDATE inquiries SET status = ? WHERE id = ?",
                (new_status, int(inquiry_id)),
            )
            return cur.rowcount > 0
    except Exception as e:
        print(f"문의 상태 업데이트 실패: {e}")
        return False

# -------------------------
# 챗봇 세션 관리 (DB 기반)
# -------------------------
def create_chat_session(user_id: str, name: str = "새 대화") -> str:
    """새 대화 세션 생성"""
    import uuid
    session_id = str(uuid.uuid4())
    ts = now_ms()
    
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions(session_id, user_id, name, created_at, updated_at)
            VALUES(?,?,?,?,?)
            """,
            (session_id, user_id, name, ts, ts),
        )
    return session_id

def get_user_chat_sessions(user_id: str) -> List[Dict]:
    """사용자의 대화 세션 목록 조회"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT session_id, user_id, name, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        
    result = []
    for r in rows:
        result.append({
            "session_id": r["session_id"],
            "user_id": r["user_id"],
            "name": r["name"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return result

def update_chat_session_name(session_id: str, name: str) -> bool:
    """세션 이름 변경"""
    ts = now_ms()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE chat_sessions SET name = ?, updated_at = ? WHERE session_id = ?",
            (name, ts, session_id),
        )
        return cur.rowcount > 0

def delete_chat_session(session_id: str) -> bool:
    """세션 삭제"""
    with get_conn() as conn:
        # FK ON DELETE CASCADE가 동작하지 않을 수 있으므로 메시지 먼저 삭제
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cur = conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        return cur.rowcount > 0

def add_chat_message(session_id: str, role: str, content: str, notice_refs: List[int] = None, notice_details: List[Dict] = None) -> bool:
    """메시지 추가"""
    ts = now_ms()
    import json
    
    refs_json = json.dumps(notice_refs) if notice_refs else None
    details_json = json.dumps(notice_details, ensure_ascii=False) if notice_details else None
    
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages(session_id, role, content, notice_refs, notice_details, created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (session_id, role, content, refs_json, details_json, ts),
        )
        # 세션 업데이트 시간 갱신
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?", (ts, session_id))
        
    return True

def get_chat_messages(session_id: str) -> List[Dict]:
    """세션의 메시지 목록 조회"""
    import json
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT role, content, notice_refs, notice_details, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        
    result = []
    for r in rows:
        refs = []
        if r["notice_refs"]:
            try:
                refs = json.loads(r["notice_refs"])
            except:
                pass
                
        details = []
        if r["notice_details"]:
            try:
                details = json.loads(r["notice_details"])
            except:
                pass
        
        result.append({
            "role": r["role"],
            "content": r["content"],
            "notice_refs": refs,
            "notice_details": details,
            "created_at": r["created_at"],
        })
    return result

def get_chatbot_keyword_stats() -> Dict[str, Dict[str, int]]:
    """
    챗봇 로그에서 팀별 키워드 통계 추출
    Returns:
        {
            "전체": {"연차": 10, "휴가": 5, ...},
            "연구1팀": {"특허": 3, ...},
            ...
        }
    """
    import json
    from collections import Counter
    
    with get_conn() as conn:
        # user_id로 팀 정보 조인
        # chat_logs가 비어있으면 결과 없음
        try:
            query = """
                SELECT l.keywords, e.team, e.department
                FROM chat_logs l
                LEFT JOIN employees e ON l.user_id = e.employee_id
                ORDER BY l.created_at DESC
            """
            cur = conn.execute(query)
            rows = cur.fetchall()
        except Exception as e:
            # 테이블이 없거나 에러 발생 시 빈 결과 반환
            print(f"키워드 통계 조회 실패: {e}")
            return {}

    stats = {"전체": Counter()}
    
    # 불용어 정의 (통계 후처리용)
    STOPWORDS = {
        '은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '으로', '로', '에서', '부터', '까지',
        '있다', '없다', '이다', '아니다', '하다', '되다', '않다', '같다', '싶다',
        '알려줘', '알려주세요', '알려', '주세요', '해주세요', '해줘', '보여줘', '보여주세요',
        '무엇', '무엇인가요', '어디', '어디서', '언제', '누구', '어떻게', '왜', 
        '궁금해', '궁금해요', '질문', '문의', '사항', '관련', '대한', '대해', '대하여',
        '안녕', '안녕하세요', '반가워', '반갑습니다', '감사', '고마워',
        '공지', '사항', '확인', '방법', '좀', '수', '할', '한', '데', '건', '것',
        '저', '나', '너', '우리', '그', '이', '저', '요', '네', '아니요',
        '이번', '저번', '다음', '오늘', '내일', '어제', '지금', '현재',
        '있어', '있나', '있니', '있나요', '없어', '없나', '없니', '없나요',
        '??', '?!', '??', '..', '...',
        '공지를', '공지사항', '최근', '뭐가', '뭔가', '알려줄래', '어떤', '어떤게',
        '관련하여', '내용', '내용이', '불러와줘', '얼마야', '얼마'
    }
    
    # 제거할 조사 목록
    JOSAS = ['은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '으로', '로', '에서', '도', '만']

    import re

    for r in rows:
        keywords_json = r["keywords"]
        team = r["team"] or "기타"
        
        try:
            keywords = json.loads(keywords_json)
            # 리스트가 아니면 패스
            if not isinstance(keywords, list):
                continue
        except:
            continue
            
        if not keywords:
            continue
            
        if team not in stats:
            stats[team] = Counter()
            
        for k in keywords:
            k = str(k).strip()
            if not k:
                continue
            
            # 1. 특수문자 제거
            k_clean = re.sub(r'[^가-힣a-zA-Z0-9]', '', k)
            
            # 2. 길이 체크 및 1차 불용어 체크
            if len(k_clean) < 2:
                continue
                
            if k in STOPWORDS or k_clean in STOPWORDS:
                continue
            
            # 3. 조사(Josa) 제거 로직 (Simple Stemming)
            # '자동차를' -> '자동차', '학교에서' -> '학교'
            cand = k_clean
            for josa in JOSAS:
                if cand.endswith(josa):
                    # 조사를 제거했을 때 2글자 이상 남아야 함
                    temp = cand[:-len(josa)]
                    if len(temp) >= 2:
                        cand = temp
                        break # 하나만 제거하고 중단 (중복 조사 처리 안함)
            
            # 조사 제거 후 다시 불용어 체크
            if cand in STOPWORDS:
                continue
                
            stats["전체"][cand] += 1
            stats[team][cand] += 1
            
    # Counter 객체를 dict로 변환하여 반환
    return {k: dict(v) for k, v in stats.items()}

def create_user_alarm(target_user_id: str, title: str, content: str, author: str = "SYSTEM") -> bool:
    """사용자에게 알림(ALARM 타입 팝업) 발송"""
    ts = now_ms()
    popup_id = ts
    
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO popups(popup_id, post_id, title, content, target_users, created_at, type)
                VALUES(?, 0, ?, ?, ?, ?, 'ALARM')
                """,
                (popup_id, title, content, target_user_id, ts),
            )
        return True
    except Exception as e:
        print(f"알림 발송 실패: {e}")
        return False

def answer_inquiry(inquiry_id: int, answer: str, admin_id: str) -> bool:
    """문의 답변 및 알림 발송"""
    ts = now_ms()
    
    try:
        with get_conn() as conn:
            # 1. 문의 업데이트
            conn.execute(
                "UPDATE inquiries SET answer = ?, answered_at = ?, answerer_id = ?, status = 'completed' WHERE id = ?",
                (answer, ts, admin_id, int(inquiry_id))
            )

            # 2. 문의자 정보 조회
            cur = conn.execute("SELECT employee_id, user_query FROM inquiries WHERE id = ?", (int(inquiry_id),))
            row = cur.fetchone()
            
            if row:
                emp_id = row['employee_id']
                uq = row['user_query']
                q_summary = uq[:30] + "..." if len(uq) > 30 else uq
                
                content_md = f"**[문의 내용]**\n{q_summary}\n\n**[답변 내용]**\n{answer}"
                
                create_user_alarm(emp_id, "문의 답변 알림", content_md, author=admin_id)
                
        return True
    except Exception as e:
        print(f"답변 등록 실패: {e}")
        return False
