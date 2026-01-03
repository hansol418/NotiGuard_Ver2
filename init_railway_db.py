#!/usr/bin/env python3
"""
Railway PostgreSQL 데이터베이스 초기화 스크립트

사용 방법:
  railway run python init_railway_db.py

또는 로컬에서 테스트:
  DATABASE_URL=postgresql://... python init_railway_db.py
"""

import os
import sys
from pathlib import Path

# DATABASE_URL 확인
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.")
    print("Railway에서 실행: railway run python init_railway_db.py")
    sys.exit(1)

print(f"🔗 DATABASE_URL: {DATABASE_URL[:30]}...")

# PostgreSQL 연결
try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ ERROR: psycopg2가 설치되지 않았습니다.")
    print("설치: pip install psycopg2-binary")
    sys.exit(1)

# 비밀번호 해시 함수
try:
    from core.auth import hash_password
except ImportError:
    print("❌ ERROR: core.auth 모듈을 찾을 수 없습니다.")
    sys.exit(1)

print("\n" + "=" * 70)
print("🚀 Railway PostgreSQL 데이터베이스 초기화")
print("=" * 70)

# PostgreSQL 연결
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ PostgreSQL 연결 성공")
except Exception as e:
    print(f"❌ PostgreSQL 연결 실패: {e}")
    sys.exit(1)

# 1. 스키마 실행
print("\n📋 1. 스키마 파일 실행...")
schema_path = Path("sql/schema_postgres.sql")

if not schema_path.exists():
    print(f"❌ ERROR: {schema_path} 파일을 찾을 수 없습니다.")
    cursor.close()
    conn.close()
    sys.exit(1)

try:
    schema_sql = schema_path.read_text(encoding="utf-8")
    cursor.execute(schema_sql)
    conn.commit()
    print("✅ 스키마 실행 완료")
except Exception as e:
    print(f"❌ 스키마 실행 실패: {e}")
    conn.rollback()
    cursor.close()
    conn.close()
    sys.exit(1)

# 2. 비밀번호 해시 업데이트
print("\n🔐 2. 계정 비밀번호 설정...")

default_password = "1234"
admin_hash = hash_password(default_password)

accounts = [
    ("admin", admin_hash, "ADMIN", None),
    ("HS001", hash_password(default_password), "EMPLOYEE", "HS001"),
    ("HS002", hash_password(default_password), "EMPLOYEE", "HS002"),
    ("HS003", hash_password(default_password), "EMPLOYEE", "HS003"),
]

try:
    for login_id, pwd_hash, role, emp_id in accounts:
        # UPDATE 또는 INSERT
        cursor.execute("""
            INSERT INTO accounts (login_id, password_hash, role, employee_id, created_at)
            VALUES (%s, %s, %s, %s, 0)
            ON CONFLICT (login_id)
            DO UPDATE SET password_hash = EXCLUDED.password_hash
        """, (login_id, pwd_hash, role, emp_id))
        print(f"  ✅ {login_id} (password: {default_password})")

    conn.commit()
    print("✅ 계정 설정 완료")
except Exception as e:
    print(f"❌ 계정 설정 실패: {e}")
    conn.rollback()
    cursor.close()
    conn.close()
    sys.exit(1)

# 3. 테이블 확인
print("\n📊 3. 테이블 확인...")

try:
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()

    print(f"생성된 테이블: {len(tables)}개")
    for table in tables:
        print(f"  - {table[0]}")
except Exception as e:
    print(f"⚠️  테이블 목록 조회 실패: {e}")

# 4. 데이터 확인
print("\n👤 4. 기본 데이터 확인...")

try:
    # 직원 수
    cursor.execute("SELECT COUNT(*) FROM employees")
    emp_count = cursor.fetchone()[0]
    print(f"  직원: {emp_count}명")

    # 계정 수
    cursor.execute("SELECT COUNT(*) FROM accounts")
    acc_count = cursor.fetchone()[0]
    print(f"  계정: {acc_count}개")

    # 공지사항 수
    cursor.execute("SELECT COUNT(*) FROM notices")
    notice_count = cursor.fetchone()[0]
    print(f"  공지사항: {notice_count}개")

except Exception as e:
    print(f"⚠️  데이터 확인 실패: {e}")

# 연결 종료
cursor.close()
conn.close()

print("\n" + "=" * 70)
print("✅ 데이터베이스 초기화 완료!")
print("=" * 70)
print()
print("📝 로그인 계정:")
print("  관리자: admin / 1234")
print("  직원1: HS001 / 1234 (김산, 경영관리본부)")
print("  직원2: HS002 / 1234 (이하나, 연구개발본부)")
print("  직원3: HS003 / 1234 (홍길동, 연구개발본부)")
print()
print("⚠️  보안: 프로덕션 환경에서는 기본 비밀번호를 변경하세요!")
print()
