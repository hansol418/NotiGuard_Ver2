#!/usr/bin/env python3
"""
로컬 SQLite → Railway PostgreSQL 데이터 마이그레이션 스크립트

사용 방법:
  python3 migrate_notices.py

환경변수:
  DATABASE_URL: Railway PostgreSQL 연결 URL
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Railway PostgreSQL 연결 정보
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:EUxzTKqEvybegsaRhWsySxVcgCRvyZHA@mainline.proxy.rlwy.net:47312/railway")
SQLITE_DB = "groupware.db"

print("=" * 70)
print("🚀 SQLite → PostgreSQL 데이터 마이그레이션")
print("=" * 70)

# 1. SQLite 연결
print(f"\n📂 SQLite DB: {SQLITE_DB}")
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# 2. PostgreSQL 연결
print(f"🔗 PostgreSQL: {DATABASE_URL[:50]}...")
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)

print("\n" + "=" * 70)
print("📊 데이터 확인")
print("=" * 70)

# SQLite 데이터 개수
sqlite_cur.execute("SELECT COUNT(*) as cnt FROM notices")
sqlite_notices_count = sqlite_cur.fetchone()[0]
print(f"SQLite notices: {sqlite_notices_count}개")

sqlite_cur.execute("SELECT COUNT(*) as cnt FROM notice_files")
sqlite_files_count = sqlite_cur.fetchone()[0]
print(f"SQLite notice_files: {sqlite_files_count}개")

# PostgreSQL 데이터 개수
pg_cur.execute("SELECT COUNT(*) as cnt FROM notices")
pg_notices_count = pg_cur.fetchone()['cnt']
print(f"PostgreSQL notices: {pg_notices_count}개")

pg_cur.execute("SELECT COUNT(*) as cnt FROM notice_files")
pg_files_count = pg_cur.fetchone()['cnt']
print(f"PostgreSQL notice_files: {pg_files_count}개")

# 3. notices 테이블 마이그레이션
print("\n" + "=" * 70)
print("📝 notices 테이블 마이그레이션")
print("=" * 70)

sqlite_cur.execute("SELECT * FROM notices ORDER BY post_id ASC")
notices = sqlite_cur.fetchall()

migrated_count = 0
skipped_count = 0

for notice in notices:
    post_id = notice['post_id']

    # 이미 존재하는지 확인
    pg_cur.execute("SELECT 1 FROM notices WHERE post_id = %s", (post_id,))
    if pg_cur.fetchone():
        print(f"  ⏭️  건너뜀: post_id={post_id} (이미 존재)")
        skipped_count += 1
        continue

    # 삽입
    try:
        # sqlite3.Row를 dict로 변환
        notice_dict = dict(notice)

        pg_cur.execute(
            """
            INSERT INTO notices (post_id, created_at, type, title, content, author, views, department, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                notice_dict['post_id'],
                notice_dict['created_at'],
                notice_dict['type'],
                notice_dict['title'],
                notice_dict['content'],
                notice_dict['author'],
                notice_dict['views'],
                notice_dict.get('department', '전체'),
                notice_dict.get('date', '')
            )
        )
        pg_conn.commit()
        print(f"  ✅ 마이그레이션: post_id={post_id}, title={notice['title'][:30]}")
        migrated_count += 1
    except Exception as e:
        print(f"  ❌ 실패: post_id={post_id}, error={e}")
        pg_conn.rollback()

print(f"\n✅ notices 마이그레이션 완료: {migrated_count}개 추가, {skipped_count}개 건너뜀")

# 4. notice_files 테이블 마이그레이션
print("\n" + "=" * 70)
print("📎 notice_files 테이블 마이그레이션")
print("=" * 70)

sqlite_cur.execute("SELECT * FROM notice_files ORDER BY file_id ASC")
files = sqlite_cur.fetchall()

file_migrated = 0
file_skipped = 0

for file in files:
    file_id = file['file_id']
    post_id = file['post_id']

    # 해당 post_id가 notices에 있는지 확인
    pg_cur.execute("SELECT 1 FROM notices WHERE post_id = %s", (post_id,))
    if not pg_cur.fetchone():
        print(f"  ⚠️  건너뜀: file_id={file_id} (post_id={post_id} 없음)")
        file_skipped += 1
        continue

    # 이미 존재하는지 확인 (file_id는 SERIAL이므로 post_id+filename으로 중복 체크)
    pg_cur.execute(
        "SELECT 1 FROM notice_files WHERE post_id = %s AND filename = %s",
        (post_id, file['filename'])
    )
    if pg_cur.fetchone():
        print(f"  ⏭️  건너뜀: post_id={post_id}, filename={file['filename']} (이미 존재)")
        file_skipped += 1
        continue

    # 삽입 (file_id는 SERIAL이므로 자동 생성)
    try:
        pg_cur.execute(
            """
            INSERT INTO notice_files (post_id, filename, mime_type, file_path, file_size, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                post_id,
                file['filename'],
                file['mime_type'],
                file['file_path'],
                file['file_size'],
                file['uploaded_at']
            )
        )
        pg_conn.commit()
        print(f"  ✅ 마이그레이션: post_id={post_id}, filename={file['filename']}")
        file_migrated += 1
    except Exception as e:
        print(f"  ❌ 실패: file_id={file_id}, error={e}")
        pg_conn.rollback()

print(f"\n✅ notice_files 마이그레이션 완료: {file_migrated}개 추가, {file_skipped}개 건너뜀")

# 5. 최종 확인
print("\n" + "=" * 70)
print("📊 마이그레이션 결과")
print("=" * 70)

pg_cur.execute("SELECT COUNT(*) as cnt FROM notices")
final_notices = pg_cur.fetchone()['cnt']
print(f"PostgreSQL notices: {final_notices}개")

pg_cur.execute("SELECT COUNT(*) as cnt FROM notice_files")
final_files = pg_cur.fetchone()['cnt']
print(f"PostgreSQL notice_files: {final_files}개")

# 연결 종료
sqlite_conn.close()
pg_conn.close()

print("\n" + "=" * 70)
print("✅ 마이그레이션 완료!")
print("=" * 70)
