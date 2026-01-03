-- PostgreSQL Schema for Popup_Service (노티가드 통합)
-- Railway 배포용 스키마

-- 공지사항 테이블
CREATE TABLE IF NOT EXISTS notices (
  post_id        BIGINT PRIMARY KEY,
  created_at     BIGINT NOT NULL,
  type           TEXT NOT NULL CHECK(type IN ('중요','일반')),
  title          TEXT NOT NULL,
  content        TEXT NOT NULL,
  author         TEXT NOT NULL DEFAULT '관리자',
  views          INTEGER NOT NULL DEFAULT 0,
  department     TEXT DEFAULT '전체',
  date           TEXT
);

-- 팝업 테이블
CREATE TABLE IF NOT EXISTS popups (
  popup_id       BIGINT PRIMARY KEY,
  post_id        BIGINT NOT NULL,
  title          TEXT NOT NULL,
  content        TEXT NOT NULL,
  target_departments TEXT NOT NULL DEFAULT '',
  target_teams       TEXT NOT NULL DEFAULT '',
  expected_send_time TEXT NOT NULL DEFAULT '오전 10시',
  created_at     BIGINT NOT NULL,
  FOREIGN KEY(post_id) REFERENCES notices(post_id) ON DELETE CASCADE
);

-- 직원 테이블
CREATE TABLE IF NOT EXISTS employees (
  employee_id      TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  department       TEXT NOT NULL,
  team             TEXT NOT NULL,
  ignore_remaining INTEGER NOT NULL DEFAULT 0
);

-- 팝업 로그 테이블
CREATE TABLE IF NOT EXISTS popup_logs (
  id             SERIAL PRIMARY KEY,
  created_at     BIGINT NOT NULL,
  employee_id    TEXT NOT NULL,
  popup_id       BIGINT NOT NULL,
  action         TEXT NOT NULL,
  confirmed      TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
  FOREIGN KEY(popup_id) REFERENCES popups(popup_id) ON DELETE CASCADE
);

-- 계정 테이블
CREATE TABLE IF NOT EXISTS accounts (
  login_id       TEXT PRIMARY KEY,
  password_hash  TEXT NOT NULL,
  role           TEXT NOT NULL CHECK(role IN ('ADMIN','EMPLOYEE')),
  employee_id    TEXT,
  created_at     BIGINT NOT NULL DEFAULT 0,
  FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE SET NULL
);

-- 첨부파일 테이블
CREATE TABLE IF NOT EXISTS notice_files (
  file_id     SERIAL PRIMARY KEY,
  post_id     BIGINT NOT NULL,
  filename    TEXT NOT NULL,
  mime_type   TEXT NOT NULL DEFAULT '',
  file_path   TEXT NOT NULL,
  file_size   INTEGER NOT NULL DEFAULT 0,
  uploaded_at BIGINT NOT NULL,
  FOREIGN KEY(post_id) REFERENCES notices(post_id) ON DELETE CASCADE
);

-- 챗봇 로그 테이블 (노티가드 통합)
CREATE TABLE IF NOT EXISTS chat_logs (
  id             SERIAL PRIMARY KEY,
  user_id        TEXT,
  user_query     TEXT NOT NULL,
  bot_response   TEXT NOT NULL,
  response_type  TEXT NOT NULL,
  summary        TEXT,
  keywords       TEXT,
  notice_refs    TEXT,
  created_at     BIGINT NOT NULL
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_popup_logs_emp_popup ON popup_logs(employee_id, popup_id);
CREATE INDEX IF NOT EXISTS idx_notices_created_at ON notices(created_at);
CREATE INDEX IF NOT EXISTS idx_popups_created_at ON popups(created_at);
CREATE INDEX IF NOT EXISTS idx_accounts_role ON accounts(role);
CREATE INDEX IF NOT EXISTS idx_notice_files_post_id ON notice_files(post_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at);

-- 기본 직원 데이터
INSERT INTO employees (employee_id, name, department, team, ignore_remaining)
VALUES
  ('HS001', '김산', '경영관리본부', '재경팀', 3),
  ('HS002', '이하나', '연구개발본부', '연구1팀', 3),
  ('HS003', '홍길동', '연구개발본부', '연구2팀', 3)
ON CONFLICT (employee_id) DO NOTHING;

-- 기본 계정 데이터
-- 주의: password_hash는 bcrypt 해시값입니다 (password: 1234)
-- init_railway_db.py에서 실제 해시값으로 생성됩니다
-- 여기서는 플레이스홀더만 삽입하고, Python 스크립트에서 업데이트
INSERT INTO accounts (login_id, password_hash, role, employee_id, created_at)
VALUES
  ('admin', 'placeholder_hash', 'ADMIN', NULL, 0),
  ('HS001', 'placeholder_hash', 'EMPLOYEE', 'HS001', 0),
  ('HS002', 'placeholder_hash', 'EMPLOYEE', 'HS002', 0),
  ('HS003', 'placeholder_hash', 'EMPLOYEE', 'HS003', 0)
ON CONFLICT (login_id) DO NOTHING;
