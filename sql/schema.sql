-- STREAMLIT/sql/schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS notices (
  post_id        INTEGER PRIMARY KEY,
  created_at     INTEGER NOT NULL,             -- epoch ms
  type           TEXT NOT NULL CHECK(type IN ('중요','일반')),
  title          TEXT NOT NULL,
  content        TEXT NOT NULL,
  author         TEXT NOT NULL DEFAULT '관리자',
  views          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS popups (
  popup_id       INTEGER PRIMARY KEY,          -- post_id와 동일하게 사용
  post_id        INTEGER NOT NULL,
  title          TEXT NOT NULL,
  content        TEXT NOT NULL,
  target_departments TEXT NOT NULL DEFAULT '', -- CSV 문자열
  target_teams       TEXT NOT NULL DEFAULT '', -- CSV 문자열
  expected_send_time TEXT NOT NULL DEFAULT '오전 10시',
  created_at     INTEGER NOT NULL,
  FOREIGN KEY(post_id) REFERENCES notices(post_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS employees (
  employee_id      TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  department       TEXT NOT NULL,
  team             TEXT NOT NULL,
  ignore_remaining INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS popup_logs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at     INTEGER NOT NULL,
  employee_id    TEXT NOT NULL,
  popup_id       INTEGER NOT NULL,
  action         TEXT NOT NULL,                -- '확인함', '확인하지 않음', '챗봇이동'
  confirmed      TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
  FOREIGN KEY(popup_id) REFERENCES popups(popup_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_popup_logs_emp_popup
ON popup_logs(employee_id, popup_id);

CREATE INDEX IF NOT EXISTS idx_notices_created_at
ON notices(created_at);

CREATE INDEX IF NOT EXISTS idx_popups_created_at
ON popups(created_at);

-- ✅ 로그인 계정 테이블 추가
-- role: 'ADMIN' | 'EMPLOYEE'
-- employee_id: EMPLOYEE면 employees.employee_id를 참조(연결), ADMIN이면 NULL
CREATE TABLE IF NOT EXISTS accounts (
  login_id       TEXT PRIMARY KEY,
  password_hash  TEXT NOT NULL,
  role           TEXT NOT NULL CHECK(role IN ('ADMIN','EMPLOYEE')),
  employee_id    TEXT,
  created_at     INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_role
ON accounts(role);

CREATE TABLE IF NOT EXISTS notice_files (
  file_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id     INTEGER NOT NULL,
  filename    TEXT NOT NULL,
  mime_type   TEXT NOT NULL DEFAULT '',
  file_path   TEXT NOT NULL,
  file_size   INTEGER NOT NULL DEFAULT 0,
  uploaded_at INTEGER NOT NULL,
  FOREIGN KEY(post_id) REFERENCES notices(post_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notice_files_post_id
ON notice_files(post_id);

-- ✅ 담당자 문의 테이블 추가
-- 챗봇에서 담당자에게 문의한 내역 저장
CREATE TABLE IF NOT EXISTS inquiries (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id    TEXT,
  department     TEXT NOT NULL,                -- 문의 대상 부서
  user_query     TEXT NOT NULL DEFAULT '',    -- 원본 질문
  content        TEXT NOT NULL,                -- 문의 내용
  status         TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'resolved'
  created_at     INTEGER NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_inquiries_created_at
ON inquiries(created_at);

CREATE INDEX IF NOT EXISTS idx_inquiries_status
ON inquiries(status);
