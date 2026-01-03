#!/usr/bin/env python3
"""
로컬 파일을 Cloudflare R2로 마이그레이션

1. uploads/ 폴더의 모든 파일을 R2에 업로드
2. Railway PostgreSQL의 notice_files 테이블에서 file_path를 R2 URL로 업데이트
"""
import os
import psycopg2
from pathlib import Path
from core.storage import upload_file_to_r2

# Railway PostgreSQL 연결 정보
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:EUxzTKqEvybegsaRhWsySxVcgCRvyZHA@mainline.proxy.rlwy.net:47312/railway")

# 로컬 업로드 폴더
UPLOAD_DIR = Path("uploads")

print("=" * 70)
print("📁 로컬 파일 → Cloudflare R2 마이그레이션")
print("=" * 70)

# 1. 로컬 파일 목록 확인
if not UPLOAD_DIR.exists():
    print(f"\n❌ {UPLOAD_DIR} 폴더가 존재하지 않습니다.")
    exit(1)

local_files = list(UPLOAD_DIR.glob("*"))
print(f"\n📂 로컬 파일: {len(local_files)}개")

if not local_files:
    print("업로드할 파일이 없습니다.")
    exit(0)

# 2. PostgreSQL 연결
print(f"\n🔗 PostgreSQL 연결 중...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 3. DB에서 파일 목록 조회
print(f"\n📋 DB에 등록된 파일 조회 중...")
cur.execute("""
    SELECT file_id, filename, file_path, mime_type
    FROM notice_files
    ORDER BY file_id
""")
db_files = cur.fetchall()
print(f"DB에 등록된 파일: {len(db_files)}개")

# 4. 파일 마이그레이션
print(f"\n🚀 R2 마이그레이션 시작...")
migrated_count = 0
skipped_count = 0
failed_count = 0

for file_id, filename, file_path, mime_type in db_files:
    # 이미 R2 URL이면 건너뛰기
    if file_path.startswith("http"):
        print(f"  ⏭️  건너뜀: {filename} (이미 R2 URL)")
        skipped_count += 1
        continue

    # 로컬 파일 경로
    local_path = Path(file_path)

    if not local_path.exists():
        print(f"  ❌ 실패: {filename} (로컬 파일 없음: {file_path})")
        failed_count += 1
        continue

    try:
        # R2에 업로드
        with open(local_path, 'rb') as f:
            r2_url = upload_file_to_r2(
                file_data=f,
                filename=local_path.name,
                folder="uploads",
                content_type=mime_type
            )

        # DB 업데이트
        cur.execute("""
            UPDATE notice_files
            SET file_path = %s
            WHERE file_id = %s
        """, (r2_url, file_id))

        conn.commit()

        print(f"  ✅ 마이그레이션: {filename}")
        print(f"     로컬: {file_path}")
        print(f"     R2: {r2_url}")
        migrated_count += 1

    except Exception as e:
        print(f"  ❌ 실패: {filename} - {str(e)}")
        conn.rollback()
        failed_count += 1

# 5. 결과 확인
print(f"\n" + "=" * 70)
print(f"✅ 마이그레이션 완료")
print(f"=" * 70)
print(f"총 {len(db_files)}개 파일")
print(f"  - 마이그레이션: {migrated_count}개")
print(f"  - 건너뜀 (이미 R2): {skipped_count}개")
print(f"  - 실패: {failed_count}개")

# 최종 확인
cur.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN file_path LIKE 'http%' THEN 1 ELSE 0 END) as r2_count
    FROM notice_files
""")
result = cur.fetchone()
total, r2_count = result

print(f"\n📊 최종 상태:")
print(f"  - 전체 파일: {total}개")
print(f"  - R2 저장: {r2_count}개")
print(f"  - 로컬 저장: {total - r2_count}개")

# 연결 종료
cur.close()
conn.close()

print(f"\n" + "=" * 70)
print(f"🎉 작업 완료!")
print(f"=" * 70)
