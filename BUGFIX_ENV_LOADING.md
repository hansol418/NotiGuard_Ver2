# 버그 수정: POTENS API 403 에러

## 문제 증상
사용자가 챗봇에서 질문("교육일정 확인") 시 다음 에러 발생:
```
API 호출 실패: 403 Client Error: Forbidden for url: https://ai.potens.ai/api/chat
```

## 원인 분석

### 1차 조사
- `.env` 파일 확인: ✅ POTENS_API_KEY 존재
- API 직접 테스트: ✅ 200 OK (정상 작동)
- 환경 변수 로드: ✅ python-dotenv 설치됨

### 2차 조사 (근본 원인)
`core/chatbot_engine.py` 파일에서 **`.env` 파일을 로드하지 않음**

```python
# ❌ 문제 코드 (기존)
import os
from core.db import get_conn

POTENS_API_KEY = os.getenv("POTENS_API_KEY", "")  # ← .env 로드 없이 읽음
```

Streamlit이 모듈을 import할 때 `.env` 파일이 자동으로 로드되지 않아 `POTENS_API_KEY`가 빈 문자열이 됨.

## 해결 방법

### 수정 내용
`core/chatbot_engine.py` 파일 상단에 `load_dotenv()` 추가:

```python
# ✅ 수정 코드
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

POTENS_API_KEY = os.getenv("POTENS_API_KEY", "")  # ← 이제 정상 로드됨
```

### 수정 파일
- `core/chatbot_engine.py` (라인 10, 14 추가)

## 테스트 결과

### 수정 전
```
📝 질문: 교육일정 확인
❌ 응답: API 호출 실패: 403 Client Error: Forbidden
```

### 수정 후
```
📝 질문: 교육일정 확인
✅ 응답: 현재 등록된 공지사항 중에는 교육 관련 일정이나 안내가 포함되어 있지 않습니다.
         교육 일정은 추후 공지될 예정이거나, 별도 채널을 통해 안내될 수 있습니다.
```

### API 키 로드 확인
```
수정 전: POTENS_API_KEY = "" (빈 문자열)
수정 후: POTENS_API_KEY = "Q1QJ6jIOTp...GxMyzY4hHh" ✅
```

## 재발 방지

### 체크리스트
환경 변수를 사용하는 모든 Python 모듈은:
1. ✅ `from dotenv import load_dotenv` import
2. ✅ `load_dotenv()` 호출
3. ✅ 그 후에 `os.getenv()` 사용

### 확인해야 할 파일
- [x] `core/chatbot_engine.py` - ✅ 수정 완료
- [x] `core/db.py` - ✅ DATABASE_URL은 Railway에서 자동 주입
- [x] `core/storage.py` - ✅ R2 환경 변수도 동일 패턴 사용 가능

## 배포 환경 차이

### 로컬 개발
- `.env` 파일 사용
- `load_dotenv()` 필수

### Railway 배포
- 환경 변수 자동 주입
- `load_dotenv()` 호출해도 무해 (이미 있는 환경 변수 우선)
- `.env` 파일 git에 커밋 금지 (`.gitignore` 확인)

## 관련 이슈
- python-dotenv 미설치 시에도 오류 발생 가능
- `requirements.txt`에 `python-dotenv` 포함 확인 ✅

---

**수정 일시**: 2026-01-03 22:20
**수정자**: Claude Code
**테스트**: ✅ 통과
**배포**: Streamlit 서버 재시작 완료
