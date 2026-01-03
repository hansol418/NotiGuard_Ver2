# 🚀 Railway 배포 최종 준비 완료

## ✅ 완료된 작업

### 1. CRUD 구현 완료
- ✅ `service.py`: `update_post()`, `delete_post()` 함수 추가
- ✅ `pages/admin.py`: 게시글 수정/삭제 UI 구현
- ✅ 수정 화면: 기존 데이터 로드, 첨부파일 유지 및 추가 지원

### 2. 챗봇 모달 구현 완료
- ✅ `core/layout.py`: 플로팅 위젯 JavaScript 트리거 방식 변경
- ✅ `core/layout.py`: `render_chatbot_modal()` 함수 구현
- ✅ `pages/admin.py`, `pages/employee.py`: 챗봇 모달 통합
- ✅ 400px 스크롤 가능한 채팅 컨테이너, 대화 초기화 기능

### 3. Cloudflare R2 스토리지 설정 완료
- ✅ R2 버킷 생성: `notiguard-files`
- ✅ `.env` 파일 R2 자격증명 추가
- ✅ `core/storage.py`: 환경 자동 감지 (로컬 vs Railway)
- ✅ `service.py`: `save_attachments()` R2 통합
- ✅ `.gitignore`: 민감 정보 제외 설정

### 4. PostgreSQL 마이그레이션 완료
- ✅ `sql/schema_postgres.sql`: PostgreSQL 호환 스키마
- ✅ `init_railway_db.py`: DB 초기화 스크립트
- ✅ `Procfile`: Railway 실행 명령어
- ✅ bcrypt 비밀번호 해시 생성 로직

### 5. 버그 수정 완료
- ✅ POTENS API 403 에러: `core/chatbot_engine.py`에 `load_dotenv()` 추가
- ✅ fetchone() 이중 호출 버그 수정
- ✅ `admin.py`에 `import time` 추가

---

## 📋 Railway 배포 단계별 가이드

### STEP 1: Railway 프로젝트 생성

1. **Railway 로그인**
   ```
   https://railway.app/
   ```

2. **New Project 클릭**
   - "Deploy from GitHub repo" 선택
   - GitHub 계정 연결 및 저장소 선택
   - 또는 "Empty Project" → 수동 Git 연결

3. **PostgreSQL 추가**
   - "+ New" 클릭
   - "Database" → "PostgreSQL" 선택
   - 자동으로 `DATABASE_URL` 환경변수 생성됨

---

### STEP 2: 환경변수 설정

Railway 프로젝트 → Variables 탭에서 다음 8개 변수 추가:

```bash
# POTENS AI API
POTENS_API_KEY=Q1QJ6jIOTp0369I9PXCFa3GxMyzY4hHh
POTENS_API_URL=https://ai.potens.ai/api/chat
RESPONSE_TIMEOUT=30

# Cloudflare R2 Storage
R2_ACCOUNT_ID=0dc39b053d6ec32088191ddbabcd40be
R2_ACCESS_KEY_ID=1bf722054c3ed6018841ca3128593003
R2_SECRET_ACCESS_KEY=f18ff1a1e342e2b979c6d4ebd80fa5b25a0f2ab22565613387e39ed8bb332098
R2_BUCKET_NAME=notiguard-files
R2_PUBLIC_URL=

# PostgreSQL (자동 생성됨)
DATABASE_URL=postgresql://...
```

⚠️ **중요**: Railway는 자동으로 `RAILWAY_ENVIRONMENT` 변수를 생성하므로 별도 설정 불필요

---

### STEP 3: Git Push 및 배포

1. **민감 정보 제외 확인**
   ```bash
   # .gitignore가 다음 파일들을 제외하는지 확인
   cat .gitignore

   # 확인 항목:
   # - .env
   # - docs/cloudflare.txt
   # - *.db
   # - uploads/
   ```

2. **Git Commit & Push**
   ```bash
   git add .
   git commit -m "Railway 배포 준비 완료 - PostgreSQL 스키마, R2 스토리지, 챗봇 모달"
   git push origin main
   ```

3. **자동 배포 확인**
   - Railway가 자동으로 빌드 시작
   - Logs 탭에서 배포 진행상황 확인
   - "Build successful" 메시지 확인

---

### STEP 4: 데이터베이스 초기화

배포 완료 후 **반드시** 실행:

```bash
railway run python init_railway_db.py
```

