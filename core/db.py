# STREAMLIT/core/db.py
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from core.auth import hash_password

# DB 설정
DB_PATH = Path("groupware.db")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# PostgreSQL 사용 여부 (Railway 환경 감지)
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import urllib.parse as urlparse


class PostgresConnectionWrapper:
    """
    PostgreSQL connection wrapper to support SQLite-style execute() calls
    """
    def __init__(self, conn):
        self._conn = conn
        self._cursor = None

    def execute(self, sql, params=None):
        """SQLite-style execute that returns a cursor"""
        if self._cursor is None:
            self._cursor = self._conn.cursor(cursor_factory=RealDictCursor)

        # SQLite 플레이스홀더(?)를 PostgreSQL 플레이스홀더(%s)로 자동 변환
        pg_sql = sql.replace('?', '%s')

        if params:
            self._cursor.execute(pg_sql, params)
        else:
            self._cursor.execute(pg_sql)
        return self._cursor

    def cursor(self, cursor_factory=None):
        """Create a new cursor (for direct cursor usage)"""
        if cursor_factory:
            return self._conn.cursor(cursor_factory=cursor_factory)
        return self._conn.cursor(cursor_factory=RealDictCursor)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        if self._cursor:
            self._cursor.close()
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        return False


@contextmanager
def get_conn():
    """
    환경에 따라 SQLite 또는 PostgreSQL 연결 반환

    - 로컬 개발: SQLite (groupware.db)
    - Railway 배포: PostgreSQL (DATABASE_URL)
    """
    conn = None
    is_postgres = False

    if USE_POSTGRES:
        # PostgreSQL 연결 시도 (Railway)
        try:
            url = urlparse.urlparse(DATABASE_URL)
            pg_conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            # Wrap PostgreSQL connection to support SQLite-style execute()
            conn = PostgresConnectionWrapper(pg_conn)
            is_postgres = True
        except Exception as e:
            print(f"PostgreSQL 연결 실패: {e}")
            print("SQLite로 폴백합니다...")
            conn = None

    # PostgreSQL 연결 실패 시 SQLite 사용
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        is_postgres = False

    # 공통 컨텍스트 매니저 로직
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    데이터베이스 초기화

    - SQLite: schema.sql 실행
    - PostgreSQL: schema_postgres.sql 실행
    """
    if USE_POSTGRES:
        # PostgreSQL 초기화
        _init_postgres()
    else:
        # SQLite 초기화
        _init_sqlite()


def _init_sqlite():
    """SQLite 초기화"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # 1) 스키마 생성/갱신
        schema_path = Path("sql/schema.sql")
        if not schema_path.exists():
            raise FileNotFoundError("sql/schema.sql 파일이 없습니다.")

        conn.executescript(schema_path.read_text(encoding="utf-8"))

        # 2) chat_logs 테이블 추가 (챗봇 통합용)
        _add_chat_logs_table_sqlite(conn)

        # 3) notices 테이블에 department, date 컬럼 추가 (챗봇 통합용)
        _add_notices_columns_sqlite(conn)

        # 4) employees 더미 데이터
        cur = conn.execute("SELECT COUNT(1) AS cnt FROM employees")
        cnt_emp = int(cur.fetchone()["cnt"])
        if cnt_emp == 0:
            conn.execute(
                "INSERT INTO employees(employee_id, name, department, team, ignore_remaining) VALUES (?,?,?,?,?)",
                ("HS001", "김산", "경영관리본부", "재경팀", 3),
            )
            conn.execute(
                "INSERT INTO employees(employee_id, name, department, team, ignore_remaining) VALUES (?,?,?,?,?)",
                ("HS002", "이하나", "연구개발본부", "연구1팀", 3),
            )
            conn.execute(
                "INSERT INTO employees(employee_id, name, department, team, ignore_remaining) VALUES (?,?,?,?,?)",
                ("HS003", "홍길동", "연구개발본부", "연구2팀", 3),
            )

        # 5) accounts 더미 계정
        cur = conn.execute("SELECT COUNT(1) AS cnt FROM accounts")
        cnt_acc = int(cur.fetchone()["cnt"])
        if cnt_acc == 0:
            # 관리자 계정
            conn.execute(
                """
                INSERT INTO accounts(login_id, password_hash, role, employee_id, created_at)
                VALUES (?,?,?,?,?)
                """,
                ("admin", hash_password("1234"), "ADMIN", None, 0),
            )

            # 직원 계정(아이디=사번)
            conn.execute(
                """
                INSERT INTO accounts(login_id, password_hash, role, employee_id, created_at)
                VALUES (?,?,?,?,?)
                """,
                ("HS001", hash_password("1234"), "EMPLOYEE", "HS001", 0),
            )
            conn.execute(
                """
                INSERT INTO accounts(login_id, password_hash, role, employee_id, created_at)
                VALUES (?,?,?,?,?)
                """,
                ("HS002", hash_password("1234"), "EMPLOYEE", "HS002", 0),
            )
            conn.execute(
                """
                INSERT INTO accounts(login_id, password_hash, role, employee_id, created_at)
                VALUES (?,?,?,?,?)
                """,
                ("HS003", hash_password("1234"), "EMPLOYEE", "HS003", 0),
            )

        # 6) popups 테이블 컬럼 보완
        cur = conn.execute("PRAGMA table_info(popups)")
        cols = [row["name"] for row in cur.fetchall()]
        if "expected_send_time" not in cols:
            conn.execute(
                "ALTER TABLE popups ADD COLUMN expected_send_time TEXT NOT NULL DEFAULT '오전 10시'"
            )

        conn.commit()

    finally:
        conn.close()


