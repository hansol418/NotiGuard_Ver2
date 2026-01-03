#!/usr/bin/env python3
"""
챗봇 엔진 테스트
"""
from core.chatbot_engine import ChatbotEngine

print("=" * 70)
print("🤖 챗봇 엔진 테스트")
print("=" * 70)

# 챗봇 엔진 초기화
engine = ChatbotEngine(user_id="test_user")

print(f"\n✅ 챗봇 엔진 초기화 완료")
print(f"   API URL: {engine.api_url}")
print(f"   API Key: {engine.api_key[:20]}...")

# 테스트 질문들
test_queries = [
    "안녕하세요",
    "VPN 설정 방법 알려주세요",
    "이번 주 공지사항이 뭐가 있나요?",
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*70}")
    print(f"[테스트 {i}] 질문: {query}")
    print(f"{'='*70}")

    try:
        result = engine.ask(query)

        print(f"\n✅ 응답 성공!")
        print(f"\n📝 응답:")
        print(f"{result['response']}")
        print(f"\n📊 메타데이터:")
        print(f"   - 응답 타입: {result['response_type']}")
        print(f"   - 참조 공지: {len(result['notice_refs'])}개")
        print(f"   - 키워드: {', '.join(result['keywords'])}")

    except Exception as e:
        print(f"\n❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*70}")
print(f"✅ 테스트 완료!")
print(f"{'='*70}")
