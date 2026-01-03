#!/usr/bin/env python3
"""
챗봇 통합 검증 스크립트
로컬 환경에서 통합이 제대로 되었는지 확인합니다.
"""

import sys
from pathlib import Path

def verify_files():
    """필수 파일 존재 확인"""
    print("📁 파일 존재 확인...")

    required_files = [
        "core/chatbot_engine.py",
        "pages/chatbot.py",
        "core/db.py",
        "core/layout.py",
        "requirements.txt"
    ]

    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
            print(f"  ❌ {file}")
        else:
            print(f"  ✅ {file}")

    if missing:
        print(f"\n⚠️  누락된 파일: {len(missing)}개")
        return False

    print(f"\n✅ 모든 필수 파일 존재")
    return True

def verify_database():
    """데이터베이스 테이블 확인"""
    print("\n🗄️  데이터베이스 테이블 확인...")

    try:
        from core.db import get_conn

        with get_conn() as conn:
            # 필수 테이블 확인
            tables = ['accounts', 'employees', 'notices', 'popups', 'popup_logs', 'chat_logs', 'notice_files']

            for table in tables:
                try:
                    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"  ✅ {table}: {count}개 레코드")
                except Exception as e:
                    print(f"  ❌ {table}: {str(e)}")
                    return False

        print(f"\n✅ 모든 테이블 정상")
        return True

    except Exception as e:
        print(f"\n❌ 데이터베이스 오류: {e}")
        return False

def verify_chatbot_engine():
    """챗봇 엔진 기능 확인"""
    print("\n🤖 챗봇 엔진 기능 확인...")

    try:
        from core.chatbot_engine import ChatbotEngine

        # 엔진 초기화
        engine = ChatbotEngine(user_id="TEST_USER")
        print("  ✅ ChatbotEngine 초기화")

        # 공지사항 조회
        notices = engine._get_recent_notices(limit=5)
        print(f"  ✅ 공지사항 조회: {len(notices)}개")

        # 컨텍스트 구성
        context = engine._build_context(notices)
        print(f"  ✅ 컨텍스트 구성: {len(context)} 문자")

        # 키워드 추출
        keywords = engine._extract_keywords("이번 주 안전교육 일정 알려줘")
        print(f"  ✅ 키워드 추출: {keywords}")

        print(f"\n✅ 챗봇 엔진 정상")
        return True

    except Exception as e:
        print(f"\n❌ 챗봇 엔진 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_environment():
    """환경 변수 확인"""
    print("\n🔧 환경 변수 확인...")

    import os

    # 선택적 환경 변수
    optional_vars = {
        'POTENS_API_KEY': '챗봇 응답 생성',
        'DATABASE_URL': 'PostgreSQL 연결',
        'R2_ACCOUNT_ID': 'Cloudflare R2 저장소'
    }

    for var, desc in optional_vars.items():
        if os.getenv(var):
            print(f"  ✅ {var}: 설정됨 ({desc})")
        else:
            print(f"  ⚠️  {var}: 미설정 ({desc})")

    # POTENS API 키가 없으면 경고
    if not os.getenv('POTENS_API_KEY'):
        print("\n⚠️  POTENS_API_KEY가 설정되지 않았습니다.")
        print("   챗봇이 응답을 생성할 수 없습니다.")
        print("   .env 파일에 POTENS_API_KEY를 추가하세요.")

    return True

def main():
    """메인 검증 프로세스"""
    print("=" * 60)
    print("🔍 챗봇 통합 검증 시작")
    print("=" * 60)

    results = []

    # 1. 파일 확인
    results.append(("파일", verify_files()))

    # 2. 데이터베이스 확인
    results.append(("데이터베이스", verify_database()))

    # 3. 챗봇 엔진 확인
    results.append(("챗봇 엔진", verify_chatbot_engine()))

    # 4. 환경 변수 확인
    results.append(("환경 변수", verify_environment()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 검증 결과 요약")
    print("=" * 60)

    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{name:15} {status}")

    # 전체 성공 여부
    all_passed = all(r[1] for r in results[:3])  # 환경 변수는 선택사항

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 통합 검증 성공!")
        print("\n다음 명령으로 앱을 실행하세요:")
        print("  streamlit run app.py")
    else:
        print("❌ 통합 검증 실패")
        print("\n위의 오류를 수정한 후 다시 시도하세요.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