def _add_chat_logs_table_sqlite(conn):
    """SQLite에 chat_logs 테이블 추가"""
    # 테이블 존재 확인
    cur = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='chat_logs'
    """)
    if cur.fetchone() is None:
        conn.execute("""
            CREATE TABLE chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_query TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                response_type TEXT NOT NULL,
                summary TEXT,
                keywords TEXT,
                notice_refs TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX idx_chat_logs_user ON chat_logs(user_id)
        """)
        conn.execute("""
            CREATE INDEX idx_chat_logs_created ON chat_logs(created_at)
        """)
        print("✅ chat_logs 테이블 생성 완료")


def _add_notices_columns_sqlite(conn):
    """SQLite notices 테이블에 department, date 컬럼 추가"""
    cur = conn.execute("PRAGMA table_info(notices)")
    cols = [row["name"] for row in cur.fetchall()]

    if "department" not in cols:
        conn.execute("ALTER TABLE notices ADD COLUMN department TEXT DEFAULT '전체'")
        print("✅ notices.department 컬럼 추가 완료")

    if "date" not in cols:
        conn.execute("ALTER TABLE notices ADD COLUMN date TEXT")
        conn.execute("""
            UPDATE notices
            SET date = strftime('%Y-%m-%d', created_at/1000, 'unixepoch')
            WHERE date IS NULL
        """)
        print("✅ notices.date 컬럼 추가 완료")


def _init_postgres():
    """PostgreSQL 초기화"""
    schema_path = Path("sql/schema_postgres.sql")
    if not schema_path.exists():
        print(f"⚠️ {schema_path} 파일이 없습니다. 수동으로 DB 초기화가 필요합니다.")
        print("Railway 배포 시 'python init_railway_db.py'를 실행하세요.")
        return

    try:
        url = urlparse.urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cursor = conn.cursor()

        # 스키마 실행
        schema_sql = schema_path.read_text(encoding="utf-8")
        cursor.execute(schema_sql)

        # 기본 관리자 계정 생성
        cursor.execute("""
            INSERT INTO accounts (login_id, password_hash, role, employee_id, created_at)
            VALUES (%s, %s, 'ADMIN', NULL, 0)
            ON CONFLICT (login_id) DO NOTHING
        """, ("admin", hash_password("1234")))

        # 기본 직원 계정 생성
        employees = [
            ("HS001", "김산", "경영관리본부", "재경팀"),
            ("HS002", "이하나", "연구개발본부", "연구1팀"),
            ("HS003", "홍길동", "연구개발본부", "연구2팀"),
        ]

        for emp_id, name, dept, team in employees:
            # 먼저 employees 테이블에 직원 정보 추가
            cursor.execute("""
                INSERT INTO employees (employee_id, name, department, team, ignore_remaining)
                VALUES (%s, %s, %s, %s, 3)
                ON CONFLICT (employee_id) DO NOTHING
            """, (emp_id, name, dept, team))

            # 그 다음 accounts 테이블에 계정 추가
            cursor.execute("""
                INSERT INTO accounts (login_id, password_hash, role, employee_id, created_at)
                VALUES (%s, %s, 'EMPLOYEE', %s, 0)
                ON CONFLICT (login_id) DO NOTHING
            """, (emp_id, hash_password("1234"), emp_id))

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ PostgreSQL 초기화 완료")

    except Exception as e:
        print(f"❌ PostgreSQL 초기화 실패: {e}")
        print("Railway 배포 시 'railway run python init_railway_db.py'를 실행하세요.")
