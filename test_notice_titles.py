#!/usr/bin/env python3
"""
참조 공지사항 제목 표시 기능 테스트
"""
import os
from dotenv import load_dotenv
from core.chatbot_engine import ChatbotEngine

load_dotenv()

# Railway DB 사용
os.environ["DATABASE_URL"] = "postgresql://postgres:EUxzTKqEvybegsaRhWsySxVcgCRvyZHA@mainline.proxy.rlwy.net:47312/railway"

print("=" * 70)
print("🧪 참조 공지 제목 표시 기능 테스트")
print("=" * 70)

engine = ChatbotEngine(user_id="test_user")

test_query = "인사평가 일정 알려주세요"
print(f"\n질문: {test_query}\n")

result = engine.ask(test_query)

print(f"응답 타입: {result['response_type']}")
print(f"\n응답 (처음 200자):\n{result['response'][:200]}...\n")

print("=" * 70)
print("📎 참조 공지 정보")
print("=" * 70)

# notice_refs (기존 - ID만)
print(f"\nnotice_refs (ID만): {result['notice_refs']}")

# notice_details (신규 - ID + 제목)
if 'notice_details' in result:
    print(f"\nnotice_details (ID + 제목):")
    for detail in result['notice_details']:
        print(f"  - ID: {detail['post_id']}")
        print(f"    제목: {detail['title']}")
        # 20자로 자른 버튼 라벨 미리보기
        short_title = detail['title'][:20] + "..." if len(detail['title']) > 20 else detail['title']
        print(f"    버튼 라벨: 📄 {short_title}")
        print()
else:
    print("\n❌ notice_details 필드가 없습니다!")

print("=" * 70)
print("✅ 테스트 완료!")
print("=" * 70)
