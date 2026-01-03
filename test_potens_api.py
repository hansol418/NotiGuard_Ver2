#!/usr/bin/env python3
"""
POTENS API 연결 테스트 스크립트
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# API 설정
API_KEY = os.getenv("POTENS_API_KEY", "Q1QJ6jIOTp0369I9PXCFa3GxMyzY4hHh")

# 테스트할 URL 목록
test_urls = [
    "https://api.potens.ai/v1/chat/completions",
    "https://ai.potens.ai/v1/chat/completions",
    "https://ai.potens.ai/api/chat",
    "https://api.potens.ai/api/chat",
]

print("=" * 70)
print("🔍 POTENS API 연결 테스트")
print("=" * 70)
print(f"\nAPI Key: {API_KEY[:20]}...{API_KEY[-10:]}")

for url in test_urls:
    print(f"\n{'='*70}")
    print(f"테스트 URL: {url}")
    print(f"{'='*70}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # 1. messages 형식으로 테스트
    payload1 = {
        "messages": [
            {"role": "user", "content": "안녕하세요"}
        ]
    }

    print("\n[시도 1] messages 형식")
    try:
        response = requests.post(url, json=payload1, headers=headers, timeout=10)
        print(f"  상태 코드: {response.status_code}")
        print(f"  응답 헤더: {dict(response.headers)}")

        if response.status_code == 200:
            print(f"  ✅ 성공!")
            print(f"  응답: {response.json()}")
            print(f"\n🎉 올바른 URL: {url}")
            print(f"🎉 올바른 형식: messages")
            break
        else:
            print(f"  ❌ 실패: {response.status_code}")
            print(f"  응답: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 에러: {str(e)}")

    # 2. prompt 형식으로 테스트
    payload2 = {
        "prompt": "안녕하세요"
    }

    print("\n[시도 2] prompt 형식")
    try:
        response = requests.post(url, json=payload2, headers=headers, timeout=10)
        print(f"  상태 코드: {response.status_code}")

        if response.status_code == 200:
            print(f"  ✅ 성공!")
            print(f"  응답: {response.json()}")
            print(f"\n🎉 올바른 URL: {url}")
            print(f"🎉 올바른 형식: prompt")
            break
        else:
            print(f"  ❌ 실패: {response.status_code}")
            print(f"  응답: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 에러: {str(e)}")
else:
    print("\n" + "="*70)
    print("⚠️  모든 URL 테스트 실패")
    print("="*70)
    print("\n가능한 원인:")
    print("1. API 키가 만료되었거나 유효하지 않음")
    print("2. API 엔드포인트가 변경됨")
    print("3. 요청 형식이 잘못됨")
    print("\nPOTENS 공식 문서를 확인하거나 관리자에게 문의하세요.")

print("\n" + "="*70)
print("테스트 종료")
print("="*70)
