#!/usr/bin/env python3
"""
Railway PostgreSQL 계정 비밀번호 재설정 스크립트

모든 계정의 비밀번호를 1234로 재설정합니다.
"""
import os
import psycopg2
from core.auth import hash_password

# Railway PostgreSQL 연결 정보
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:EUxzTKqEvybegsaRhWsySxVcgCRvyZHA@mainline.proxy.rlwy.net:47312/railway")

print("=" * 70)
print("🔐 계정 비밀번호 재설정")
print("=" * 70)

# PostgreSQL 연결
print(f"\n🔗 PostgreSQL 연결 중...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 새 비밀번호 해시 생성
new_password = "1234"
password_hash = hash_password(new_password)

print(f"\n✅ 새 비밀번호 해시 생성 완료")
print(f"비밀번호: {new_password}")
print(f"해시: {password_hash[:50]}...")

# 모든 계정 조회
print(f"\n📋 현재 계정 목록:")
cur.execute("SELECT login_id, role, employee_id FROM accounts ORDER BY login_id")
accounts = cur.fetchall()

for acc in accounts:
    login_id, role, employee_id = acc
    emp_info = f" -> {employee_id}" if employee_id else ""
    print(f"  - {login_id} ({role}){emp_info}")

# 비밀번호 업데이트
print(f"\n🔄 비밀번호 업데이트 중...")
updated_count = 0

for acc in accounts:
    login_id = acc[0]
    try:
        cur.execute(
            "UPDATE accounts SET password_hash = %s WHERE login_id = %s",
            (password_hash, login_id)
        )
        print(f"  ✅ {login_id} 비밀번호 업데이트 완료")
        updated_count += 1
    except Exception as e:
        print(f"  ❌ {login_id} 업데이트 실패: {e}")

conn.commit()

# 결과 확인
print(f"\n" + "=" * 70)
print(f"✅ 비밀번호 재설정 완료")
print(f"=" * 70)
print(f"총 {updated_count}개 계정 비밀번호 업데이트됨")
print(f"\n📌 로그인 정보:")
print(f"  - admin / 1234")
print(f"  - HS001 / 1234")
print(f"  - HS002 / 1234")
print(f"  - HS003 / 1234")
print(f"\n" + "=" * 70)

# 연결 종료
cur.close()
conn.close()