**예상 출력:**
```
======================================================================
🚀 Railway PostgreSQL 데이터베이스 초기화
======================================================================
✅ PostgreSQL 연결 성공

📋 1. 스키마 파일 실행...
✅ 스키마 실행 완료

🔐 2. 계정 비밀번호 설정...
  ✅ admin (password: 1234)
  ✅ HS001 (password: 1234)
  ✅ HS002 (password: 1234)
  ✅ HS003 (password: 1234)
✅ 계정 설정 완료

📊 3. 테이블 확인...
생성된 테이블: 8개
  - accounts
  - chat_logs
  - employees
  - notice_files
  - notices
  - popup_logs
  - popups

👤 4. 기본 데이터 확인...
  직원: 3명
  계정: 4개
  공지사항: 0개

======================================================================
✅ 데이터베이스 초기화 완료!
======================================================================

📝 로그인 계정:
  관리자: admin / 1234
  직원1: HS001 / 1234 (김산, 경영관리본부)
  직원2: HS002 / 1234 (이하나, 연구개발본부)
  직원3: HS003 / 1234 (홍길동, 연구개발본부)

⚠️  보안: 프로덕션 환경에서는 기본 비밀번호를 변경하세요!
```

---

### STEP 5: 배포 테스트

Railway에서 제공하는 URL로 접속하여 다음 항목 테스트:

#### 1. 로그인 테스트
```
계정: admin
비밀번호: 1234
```
- ✅ 로그인 성공
- ✅ 관리자 대시보드 표시

#### 2. 게시판 CRUD 테스트
- ✅ 새 공지사항 작성
- ✅ 파일 첨부 (R2 업로드 확인)
- ✅ 게시글 조회 (조회수 증가 확인)
- ✅ 게시글 수정 (제목/내용/첨부파일)
- ✅ 게시글 삭제

**R2 업로드 확인 방법:**
- Cloudflare Dashboard → R2 → notiguard-files 버킷
- uploads/ 폴더에 파일이 업로드되었는지 확인

#### 3. 챗봇 모달 테스트
- ✅ 우측 하단 플로팅 위젯 클릭
- ✅ 모달 팝업 열림 (새 탭 아님)
- ✅ 질문 입력: "교육일정 확인"
- ✅ POTENS AI 응답 수신
- ✅ 대화 초기화 버튼 작동
- ✅ 닫기 버튼 작동

#### 4. 직원 계정 테스트
- ✅ 로그아웃 후 HS001/1234로 로그인
- ✅ 직원 대시보드 표시
- ✅ 팝업 알림 기능 확인
- ✅ 챗봇 모달 작동 확인

---

## 🗂️ 생성된 파일 목록

### Railway 배포 필수 파일
- ✅ `sql/schema_postgres.sql` - PostgreSQL 스키마
- ✅ `init_railway_db.py` - DB 초기화 스크립트
- ✅ `Procfile` - Railway 실행 명령어

### 문서 파일
- ✅ `R2_STORAGE_SETUP.md` - R2 스토리지 설정 가이드
- ✅ `RAILWAY_DEPLOY_GUIDE.md` - Railway 배포 가이드
- ✅ `RAILWAY_READY_CHECKLIST.md` - 배포 체크리스트
- ✅ `CRUD_IMPLEMENTATION.md` - CRUD 구현 문서
- ✅ `CHATBOT_MODAL_IMPLEMENTATION.md` - 챗봇 모달 구현 문서
- ✅ `BUGFIX_ENV_LOADING.md` - 환경변수 로딩 버그 수정 문서

---

## 📊 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway 배포                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  Streamlit   │ ───► │ PostgreSQL   │                    │
│  │  App Server  │      │  Database    │                    │
│  │              │      │              │                    │
│  │  - app.py    │      │ - notices    │                    │
│  │  - admin.py  │      │ - popups     │                    │
│  │  - employee  │      │ - employees  │                    │
│  └──────┬───────┘      │ - accounts   │                    │
│         │              │ - chat_logs  │                    │
│         │              └──────────────┘                    │
│         │                                                   │
│         ├──────────────────────────────────────┐           │
│         │                                       │           │
│         ▼                                       ▼           │
│  ┌──────────────┐                      ┌──────────────┐   │
│  │ POTENS.ai    │                      │ Cloudflare   │   │
│  │ Chatbot API  │                      │ R2 Storage   │   │
│  │              │                      │              │   │
│  │ - 노티가드    │                      │ - 첨부파일    │   │
│  │ - 공지검색    │                      │ - 이미지      │   │
│  └──────────────┘                      └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 보안 체크리스트

