# core/potens.py
import os
import requests
from dotenv import load_dotenv

# Streamlit pages / dialog 환경에서도 확실히 잡히게 "여기서" 로드
load_dotenv(override=False)

POTENS_API_KEY = os.getenv("POTENS_API_KEY", "")
POTENS_API_URL = os.getenv("POTENS_API_URL", "https://ai.potens.ai/api/chat")
RESPONSE_TIMEOUT = float(os.getenv("RESPONSE_TIMEOUT", "30"))


def build_summary_prompt(title: str, content: str) -> str:
    title_part = f"제목: {title}\n" if title else ""
    return f"""당신은 회사 공지를 직원이 빠르게 이해하도록 돕는 요약 도우미입니다.

규칙:
- 5줄 이내로 핵심만 요약
- 일정/마감/대상/필수 행동이 있으면 마지막에 '해야 할 일'로 별도 정리
- 문의/연락처/내선 등 단순 연락 문구는 제외
- 한국어 존댓말, 간결하게
- 이미지가 올라왔을 시 본문의 내용과 비교한 후 연관된 이미지이면 해당 이미지에 대한 내용도 포함

[공지]
{title_part}내용:
{content}
"""


def summarize_notice(title: str, content: str) -> str:
    if not POTENS_API_KEY:
        raise RuntimeError("POTENS_API_KEY가 설정되지 않았습니다. (.env 또는 배포 환경변수 확인)")

    content = (content or "").strip()
    if not content:
        return ""

    prompt = build_summary_prompt(title or "", content)

    headers = {
        "Authorization": f"Bearer {POTENS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt}

    r = requests.post(
        POTENS_API_URL,
        json=payload,
        headers=headers,
        timeout=RESPONSE_TIMEOUT,
    )
    r.raise_for_status()

    result = r.json()

    # 챗봇앱과 동일한 '범용 파싱'
    if isinstance(result, dict):
        summary = (
            result.get("response")
            or result.get("answer")
            or result.get("text")
            or result.get("message")
            or result.get("content")
        )
        if summary:
            return str(summary).strip()

    return str(result).strip()
