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

        # 3. 관리자인 경우 키워드 통계 추가
        is_admin = (self.user_id == "admin")
        keyword_stats_text = ""
        
        if is_admin:
            import service
            keyword_stats = service.get_chatbot_keyword_stats()
            if keyword_stats:
                # 전체 키워드 TOP 10 추출
                total_keywords = keyword_stats.get("전체", {})
                if total_keywords:
                    top_keywords = sorted(total_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
                    keyword_list = [f"{kw} ({count}회)" for kw, count in top_keywords]
                    keyword_stats_text = f"\n\n**[관리자 전용] 직원들이 최근 자주 질문한 키워드 TOP 10:**\n" + ", ".join(keyword_list)

        # 4. 프롬프트 생성 (관리자면 키워드 통계 포함)
        prompt = self._build_prompt(user_query, context, keyword_stats_text if is_admin else "")

        # 5. POTENS API 호출
        response_text = self._call_potens_api(prompt)

        # 6. 응답 타입 분류
        response_type = self._detect_response_type(response_text)

        # 7. 참조 공지 추출 (LLM 답변 내 [제목] 등 매칭)
        notice_refs = self._extract_notice_refs(response_text, recent_notices)
        
        # 추가 공지 풀 (검색 결과 저장용)
        extra_notices = []

        # 7-1. 키워드 추출
        keywords = self._extract_keywords(user_query)

        # 7-2. 만약 참조된 공지가 없다면, 키워드 검색으로 보완
        if not notice_refs and response_type == "NORMAL":
            # 가장 긴 키워드 우선 사용 (구체적일 확률 높음)
            search_keywords = sorted(keywords, key=len, reverse=True)
            for kw in search_keywords[:2]:  # 상위 2개 키워드로 시도
                found = self.search_notices(kw, limit=3)
                if found:
                    for f in found:
                        if f['post_id'] not in notice_refs:
                            notice_refs.append(f['post_id'])
                            extra_notices.append(f)
                    
                    # 3개 찾으면 중단
                    if len(notice_refs) >= 3:
                        notice_refs = notice_refs[:3]
                        break
        
        # 8. 참조 공지 상세 정보 생성 (ID + 제목)
        # recent_notices와 extra_notices를 합쳐서 조회
        all_pool = recent_notices + extra_notices
        # 중복 제거 (딕셔너리는 해시 불가능하므로 post_id 기준)
        seen_ids = set()
        unique_pool = []
        for n in all_pool:
            if n['post_id'] not in seen_ids:
                unique_pool.append(n)
                seen_ids.add(n['post_id'])

        notice_details = []
        for ref_id in notice_refs:
            notice = next((n for n in unique_pool if n['post_id'] == ref_id), None)
            if notice:
                notice_details.append({
                    "post_id": ref_id,
                    "title": notice['title']
                })

        # 9. 로그 저장
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
            "notice_details": notice_details,  # 제목 포함 상세 정보 추가
            "keywords": keywords
        }
    def _get_recent_notices(self, limit: int = 100) -> List[Dict]:
        """
        최근 공지 조회 (통합 DB)

        Args:
            limit: 조회할 공지 개수 (기본값 100개)

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
                            ELSE to_timestamp(created_at / 1000)::date
                        END DESC,
                        post_id DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                # RealDictCursor는 이미 dict-like 객체를 반환
                return [dict(row) for row in rows]
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
            # 공지 내용 준비 (최대 1500자, 더 긴 답변 가능하도록)
            content = n['content']
            if len(content) > 1500:
                content = content[:1500] + "..."

            parts.append(
                f"[공지 {i}]\n"
                f"제목: {n['title']}\n"
                f"부서: {n.get('department', '전체')}\n"
                f"날짜: {n.get('date', '')}\n"
                f"유형: {n.get('type', '일반')}\n"
                f"내용: {content}\n"
            )
        return "\n".join(parts)

    def _build_prompt(self, user_query: str, context: str, keyword_stats: str = "") -> str:
        """
        프롬프트 생성 (노티가드 시스템 프롬프트)

        Args:
            user_query: 사용자 질문
            context: 공지 컨텍스트
            keyword_stats: 키워드 통계 (관리자만)

        Returns:
            프롬프트 문자열
        """
        # 관리자 전용 안내 추가
        admin_guidance = ""
        if keyword_stats:
            admin_guidance = f"""
**[관리자 모드 안내]**
당신은 현재 관리자와 대화하고 있습니다. 아래는 직원들이 최근 자주 질문한 키워드 통계입니다:
{keyword_stats}