- ✅ `.env` 파일 Git 제외 (.gitignore)
- ✅ `docs/cloudflare.txt` Git 제외
- ✅ Railway 환경변수로 자격증명 관리
- ✅ bcrypt 비밀번호 해시 사용
- ⚠️  **프로덕션 배포 후**: 기본 비밀번호 1234 변경 필수

---

## 📝 기본 로그인 계정

| 계정    | 비밀번호 | 권한      | 직원ID | 이름   | 소속               |
|---------|---------|-----------|--------|--------|-------------------|
| admin   | 1234    | ADMIN     | -      | -      | -                 |
| HS001   | 1234    | EMPLOYEE  | HS001  | 김산   | 경영관리본부/재경팀 |
| HS002   | 1234    | EMPLOYEE  | HS002  | 이하나 | 연구개발본부/연구1팀|
| HS003   | 1234    | EMPLOYEE  | HS003  | 홍길동 | 연구개발본부/연구2팀|

---

## ⚡ 주요 기능

### 1. 게시판 (CRUD 완전 구현)
- ✅ 공지사항 생성 (중요/일반)
- ✅ 목록 조회 (페이징, 검색)
- ✅ 상세 조회 (조회수 증가)
- ✅ 게시글 수정 (제목/내용/첨부파일)
- ✅ 게시글 삭제 (CASCADE)

### 2. 첨부파일 시스템
- ✅ 로컬 환경: `uploads/` 폴더
- ✅ Railway 환경: Cloudflare R2 스토리지
- ✅ 자동 환경 감지 (`IS_RAILWAY` 플래그)
- ✅ 다운로드 링크 자동 생성

### 3. 노티가드 AI 챗봇
- ✅ POTENS.ai API 통합
- ✅ 모달 다이얼로그 방식
- ✅ 공지사항 검색 및 요약
- ✅ 대화 이력 관리
- ✅ 챗봇 로그 DB 저장

### 4. 팝업 알림 시스템
- ✅ 부서/팀 타겟팅
- ✅ 직원별 팝업 로그
- ✅ 무시 횟수 관리
- ✅ 확인 여부 추적

---

## 🚨 배포 후 필수 작업

1. **기본 비밀번호 변경**
   - admin 계정 비밀번호 변경
   - 모든 직원 계정 초기 비밀번호 변경

2. **R2 공개 URL 설정** (선택사항)
   - Cloudflare R2에서 커스텀 도메인 설정
   - `.env`의 `R2_PUBLIC_URL` 업데이트

3. **모니터링 설정**
   - Railway Logs 탭에서 애플리케이션 로그 확인
   - PostgreSQL 성능 모니터링

4. **백업 계획**
   - PostgreSQL 자동 백업 설정
   - R2 버킷 버전 관리 활성화

---

## 📞 문제 해결

### Q: 배포 후 500 에러 발생
**A**: Railway Logs 탭 확인
- Python 패키지 설치 실패: `requirements.txt` 확인
- 환경변수 누락: Variables 탭에서 8개 변수 모두 설정되었는지 확인

### Q: 데이터베이스 연결 실패
**A**: `init_railway_db.py` 실행 확인
```bash
railway run python init_railway_db.py
```

### Q: 파일 업로드 실패
**A**: R2 자격증명 확인
- Railway Variables에서 R2_* 변수 확인
- Cloudflare R2 대시보드에서 버킷 존재 확인

### Q: 챗봇 응답 없음 (403 에러)
**A**: POTENS API 키 확인
- Railway Variables에서 `POTENS_API_KEY` 확인
- 키 유효성 테스트

---

## ✅ 최종 체크리스트

- ✅ PostgreSQL 스키마 파일 생성
- ✅ Procfile 생성
- ✅ init_railway_db.py 생성
- ✅ Cloudflare R2 버킷 생성
- ✅ .gitignore 민감 정보 제외
- ⏳ Railway 프로젝트 생성
- ⏳ 환경변수 8개 설정
- ⏳ Git Push 및 배포
- ⏳ init_railway_db.py 실행
- ⏳ 배포 테스트 (로그인, CRUD, 챗봇, 파일업로드)

---

## 🎯 다음 단계

**지금 바로 Railway 배포를 시작하세요!**

1. https://railway.app/ 접속
2. New Project → GitHub 연결
3. PostgreSQL 추가
4. 환경변수 8개 설정
5. Git Push
6. `railway run python init_railway_db.py` 실행
7. 배포 URL 접속하여 테스트

**모든 준비가 완료되었습니다! 🚀**
