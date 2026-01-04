"""
통합 챗봇 엔진 (노티가드 로직 이식)
Popup_Service DB와 연동하여 공지사항 질의응답 제공
"""
import requests
import json
import os
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from core.db import get_conn

# .env 파일 로드
load_dotenv()

# POTENS API 설정
POTENS_API_KEY = os.getenv("POTENS_API_KEY", "")
POTENS_API_URL = os.getenv("POTENS_API_URL", "https://ai.potens.ai/api/chat")
RESPONSE_TIMEOUT = float(os.getenv("RESPONSE_TIMEOUT", "30"))

# PostgreSQL 사용 여부
USE_POSTGRES = bool(os.getenv("DATABASE_URL"))


class ChatbotEngine:
    """
    노티가드 챗봇 엔진 (통합 버전)

    Features:
    - 최신 공지사항 기반 질의응답
    - POTENS.ai API 연동
    - 응답 타입 분류 (NORMAL/MISSING/IRRELEVANT)
    - 채팅 로그 저장
    - 팝업 연동 기능
    """

    def __init__(self, user_id: str):
        """
        Args:
            user_id: 사용자 ID (employee_id)
        """
        self.user_id = user_id
        self.api_key = POTENS_API_KEY
        self.api_url = POTENS_API_URL

    def ask(self, user_query: str) -> Dict:
        """
        사용자 질문 처리

        Args:
            user_query: 사용자 질문

        Returns:
            {
                "response": "챗봇 답변",
                "response_type": "NORMAL" | "MISSING" | "IRRELEVANT",
                "notice_refs": [공지 ID 리스트],
                "keywords": [추출된 키워드]
            }
        """
        # 1. 최근 공지 조회 (기본값 50개)
        recent_notices = self._get_recent_notices()

        # 2. 컨텍스트 구성
        context = self._build_context(recent_notices)

        # 3. 프롬프트 생성
        prompt = self._build_prompt(user_query, context)

        # 4. POTENS API 호출
        response_text = self._call_potens_api(prompt)

        # 5. 응답 타입 분류
        response_type = self._detect_response_type(response_text)

        # 6. 참조 공지 추출
        notice_refs = self._extract_notice_refs(response_text, recent_notices)

        # 7. 키워드 추출
        keywords = self._extract_keywords(user_query)

        # 8. 로그 저장
        self._save_chat_log(
            user_query,
            response_text,
            response_type,
            notice_refs,
            keywords
        )

        return {
            "response": self._clean_response(response_text),
            "response_type": response_type,
            "notice_refs": notice_refs,
            "keywords": keywords
        }

    def _get_recent_notices(self, limit: int = 50) -> List[Dict]:
        """
        최근 공지 조회 (통합 DB)

        Args:
            limit: 조회할 공지 개수 (기본값 50개로 증가)

        Returns:
            공지 리스트 (날짜 기준 내림차순)
        """
        with get_conn() as conn:
            if USE_POSTGRES:
                # PostgreSQL - date 필드 기준 정렬 (NULL이면 created_at 사용)
                cur = conn.cursor()
                cur.execute("""
                    SELECT post_id, title, content, department, date, type
                    FROM notices
                    ORDER BY
                        CASE
                            WHEN date IS NOT NULL THEN date::date
                            ELSE (created_at / 1000)::int::abstime::date
                        END DESC,
                        post_id DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                # SQLite - date 필드 기준 정렬
                cur = conn.execute("""
                    SELECT post_id, title, content,
                           COALESCE(department, '전체') as department,
                           COALESCE(date, strftime('%Y-%m-%d', created_at/1000, 'unixepoch')) as date,
                           type
                    FROM notices
                    ORDER BY
                        CASE
                            WHEN date IS NOT NULL THEN date
                            ELSE strftime('%Y-%m-%d', created_at/1000, 'unixepoch')
                        END DESC,
                        post_id DESC
                    LIMIT ?
                """, (limit,))
                return [dict(r) for r in cur.fetchall()]

    def _build_context(self, notices: List[Dict]) -> str:
        """
        공지 컨텍스트 구성

        Args:
            notices: 공지 리스트

        Returns:
            컨텍스트 문자열
        """
        if not notices:
            return "현재 등록된 공지사항이 없습니다."

        parts = []
        for i, n in enumerate(notices, 1):
            parts.append(
                f"[공지 {i}]\n"
                f"제목: {n['title']}\n"
                f"부서: {n.get('department', '전체')}\n"
                f"날짜: {n.get('date', '')}\n"
                f"유형: {n.get('type', '일반')}\n"
                f"내용: {n['content'][:200]}...\n"  # 내용 일부만
            )
        return "\n".join(parts)

    def _build_prompt(self, user_query: str, context: str) -> str:
        """
        프롬프트 생성 (노티가드 시스템 프롬프트)

        Args:
            user_query: 사용자 질문
            context: 공지 컨텍스트

        Returns:
            프롬프트 문자열
        """
        return f"""당신은 효성전기의 공지사항 알림 챗봇 '노티가드(NotiGuard)'입니다.

**자기소개 (메타 질문 대응):**
사용자가 "너는 누구니?", "무엇을 할 수 있어?", "어떻게 사용해?" 등의 질문을 하면:
- 자신을 '노티가드'로 소개하고, 효성전기 공지사항 검색 및 안내를 돕는 AI 챗봇임을 설명
- 공지사항 검색, 일정 안내, 부서별 공지 확인 등의 기능을 소개
- 예시 질문을 제공 (예: "안전교육 일정 알려줘", "인사팀 공지사항 보여줘")

**역할:**
- 효성전기 직원들의 공지사항 관련 질문에 친절하고 정확하게 답변합니다.
- 제공된 공지사항 데이터베이스를 기반으로만 답변합니다.
- 공지사항을 찾으면 **제목, 부서, 날짜, 내용**을 모두 포함하여 상세히 안내합니다.
- **중요: 비슷한 내용의 공지사항이 여러 개 있을 경우, '날짜'가 가장 최신인 공지사항을 정답으로 간주하고 우선적으로 안내하세요.**

**답변 규칙:**
1. **메타 질문** (챗봇 자체에 대한 질문):
   - "너는 누구?", "뭐 할 수 있어?", "사용법" 등의 질문에는 자기소개와 기능 설명
   - 예시 질문을 함께 제공하여 사용자가 바로 질문할 수 있도록 유도

2. **공지사항 검색 질문** (정상 답변):
   - 관련 공지사항이 있으면 상세 내용을 검색하여 답변
   - **중요: 답변 끝에 "다른 질문 있으신가요?" 등의 상투적인 멘트나 예시 질문 목록을 붙이지 마세요. 공지사항 내용만 깔끔하게 전달하세요.**
   - 형식:
     ```
     📌 [공지사항 제목]
     • 담당부서: [부서명]
     • 공지일자: [날짜]
     • 상세내용: [내용 전체]
     ```
   - 여러 개 있으면 최대 3개까지 표시
   - 답변 시작에 "TYPE:NORMAL"을 포함하지 마세요.
   - **공지사항 내용 중 "문의사항은 ~로 연락 바랍니다", "내선 XXXX" 등 단순 연락처 안내 문구는 제외하고 작성하세요.**

3. **정보 없음**:
   - 질문과 관련된 공지사항이 없으면:
   - 반드시 "TYPE:MISSING"으로 시작
   - 예: "TYPE:MISSING 죄송합니다. [질문 키워드]에 대한 공지사항을 찾을 수 없습니다."
   - **예시 질문을 덧붙이지 마세요.**

4. **업무 무관 질문**:
   - 날씨, 맛집, 게임 등 업무와 무관한 질문:
   - 반드시 "TYPE:IRRELEVANT"로 시작
   - 예: "TYPE:IRRELEVANT 죄송합니다. 저는 효성전기 공지사항에 대해서만 답변할 수 있습니다. 대신 이런걸 물어보세요: [예시 질문 1], [예시 질문 2]"
   - **이 경우에만 예시 질문을 함께 제공하세요.**

**답변 스타일:**
- 존댓말 사용
- 친근하고 도움이 되는 톤
- 공지사항 정보는 구조화하여 읽기 쉽게 제공
- 날짜, 부서, 담당자 등 메타데이터 포함

**공지사항 데이터:**
{context}

**사용자 질문:** {user_query}

위 공지사항을 참고하여 답변해주세요.

    def _call_potens_api(self, prompt: str) -> str:
        """
        POTENS API 호출

        Args:
            prompt: 프롬프트

        Returns:
            API 응답 텍스트
        """
        if not self.api_key:
            return "TYPE:MISSING POTENS API 키가 설정되지 않았습니다. 관리자에게 문의하세요."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt}

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=RESPONSE_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()

            # 응답 파싱 (여러 형식 지원)
            return (
                result.get("response") or
                result.get("answer") or
                result.get("text") or
                result.get("message") or
                result.get("content") or
                str(result)
            ).strip()
        except requests.exceptions.Timeout:
            return "TYPE:MISSING API 요청 시간이 초과되었습니다. 다시 시도해주세요."
        except requests.exceptions.RequestException as e:
            return f"TYPE:MISSING API 호출 실패: {str(e)}"
        except Exception as e:
            return f"TYPE:MISSING 오류 발생: {str(e)}"

    def _detect_response_type(self, response: str) -> str:
        """
        응답 타입 분류

        Args:
            response: API 응답

        Returns:
            "NORMAL" | "MISSING" | "IRRELEVANT"
        """
        if "TYPE:MISSING" in response:
            return "MISSING"
        elif "TYPE:IRRELEVANT" in response:
            return "IRRELEVANT"
        else:
            return "NORMAL"

    def _clean_response(self, response: str) -> str:
        """
        응답 정리 (TYPE: 접두사 제거)

        Args:
            response: 원본 응답

        Returns:
            정리된 응답
        """
        if response.startswith("TYPE:"):
            parts = response.split("\n", 1)
            return parts[1].strip() if len(parts) > 1 else response.replace("TYPE:MISSING ", "").replace("TYPE:IRRELEVANT ", "")
        return response

    def _extract_notice_refs(self, response: str, notices: List[Dict]) -> List[int]:
        """
        참조된 공지 ID 추출

        Args:
            response: 챗봇 응답
            notices: 공지 리스트

        Returns:
            참조된 공지 ID 리스트
        """
        refs = []
        for notice in notices:
            # 제목이 응답에 포함되어 있으면 참조로 간주
            if notice['title'] in response:
                refs.append(notice['post_id'])
        return refs[:3]  # 최대 3개

    def _extract_keywords(self, query: str) -> List[str]:
        """
        질문에서 키워드 추출 (간단한 버전)

        Args:
            query: 사용자 질문

        Returns:
            키워드 리스트
        """
        # 불용어 제거 및 단어 추출
        stopwords = ['은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '으로', '로', '에서', '있', '없', '하', '되']
        words = query.split()
        keywords = [w for w in words if len(w) > 1 and w not in stopwords]
        return keywords[:5]  # 최대 5개

    def _save_chat_log(
        self,
        query: str,
        response: str,
        response_type: str,
        refs: List[int],
        keywords: List[str]
    ):
        """
        채팅 로그 저장

        Args:
            query: 사용자 질문
            response: 챗봇 응답
            response_type: 응답 타입
            refs: 참조 공지 ID
            keywords: 키워드
        """
        created_at = int(time.time() * 1000)

        with get_conn() as conn:
            if USE_POSTGRES:
                # PostgreSQL
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO chat_logs
                    (user_id, user_query, bot_response, response_type, notice_refs, keywords, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.user_id,
                    query,
                    response,
                    response_type,
                    json.dumps(refs),
                    json.dumps(keywords, ensure_ascii=False),
                    created_at
                ))
                conn.commit()
            else:
                # SQLite
                conn.execute("""
                    INSERT INTO chat_logs
                    (user_id, user_query, bot_response, response_type, notice_refs, keywords, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id,
                    query,
                    response,
                    response_type,
                    json.dumps(refs),
                    json.dumps(keywords, ensure_ascii=False),
                    created_at
                ))

    # ===== 팝업 연동 기능 =====

    def check_pending_popups(self) -> Optional[Dict]:
        """
        미확인 팝업 조회

        Returns:
            미확인 팝업 정보 또는 None
        """
        import service
        return service.get_latest_popup_for_employee(self.user_id)

    def confirm_popup_from_chat(self, popup_id: int) -> bool:
        """
        챗봇에서 팝업 확인 처리

        Args:
            popup_id: 팝업 ID

        Returns:
            성공 여부
        """
        import service
        return service.confirm_popup_action(self.user_id, popup_id)

    def search_notices(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        키워드로 공지 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수 (기본값 20개로 증가)

        Returns:
            검색된 공지 리스트 (날짜 기준 내림차순)
        """
        with get_conn() as conn:
            if USE_POSTGRES:
                cur = conn.cursor()
                cur.execute("""
                    SELECT post_id, title, content, department, date, type
                    FROM notices
                    WHERE title LIKE %s OR content LIKE %s OR department LIKE %s
                    ORDER BY
                        CASE
                            WHEN date IS NOT NULL THEN date::date
                            ELSE (created_at / 1000)::int::abstime::date
                        END DESC,
                        post_id DESC
                    LIMIT %s
                """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                cur = conn.execute("""
                    SELECT post_id, title, content,
                           COALESCE(department, '전체') as department,
                           COALESCE(date, strftime('%Y-%m-%d', created_at/1000, 'unixepoch')) as date,
                           type
                    FROM notices
                    WHERE title LIKE ? OR content LIKE ? OR department LIKE ?
                    ORDER BY
                        CASE
                            WHEN date IS NOT NULL THEN date
                            ELSE strftime('%Y-%m-%d', created_at/1000, 'unixepoch')
                        END DESC,
                        post_id DESC
                    LIMIT ?
                """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
                return [dict(r) for r in cur.fetchall()]

    def summarize_query(self, user_query: str) -> str:
        """
        사용자 질문을 사이드바 레이블용으로 요약 (최대 15자)

        Args:
            user_query: 사용자 질문

        Returns:
            요약된 문자열 (최대 15자)
        """
        # 질문이 짧으면 그대로 반환
        if len(user_query) <= 15:
            return user_query

        # 간단한 규칙 기반 요약
        # 불용어 제거
        stopwords = ['알려줘', '알려주세요', '무엇', '어떻게', '언제', '어디서',
                     '누가', '왜', '있어', '해줘', '대해', '관련', '안내', '요', '요?']

        # 단어 추출
        words = user_query.split()
        keywords = []
        for word in words:
            # 불용어가 아니고, 2글자 이상인 단어만 추가
            if word not in stopwords and len(word) >= 2:
                keywords.append(word)

        # 키워드로 요약 생성
        if keywords:
            summary = ' '.join(keywords[:3])  # 최대 3개 키워드
            if len(summary) > 15:
                summary = summary[:15]
            return summary

        # 키워드가 없으면 원본 문자열 앞부분
        return user_query[:15]