관리자가 이 키워드들에 대해 질문하면, 해당 키워드와 관련된 공지사항을 찾아 상세히 안내해주세요.
관리자가 "직원들이 자주 묻는 질문", "많이 질문하는 내용" 등을 물으면 위 키워드 TOP 10을 보기 좋게 정리하여 알려주세요.

"""

        return f"""당신은 효성전기의 공지사항 알림 챗봇 '노티가드(NotiGuard)'입니다.
{admin_guidance}
**자기소개 (메타 질문 대응):**
사용자가 "너는 누구니?", "무엇을 할 수 있어?", "어떻게 사용해?" 등의 질문을 하면:
- 자신을 '노티가드'로 소개하고, 효성전기 공지사항 검색 및 안내를 돕는 AI 챗봇임을 설명
- 공지사항 검색, 일정 안내, 부서별 공지 확인 등의 기능을 소개
- 예시 질문을 제공 (예: "안전교육 일정 알려줘", "인사팀 공지사항 보여줘")

**역할:**
- 효성전기 직원들의 공지사항 관련 질문에 친절하고 정확하게 답변합니다.
- 제공된 공지사항 데이터베이스를 기반으로만 답변합니다.
- 공지사항 내용을 **이해하고 핵심만 요약**하여 사용자 질문에 맞게 답변합니다.
- **중요: 공지사항 원문을 그대로 복사하지 말고, AI가 내용을 분석하여 핵심 정보만 간결하게 전달하세요.**
- **중요: 비슷한 내용의 공지사항이 여러 개 있을 경우, '날짜'가 가장 최신인 공지사항을 정답으로 간주하고 우선적으로 안내하세요.**

**답변 규칙:**
1. **메타 질문** (챗봇 자체에 대한 질문):
   - "너는 누구?", "뭐 할 수 있어?", "사용법" 등의 질문에는 자기소개와 기능 설명
   - 예시 질문을 함께 제공하여 사용자가 바로 질문할 수 있도록 유도

