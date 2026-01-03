# 문제 해결 가이드

## 챗봇 페이지 404 에러

### 증상
브라우저 콘솔에 다음과 같은 에러 표시:
```
GET http://localhost:8501/chatbot/_stcore/health 404 (Not Found)
GET http://localhost:8501/chatbot/_stcore/host-config 404 (Not Found)
```

### 원인
Streamlit 멀티페이지 앱의 URL 라우팅 이슈. 브라우저가 `/chatbot/`을 베이스 경로로 인식하고 있음.

### 해결 방법

#### 방법 1: 브라우저 캐시 초기화 (권장)
1. 브라우저 캐시 완전 삭제:
   - **Chrome**: Cmd+Shift+Delete → "캐시된 이미지 및 파일" 선택 후 삭제
   - **Safari**: Cmd+Option+E → 캐시 비우기

2. 또는 **시크릿/프라이빗 모드**로 접속

3. Streamlit 서버 재시작:
   ```bash
   # 터미널에서 Ctrl+C로 서버 종료
   streamlit run app.py
   ```

4. **루트 URL로 접속**: `http://localhost:8501` (❌ `/chatbot`로 직접 접속 금지)

5. 로그인 후 사이드바에서 "챗봇" 버튼 클릭

#### 방법 2: 하드 리프레시
1. 페이지에서 **Cmd+Shift+R** (Mac) 또는 **Ctrl+Shift+R** (Windows)
2. 루트 URL(`http://localhost:8501`)로 이동
3. 사이드바에서 "챗봇" 클릭

#### 방법 3: 포트 변경
다른 포트로 서버 실행:
```bash
streamlit run app.py --server.port 8502
```
그 후 `http://localhost:8502` 접속

### 예방 방법
- 챗봇 페이지 URL을 북마크하지 말 것
- 항상 루트 URL(`http://localhost:8501`)부터 접속
- 페이지 이동은 사이드바 메뉴 사용

---

## POTENS API 키 미설정 경고

### 증상
챗봇에서 질문 시 다음 메시지 표시:
```
POTENS API 키가 설정되지 않았습니다. 관리자에게 문의하세요.
```

### 해결 방법
1. 프로젝트 루트에 `.env` 파일 생성:
   ```bash
   POTENS_API_KEY=your_api_key_here
   POTENS_API_URL=https://ai.potens.ai/api/chat
   ```

2. Streamlit 서버 재시작

---

## PostgreSQL 연결 실패 (Railway 배포 시)

### 증상
Railway 배포 후 데이터베이스 연결 실패

### 해결 방법
1. Railway 대시보드에서 `DATABASE_URL` 환경 변수 확인
2. PostgreSQL 플러그인이 추가되었는지 확인
3. `sql/schema_postgres.sql` 파일이 있는지 확인
4. 초기화 스크립트 실행:
   ```bash
   railway run python init_railway_db.py
   ```

---

## 챗봇 통계 "no such table: chat_logs" 에러

### 해결 방법
데이터베이스 재초기화:
```bash
python3 -c "from core.db import init_db; init_db()"
```

---

## 파일 업로드 실패 (Railway)

### 원인
Railway의 임시 파일 시스템 - 재배포 시 파일 삭제됨

### 해결 방법
Cloudflare R2 설정:
1. Cloudflare 계정에서 R2 버킷 생성
2. Railway 환경 변수 설정:
   ```
   R2_ACCOUNT_ID=your_account_id
   R2_ACCESS_KEY_ID=your_access_key
   R2_SECRET_ACCESS_KEY=your_secret_key
   R2_BUCKET_NAME=your_bucket_name
   R2_PUBLIC_URL=https://your-bucket.r2.dev
   ```

---

## 일반적인 Streamlit 에러

### "Please replace use_container_width with width" 경고
Streamlit 버전 업데이트로 인한 deprecation 경고. 기능에는 영향 없음.

### 페이지 리로드 시 로그인 상태 초기화
정상 동작. Streamlit은 세션 상태를 메모리에 저장하므로 페이지 새로고침 시 초기화됨.

### 여러 다이얼로그 열림 경고
다이얼로그를 닫지 않고 다른 액션 시도 시 발생. 다이얼로그를 먼저 닫을 것.

---

## 도움이 필요하면

1. 통합 검증 스크립트 실행:
   ```bash
   python3 verify_integration.py
   ```

2. 로그 확인:
   ```bash
   # Streamlit 로그
   tail -f ~/.streamlit/logs/streamlit.log
   ```

3. 이슈 보고:
   - [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md) 참조
   - [RAILWAY_INTEGRATION_PLAN.md](./RAILWAY_INTEGRATION_PLAN.md) 참조