2. **공지사항 검색 질문** (정상 답변):
   - 관련 공지사항을 찾아서 **AI가 내용을 이해하고 핵심만 요약하여** 답변
   - **중요: 원문을 그대로 복사하지 말고, 사용자 질문에 필요한 정보만 추출하여 간결하게 설명하세요.**
   - **중요: 답변 끝에 "다른 질문 있으신가요?" 등의 상투적인 멘트나 예시 질문 목록을 붙이지 마세요.**
   - **중요: 관련 공지가 여러 개 있을 경우, 각 공지사항을 반드시 **빈 줄로 구분**하여 보기 좋게 표시하세요.**
   - **중요: 모든 정보를 한 줄로 압축하지 말고, 줄바꿈을 적극 활용하여 읽기 편하게 작성하세요.**

   - **공지사항이 1개**일 때:
     ```
      📌 [공지 제목]

     • **일시:** [날짜/시간]
     • **장소:** [장소명]
     • **대상:** [대상자]

     **내용:**
     [본문 내용을 충실하게 요약. 중요한 세부사항, 절차, 유의사항 등을 빠뜨리지 말고 포함. 문장 수 제한 없이 내용이 완전히 전달되도록 작성. 문단을 나누어 읽기 쉽게 작성]

     📋 담당부서: [부서명] | 공지일자: [날짜]
     ```

   - **공지사항이 2개 이상**일 때:
     ```
     총 [N]개의 공지사항을 찾았습니다:

     ---

     **1. [첫 번째 공지 제목]**

     • **일시:** [날짜/시간]
     • **장소:** [장소명]
     • **대상:** [대상자]

     **내용:**
     [본문 내용을 충실하게 요약. 중요한 세부사항, 절차, 유의사항 등을 빠뜨리지 말고 포함. 문장 수 제한 없이 내용이 완전히 전달되도록 작성. 문단을 나누어 읽기 쉽게 작성]

     ---

     **2. [두 번째 공지 제목]**

     • **일시:** [날짜/시간]
     • **장소:** [장소명]
     • **대상:** [대상자]

     **내용:**
     [본문 내용을 충실하게 요약. 중요한 세부사항, 절차, 유의사항 등을 빠뜨리지 말고 포함. 문장 수 제한 없이 내용이 완전히 전달되도록 작성. 문단을 나누어 읽기 쉽게 작성]

     ---

     **3. [세 번째 공지 제목]**

     • **일시:** [날짜/시간]
     • **장소:** [장소명]
     • **대상:** [대상자]

     **내용:**
     [본문 내용을 충실하게 요약. 중요한 세부사항, 절차, 유의사항 등을 빠뜨리지 말고 포함. 문장 수 제한 없이 내용이 완전히 전달되도록 작성. 문단을 나누어 읽기 쉽게 작성]
     ```
     **⚠️ 필수 규칙 - 반드시 지켜야 합니다:**
     1. "---"로 각 공지를 구분
     2. **절대 한 줄에 여러 bullet point를 작성하지 마세요!**
     3. **각 bullet point(• **일시:**, • **장소:**, • **대상:**) 뒤에는 반드시 줄바꿈(\n)을 넣으세요!**
     4. "내용" 부분은 문장 수 제한 없이 충실하게 요약

     **❌ 절대 하지 말아야 할 형식:**
     ```
     • 일시: 2025-01-27 • 장소: 본사 • 대상: 전체  (이렇게 한 줄로 쓰지 마세요!)
     ```

     **✅ 반드시 이렇게 작성:**
     ```
     • **일시:** 2025-01-27
     • **장소:** 본사
     • **대상:** 전체
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
- 존댓말 사용, 친근하고 도움이 되는 톤
- **원문 그대로가 아닌, AI가 이해하고 재구성한 자연스러운 문장으로 답변**
- 사용자 질문의 의도를 파악하여 필요한 정보를 충실하게 제공
- **공지사항 내용을 최대한 손실 없이 전달하되, AI가 읽기 쉽게 재구성**
- **문장 수 제한 없이 본문의 중요한 정보(배경, 목적, 절차, 대상, 일정, 유의사항 등)를 모두 포함**
- 일정, 마감일, 대상자 등 중요 정보는 **별도로 정리하여 강조**
- 불필요한 서론이나 부연 설명 없이 바로 핵심부터 전달
- **가독성을 위한 줄바꿈 규칙:**
  - bullet point(•)는 반드시 각 항목마다 줄바꿈
  - 긴 문단은 2-3문장마다 빈 줄로 구분
  - 제목과 본문 사이, 본문과 부가정보 사이에 빈 줄 추가
  - 나열되는 정보(일시, 장소, 대상)는 각각 별도 줄에 표시

**답변 예시 (참고용):**

❌ 나쁜 예 1 (원문 복사):
"📌 2025년 상반기 정기 인사평가 실시 안내 및 가이드라인
• 상세내용: 2025년 상반기 정기 인사평가가 시작됩니다. 모든 임직원 여러분께서는 아래 일정을 준수하여 주시기 바랍니다. 1. 평가 대상: 2024년 12월 31일 기준 재직 중인 전 직원 (수습기간 중인 직원 제외) 2. 평가 기간: - 본인 평가(Self-Review): 2025년 1월 20일(월) ~ 1월 24일(금)..."

✅ 좋은 예 1 (단일 공지 - AI 요약):
"📌 2025년 상반기 정기 인사평가 실시 안내

2025년 상반기 정기 인사평가가 실시됩니다. 모든 재직자(수습 직원 제외)가 평가 대상이며, 본인 평가부터 피드백 면담까지 약 한 달간 진행됩니다.

올해부터 평가 기준이 일부 변경되었습니다. 협업 능력 평가 비중이 기존 10%에서 20%로 상향 조정되었으며, 정량적 성과뿐만 아니라 정성적 노력 과정에 대한 서술이 필수화되었습니다. 또한 동료 피드백 시스템이 새롭게 도입되어 팀원 간 상호 평가가 반영됩니다.

평가는 4단계로 진행되며, 각 단계별로 시스템에서 평가 양식을 작성해야 합니다. 기한을 넘기면 자동으로 미제출 처리되므로 일정을 반드시 준수해 주시기 바랍니다. 평가 결과는 3월 초 개별 통보되며, 승진 및 보상 심사에 활용됩니다.

**주요 일정:**
• 본인 평가: 1월 20일~24일
• 1차 평가(팀장급): 1월 27일~31일
• 2차 평가(부문장급): 2월 3일~7일
• 피드백 면담: 2월 17일~21일

📋 담당부서: 인사팀 | 공지일자: 2025-01-15"

❌ 나쁜 예 2 (여러 공지 - 한 줄로 압축):
"1. 특허 출원 교육 • 일시: 2025년 2월 5일(수) 14:00~17:00 • 장소: 연구동 세미나실 • 대상...2. 안전사고 예방 교육 • 일시: 2025년 1월 24일(금) 15:00~16:30 • 장소: 생산동...3. SW 코딩 규칙 교육 • 일시: 2025년 1월 30일(목) 14:00 • 장소: 연구동..."

✅ 좋은 예 2 (여러 공지 - 줄바꿈과 구분선 활용):
"총 3개의 교육 일정을 안내드립니다:

---

**1. 특허 출원 교육**

• **일시:** 2025년 2월 5일(수) 14:00~17:00
• **장소:** 연구동 세미나실
• **대상:** 연구개발본부 전체

**내용:**
특허청 출신 전문 변리사를 초빙하여 특허 출원 실무 교육을 진행합니다. 특허 명세서 작성법, 선행기술조사 방법, 출원 절차 및 심사 대응 전략을 다루며, 실제 사례를 바탕으로 한 실습이 포함됩니다.

교육 이수자에게는 특허 출원 인센티브 지급 시 우대 혜택이 제공되며, 참석 확인서가 발급됩니다. 사전 신청이 필수이므로 1월 30일까지 인사시스템에서 신청해 주시기 바랍니다.

---

**2. 안전사고 예방 교육**

• **일시:** 2025년 1월 24일(금) 15:00~16:30
• **장소:** 생산동 2층 대회의실
• **대상:** 전 직원 필수 참석

**내용:**
산업안전보건법 개정사항과 2025년 회사 안전관리 방침을 안내하는 법정 필수 교육입니다. 작업장 안전수칙, 화재 대응 절차, 응급처치 방법, 안전보호구 착용 규정 등을 다룹니다.

미참석 시 개별 보충교육 대상이 되며, 안전관리 평가에 반영되므로 반드시 참석해 주시기 바랍니다. 불가피하게 참석이 어려운 경우 부서장 승인 하에 2월 5일 보충교육에 참석 가능합니다.

---

**3. SW 코딩 규칙 교육**

• **일시:** 2025년 1월 30일(목) 14:00~16:00
• **장소:** 연구동 1층 교육실
• **대상:** 소프트웨어 개발 담당자

**내용:**
사내 소프트웨어 코딩 표준 가이드라인 준수를 위한 교육입니다. 변수명 명명 규칙, 주석 작성법, 코드 리뷰 프로세스, 버전 관리 규칙 등 품질 관리 기법을 다룹니다.

2월부터 모든 신규 프로젝트에 코딩 표준 준수가 의무화되며, 분기별 코드 품질 감사가 시행됩니다. 교육 자료는 교육 후 사내 포털에 공유되며, 미참석자는 자료를 확인하고 온라인 퀴즈를 통과해야 합니다."

**공지사항 데이터베이스:**
{context}

---

**사용자 질문:**
{user_query}

**응답:**위 공지사항을 참고하여 답변해주세요."""

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
        응답 정리 (TYPE: 접두사 제거, bullet point 줄바꿈 자동 처리)

        Args:
            response: 원본 응답

        Returns:
            정리된 응답
        """
        # TYPE: 접두사 제거
        if response.startswith("TYPE:"):
            parts = response.split("\n", 1)
            response = parts[1].strip() if len(parts) > 1 else response.replace("TYPE:MISSING ", "").replace("TYPE:IRRELEVANT ", "")

        # bullet point 줄바꿈 처리
        # 한 줄에 여러 bullet point가 있는 경우 자동으로 분리
        lines = response.split('\n')
        fixed_lines = []

        for line in lines:
            # 한 줄에 2개 이상의 bullet point가 있는 경우 감지
            # 패턴: "• text • text" 또는 "• **label:** value • **label:** value"
            bullet_count = line.count('•')

            if bullet_count >= 2:
                # bullet point로 분리 (첫 번째 제외)
                parts = line.split('•')

                # 첫 번째 부분 처리 (빈 문자열이거나 공백일 수 있음)
                if parts[0].strip():
                    fixed_lines.append(parts[0].strip())

                # 나머지 bullet point들은 각각 새로운 줄로
                for part in parts[1:]:
                    if part.strip():
                        fixed_lines.append('• ' + part.strip())
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

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
        질문에서 키워드 추출 (개선된 버전)

        Args:
            query: 사용자 질문

        Returns:
            키워드 리스트
        """
        import re
        
        # 특수문자 제거 (정규식: 한글, 영문, 숫자, 공백만 허용)
        # '공지사항?' -> '공지사항 '
        query_clean = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', query)
        words = query_clean.split()
        
        stopwords = [
            '은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '으로', '로', '에서', '부터', '까지',
            '있다', '없다', '이다', '아니다', '하다', '되다', '않다', '같다', '싶다',
            '알려줘', '알려주세요', '알려', '주세요', '해주세요', '해줘', '보여줘', '보여주세요',
            '무엇', '무엇인가요', '어디', '어디서', '언제', '누구', '어떻게', '왜', 
            '궁금해', '궁금해요', '질문', '문의', '사항', '관련', '대한', '대해', '대하여',
            '안녕', '안녕하세요', '반가워', '반갑습니다', '감사', '고마워',
            '공지', '사항', '확인', '방법', '좀', '수', '할', '한', '데', '건', '것',
            '저', '나', '너', '우리', '그', '이', '저', '요', '네', '아니요',
            '이번', '저번', '다음', '오늘', '내일', '어제', '지금', '현재'
        ]
        
        keywords = []
        for w in words:
            w = w.strip()
            # 2글자 이상이고 불용어가 아닌 경우만
            if len(w) > 1 and w not in stopwords:
                keywords.append(w)
                
        # 중복 제거 (순서 유지)
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                unique_keywords.append(k)
                seen.add(k)

        return unique_keywords[:5]  # 최대 5개

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
                            ELSE to_timestamp(created_at / 1000)::date
                        END DESC,
                        post_id DESC
                    LIMIT %s
                """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
                rows = cur.fetchall()
                # RealDictCursor는 이미 dict-like 객체를 반환
                return [dict(row) for row in rows]
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

    # ===== 담당자 문의 기능 =====

    def detect_target_department(self, user_query: str) -> str:
        """
        사용자 질문을 분석하여 관련 부서 감지

        Args:
            user_query: 사용자 질문

        Returns:
            감지된 부서명 (없으면 "경영관리본부")
        """
        from core.config import DEPARTMENT_EMAILS

        query_lower = user_query.lower()

        # 키워드 매핑
        keyword_map = {
            "재경팀": ["재무", "회계", "비용", "경비", "세금", "카드", "급여", "예산"],
            "연구1팀": ["연구", "개발", "설계", "프로젝트", "기술"],
            "연구2팀": ["연구2", "연구 2"],
            "생산팀": ["생산", "제조", "공장", "생산성"],
            "품질팀": ["품질", "검사", "테스트", "불량"],
            "영업1팀": ["영업", "판매", "고객", "수주"],
            "경영관리본부": ["인사", "채용", "휴가", "연차", "복지", "총무", "시설"]
        }

        # 키워드 매칭
        for dept, keywords in keyword_map.items():
            if dept in DEPARTMENT_EMAILS and any(k in query_lower for k in keywords):
                return dept

        # 기본값: 경영관리본부
        return "경영관리본부"

    def refine_email_content(self, target_dept: str, user_query: str, current_content: str) -> str:
        """
        AI를 사용하여 이메일 내용을 격식있게 다듬기

        Args:
            target_dept: 대상 부서
            user_query: 원본 질문
            current_content: 사용자가 작성한 초안

        Returns:
            다듬어진 이메일 내용
        """
        prompt = f"""당신은 비즈니스 이메일 작성 전문가입니다.

사용자가 {target_dept} 담당자에게 다음과 같은 질문으로 문의 이메일을 작성하려고 합니다:

**원본 질문:** {user_query}

**사용자가 작성한 초안:**
{current_content}

위 내용을 바탕으로 격식 있고 전문적인 비즈니스 이메일로 다듬어주세요.

**작성 가이드:**
- 존댓말과 정중한 어투 사용
- 간결하고 명확하게 요점 전달
- 인사말과 맺음말 포함
- 문단 구분을 명확히
- 과도한 꾸밈말이나 불필요한 내용 제거

**이메일 형식:**
안녕하십니까, {target_dept} 담당자님.
효성전기 [소속] [이름]입니다.

[본문 내용]

확인 부탁드립니다.
감사합니다.
"""

        try:
            response = self._call_potens_api(prompt)
            # TYPE: 접두사 제거
            response = self._clean_response(response)
            return response
        except Exception as e:
            print(f"AI 다듬기 실패: {e}")
            # 실패 시 기본 포맷 반환
            return f"""안녕하십니까, {target_dept} 담당자님.
효성전기 직원입니다.

다음과 같은 내용으로 문의드립니다:

{user_query}

{current_content}

확인 부탁드립니다.
감사합니다."""
