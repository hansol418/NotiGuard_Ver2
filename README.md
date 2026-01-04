# 🏢 노티가드 그룹웨어 (NotiGuard Groupware)

> 효성전기 그룹웨어 공지/팝업 알림 + 요약 기능 - Streamlit MVP  
> Hyosung Electric Groupware Notice/Popup + Summary - Streamlit MVP

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)

> **🌐 Production URL**: (TBD)  
> ※ 현재 저장소 기준은 로컬/내부망 실행을 기본으로 합니다.

---

## 📋 프로젝트 개요 (Project Overview)

노티가드 그룹웨어는 **직원 공지 열람률 저하**와 **중요 공지 확인 지연** 문제를 해결하기 위한 사내 MVP입니다.  
관리자는 공지를 등록하고, **중요 공지(팝업)**는 대상(본부/팀)에게 강제 노출되며 직원은 **확인/나중/요약/챗봇 이동**으로 처리합니다.  
또한 공지는 **POTENS.ai API 기반 요약**을 제공하여 직원이 빠르게 핵심을 파악할 수 있도록 돕습니다.

NotiGuard Groupware is an internal MVP designed to improve **notice readership** and **timeliness**.  
Admins register notices and send **important popup notices** to specific targets (department/team). Employees can handle popups via confirm/ignore/summary/chatbot actions. Notice summaries are generated using **POTENS.ai API**.

---

## ✨ 주요 기능 (Key Features)

### 🧑‍💼 관리자 (Admin)
- 📝 **공지 CRUD**: 작성/조회/수정/삭제
- 🎯 **중요공지 팝업 발송**: 본부/팀 단위 대상 선택, 예약 전송 시간 설정
- 📎 **첨부파일 관리**: 이미지/파일 업로드 (Cloudflare R2 저장)
- 🤖 **AI 챗봇**: 공지사항 질의응답

### 👩‍💻 직원 (Employee)
- 📌 **중요공지 팝업 수신**: 5초 주기 자동 조회, 미응답 팝업 노출
- ✅ **팝업 처리**: 확인/나중/요약/챗봇
- 🧾 **AI 요약**: POTENS.ai 기반 공지 핵심 요약
- 🤖 **AI 챗봇**:
  - 플로팅 위젯 (우측 하단)
  - 챗봇 모달 (클릭 시 대화창)
  - 독립 챗봇 페이지
  - 공지사항 검색 및 질의응답

### 🔐 로그인/권한
- 🔑 **accounts 기반 로그인**: ADMIN / EMPLOYEE 역할 분리
- 🚫 권한 기반 페이지 접근 제어 (`st.switch_page`)

---

## 🛠️ 기술 스택 (Tech Stack)

| 카테고리 (Category) | 기술 (Technology) | 비고 (Notes) |
|---|---|---|
| **Language** | Python | 3.10+ |
| **Frontend** | Streamlit | Pages 구조 + `st.dialog` |
| **Database** | PostgreSQL / SQLite | Railway (프로덕션) / Local (개발) |
| **Storage** | Cloudflare R2 | 첨부파일 스토리지 |
| **AI** | POTENS.ai API | 챗봇 + 공지 요약 |
| **Libraries** | requests, python-dotenv, psycopg2, boto3 | API/환경변수/DB/스토리지 |

---

## 📁 프로젝트 구조 (Project Structure)

> ✅ 현재 실제 구조 기준 (POPUP_SERVICE-MAIN)

```text
Popup_Service-main/
├── app.py                          # 앱 엔트리포인트
├── service.py                      # 비즈니스 로직
├── Procfile                        # Railway 배포 설정
├── requirements.txt                # 패키지 의존성
├── README.md                       # 이 문서 (공개용)
│
├── core/                           # 핵심 모듈
│   ├── auth.py                     # 인증
│   ├── db.py                       # DB 연결 (PostgreSQL/SQLite)
│   ├── layout.py                   # UI 레이아웃
│   ├── summary.py                  # POTENS 요약
│   ├── chatbot_engine.py           # AI 챗봇 엔진 ✨
│   └── storage.py                  # R2 스토리지 ✨
│
├── pages/                          # Streamlit 페이지
│   ├── 0_Login.py                  # 로그인
│   ├── admin.py                    # 관리자 페이지
│   ├── employee.py                 # 직원 페이지
│   └── chatbot.py                  # 챗봇 페이지 ✨
│
├── sql/
│   └── schema.sql                  # DB 스키마
│
├── assets/                         # 정적 파일
│   ├── chatimg.png
│   └── chatimg_r.png
│
├── docs/                           # 📚 개발 문서 (민감정보 포함, Git 제외)
│   ├── CLAUDE.md                   # 로컬 개발 가이드
│   ├── DEPLOYMENT_COMPLETE.md      # 최종 배포 완료 문서 ✅
│   ├── RAILWAY_ENV_SETUP.md        # Railway 환경변수 가이드
│   └── ... (기타 기술 문서)
│
├── test_chatbot.py                 # 챗봇 테스트 ✨
├── test_potens_api.py              # API 테스트 ✨
├── init_railway_db.py              # Railway DB 초기화
└── migrate_files_to_r2.py          # 파일 R2 마이그레이션 ✨
```

✨ = 최근 추가된 파일

---

## 🚀 설치 및 실행 (Installation & Execution)

### 1. 사전 요구사항 (Prerequisites)
- Python 3.10+
- pip

### 2. 프로젝트 클론 (Clone Project)
```bash
git clone https://github.com/hansol418/Popup_Service.git
cd POPUP_SERVICE-MAIN
```

### 3. 가상환경 생성 및 활성화 (Create & Activate Virtual Environment)
```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
# venv\Scripts\activate
```

### 4. 필요 라이브러리 설치 (Install Dependencies)
```bash
pip install -r requirements.txt
```

### 5. 환경 변수 설정 (Environment Configuration)

`.env` 파일을 프로젝트 루트에 생성하고 필요한 환경변수를 입력합니다.

```env
# POTENS AI 챗봇 (필수)
POTENS_API_KEY=your_actual_api_key_here
POTENS_API_URL=https://ai.potens.ai/api/chat
RESPONSE_TIMEOUT=30

# Cloudflare R2 스토리지 (선택 - 로컬은 uploads/ 폴더 사용)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=notiguard-files
```

> ⚠️ `POTENS_API_KEY`가 없으면 챗봇/요약 기능에서 RuntimeError가 발생합니다.
>
> 📚 **상세 설정 가이드**: `docs/CLAUDE.md` 참조

### 6. 애플리케이션 실행 (Run Application)
```bash
streamlit run app.py
```

---

## 📖 사용 방법 (Usage Guide)

### 🔐 로그인 (Login)
- 앱 실행 시 `app.py`가 항상 `pages/0_Login.py`로 이동합니다.
- 로그인 성공 시 role에 따라 페이지가 분기됩니다.
  - ADMIN → `pages/admin.py`
  - EMPLOYEE → `pages/employee.py`

### 🧑‍💼 관리자 모드 (Admin Mode)
1. 좌측 사이드바에서 **게시판 / 글쓰기** 메뉴 사용
2. **글쓰기**
   - 공지 유형(중요/일반), 제목, 내용 입력
   - 첨부파일 업로드 가능 (이미지/파일)
3. **중요 공지 등록 시**
   - 대상 선택 모달이 열림 (본부/팀 선택 + 예약시간 선택)
   - “선택한 대상에게 팝업 발송” 시 popups 테이블에 등록

### 👩‍💻 직원 모드 (Employee Mode)
1. 홈 화면에서 **5초마다 중요공지(팝업) 조회**
2. 중요 공지가 도착하면 `st.dialog` 팝업 자동 노출
3. 팝업에서 처리 방식 선택:
   - **1. 확인함**: 2차 확인 후 확인 처리 로그 기록
   - **2. 나중에 확인**: ignore_remaining 차감 확인 + 로그 기록
   - **3. 요약 보기**: POTENS 요약 모달 표시(중첩 dialog 방지 구조)
   - **4. 챗봇으로 바로가기**: 외부 챗봇 링크 새 탭 열기 + 이동 로그 기록

---

## 🗄️ 데이터베이스 스키마 (Database Schema)

> `sql/schema.sql` 기준 (SQLite)

### notices (공지 게시글)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| post_id | INTEGER (PK) | 공지 ID |
| created_at | INTEGER | epoch ms |
| type | TEXT | '중요' / '일반' |
| title | TEXT | 제목 |
| content | TEXT | 내용 |
| author | TEXT | 작성자 |
| views | INTEGER | 조회수 |

### popups (중요공지 팝업)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| popup_id | INTEGER (PK) | 팝업 ID (post_id와 동일 사용) |
| post_id | INTEGER (FK) | notices 참조 |
| target_departments | TEXT | CSV(본부 목록) |
| target_teams | TEXT | CSV(팀 목록) |
| expected_send_time | TEXT | '오전 10시' / '오후 2시' |
| created_at | INTEGER | 생성 시각 |

### employees (직원)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| employee_id | TEXT (PK) | 사번 |
| name | TEXT | 이름 |
| department | TEXT | 본부 |
| team | TEXT | 팀 |
| ignore_remaining | INTEGER | 나중에 확인 가능 횟수 |

### popup_logs (팝업 처리 로그)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | INTEGER (PK) | 로그 ID |
| employee_id | TEXT | 직원 |
| popup_id | INTEGER | 팝업 |
| action | TEXT | '확인함'/'확인하지 않음'/'챗봇이동' |
| confirmed | TEXT | 2차확인 값 등 |

### accounts (로그인 계정)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| login_id | TEXT (PK) | 로그인 ID |
| password_hash | TEXT | 해시 비밀번호 |
| role | TEXT | 'ADMIN'/'EMPLOYEE' |
| employee_id | TEXT | 직원 계정 연결 (ADMIN은 NULL) |

### notice_files (첨부파일)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| file_id | INTEGER (PK) | 파일 ID |
| post_id | INTEGER (FK) | 공지 연결 |
| filename | TEXT | 원본 파일명 |
| mime_type | TEXT | MIME |
| file_path | TEXT | uploads 경로 |
| file_size | INTEGER | 파일 크기 |
| uploaded_at | INTEGER | 업로드 시각 |

---

## 🤖 공지 요약 (POTENS.ai Summary)

`core/summary.py`에서 공지 요약 프롬프트를 생성하고 POTENS API로 요청합니다.

- 요약 규칙:
  - 5줄 이내 핵심 요약
  - 일정/마감/대상/필수 행동이 있으면 마지막에 “해야 할 일”로 정리
  - 문의/내선 등 단순 연락 문구는 제외
  - 첨부 이미지가 본문과 연관되면 관련 내용도 포함

---

## 🧪 테스트 (Testing)

### 1) 관리자 테스트 시나리오
- 일반 공지 등록 → 게시판 리스트/상세 확인
- 중요 공지 등록 → 대상 선택 모달 → 팝업 생성 확인
- 첨부 이미지 업로드 → employee 팝업에서 이미지 표시 확인

### 2) 직원 테스트 시나리오
- 홈 화면에서 팝업 자동 노출 확인(5초 polling)
- “확인함” → 로그 기록 + 팝업 닫힘
- “나중에 확인” → ignore_remaining 차감 확인
- “요약 보기” → 요약 모달 단독 오픈(중첩 방지) 확인

---

## 🚢 배포 (Deployment)

### ✅ Railway 프로덕션 배포 완료 (2026-01-04)

- **플랫폼**: Railway
- **데이터베이스**: PostgreSQL (관리형)
- **스토리지**: Cloudflare R2
- **상태**: 정상 운영 중

### 배포 가이드

**📚 상세 가이드**: `docs/DEPLOYMENT_COMPLETE.md`, `docs/RAILWAY_ENV_SETUP.md` 참조

#### 필수 환경변수
```bash
DATABASE_URL=postgresql://...              # Railway 자동 설정
POTENS_API_KEY=<your_api_key>             # POTENS AI
POTENS_API_URL=https://ai.potens.ai/api/chat
RESPONSE_TIMEOUT=30
R2_ACCOUNT_ID=<your_account_id>           # Cloudflare R2
R2_ACCESS_KEY_ID=<your_access_key>
R2_SECRET_ACCESS_KEY=<your_secret_key>
R2_BUCKET_NAME=notiguard-files
```

#### Streamlit 실행 커맨드 (Procfile)
```bash
release: python init_railway_db.py
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## 📝 개발 로드맵 (Development Roadmap)

### 현재 버전 (Current Version)
v1.0 MVP ✅

---

### ✅ 완료된 기능 (Completed Features)

#### 🔐 인증 / 접근 제어
- ✅ accounts 기반 로그인 시스템  
  - ADMIN / EMPLOYEE 역할 분리  
  - 비밀번호 해시 검증 (verify_password)
- ✅ 권한 기반 페이지 접근 제어  
  - 로그인 상태 및 role 검증 후 `st.switch_page` 처리
- ✅ 앱 엔트리포인트 강제 로그인 구조  
  - `app.py` → 항상 로그인 페이지로 시작

#### 🧑‍💼 관리자 기능 (Admin)
- ✅ 공지사항 CRUD  
  - 일반공지 / 중요공지 등록  
  - 공지 리스트 조회 및 상세 조회
- ✅ 중요공지 팝업 생성  
  - 공지 작성 후 팝업 생성  
  - 본부 / 팀 단위 대상 지정
- ✅ 첨부파일 업로드  
  - 이미지/파일 업로드  
  - 디스크 저장 (`uploads/`)  
  - DB 메타데이터 관리 (`notice_files`)
- ✅ 첨부 이미지 자동 연계  
  - 중요공지 팝업 시 첫 번째 이미지 자동 노출

#### 👩‍💻 직원 기능 (Employee)
- ✅ 중요공지 팝업 자동 수신  
  - 홈 화면 진입 시  
  - 5초 주기 polling 기반 조회  
  - 미응답 팝업만 노출
- ✅ 팝업 처리 플로우 구현  
  - 1️⃣ 확인함 (2차 확인 포함)  
  - 2️⃣ 나중에 확인 (잔여 횟수 차감)  
  - 3️⃣ 요약 보기  
  - 4️⃣ 챗봇으로 바로가기
- ✅ 팝업 중복 방지 로직  
  - `popup_logs` 기반 응답 여부 체크  
  - 동일 팝업 재노출 방지
- ✅ 팝업 처리 로그 기록  
  - 확인 / 미확인 / 챗봇 이동 로그 저장

#### 🧾 공지 요약 기능
- ✅ POTENS.ai API 연동  
  - 공지 내용을 기반으로 요약 생성
- ✅ 요약 프롬프트 규칙 설계  
  - 5줄 이내 핵심 요약  
  - 일정 / 대상 / 필수 행동 분리  
  - 불필요한 연락처 정보 제거
- ✅ 요약 모달 단독 호출 구조  
  - Streamlit dialog 중첩 제한 회피  
  - state 기반 트리거 방식
- ✅ 요약 결과 캐싱  
  - 동일 팝업 재요약 방지

#### 🖼️ UI / UX (팝업 중심)
- ✅ Streamlit `st.dialog` 기반 팝업 UI
- ✅ JS + CSS 주입을 통한 팝업 스타일 강제 제어  
  - 팝업 크기, 스크롤 영역, 버튼 레이아웃 고정
- ✅ 본문 스크롤 분리 구조  
  - 제목/버튼 고정 + 본문만 스크롤
- ✅ 이미지 + 텍스트 혼합 렌더링

#### 🔗 챗봇 연계 기능
- ✅ 팝업 내 ‘챗봇으로 바로가기’ 버튼  
  - 새 탭으로 챗봇 서비스 열기  
  - 이동 로그 기록
- ✅ 로그인 후 모든 페이지에서 접근 가능한 챗봇 진입  
  - 우측 하단 플로팅 챗봇 위젯 제공  
  - 클릭 시 외부 챗봇 서비스로 즉시 이동

#### 🗄️ 데이터베이스
- ✅ PostgreSQL / SQLite 이중 지원
  - Railway (프로덕션): PostgreSQL
  - Local (개발): SQLite
- ✅ 공지 / 팝업 / 직원 / 계정 / 로그 / 첨부파일 / 챗봇로그 스키마 (7개 테이블)
- ✅ PostgreSQL 마이그레이션 완료
  - SQLite → PostgreSQL 데이터 이전 (18개 공지, 12개 파일)
  - 쿼리 플레이스홀더 변환 (`?` → `%s`)
- ✅ 첨부파일 메타 + 실제 파일 분리 관리
- ✅ 조회수 증가 제어 로직 (중복 방지)

#### 📁 파일 스토리지
- ✅ Cloudflare R2 연동 완료
- ✅ 파일 업로드/다운로드 자동화
- ✅ R2 Public URL 생성
- ✅ 로컬 백업 (개발 환경)
- ✅ 기존 파일 R2 마이그레이션 완료 (12개)

#### 🤖 AI 챗봇 통합 ✨
- ✅ POTENS.ai API 연동 완료
- ✅ 공지사항 기반 질의응답
- ✅ 응답 타입 분류 (NORMAL/MISSING/IRRELEVANT)
- ✅ 플로팅 위젯 UI (우측 하단)
- ✅ 챗봇 모달 다이얼로그
- ✅ 독립 챗봇 페이지
- ✅ 채팅 로그 저장
- ✅ 참조 공지 추출 및 표시
- ✅ 채팅 세션 관리 (자동 요약)
- ✅ 탭 기반 대화 기록 UI (최근 20개)
- ✅ 참조 공지 제목 표시 (버튼에 제목 포함)
- ✅ PostgreSQL 프로덕션 호환성 확보
- ✅ 시스템 프롬프트 개선 (UX 향상)

---

### 📌 향후 계획 (Future Plans) – 병합/연동 고려 사항 (검토본)

#### 1. 데이터베이스 통합 (DB Integration)
현재 노티가드 챗봇 서비스와 팝업 서비스는 서로 다른 데이터베이스 구조를 사용하고 있다.  
노티가드 서비스는 임의의 더미 공지 데이터를 고정한 상태로 동작하고 있으며,  
팝업 서비스는 관리자가 게시글을 직접 작성하면서 테스트하는 구조로 운영 중이다.

이로 인해 공지(notices), 로그, 사용자 테이블 구조가 서로 달라  
공지 데이터의 일관성과 정합성 유지가 어려운 상황이다.  
향후에는 두 서비스가 참조하는 공지, 로그, 사용자 데이터를  
하나의 통합 DB 구조로 정리하는 작업이 필요하다.

#### 2. 인증 및 계정 체계 통합 (Authentication Integration)
현재 두 서비스는 각각 독립적인 로그인 방식으로 동작하고 있다.  
향후에는 팝업을 관리하는 그룹웨어 페이지에서 한 번 로그인하면,  
동일한 인증 정보를 기반으로  
우측 하단에 위치한 노티가드(챗봇) 위젯에도 자동으로 접근할 수 있도록 통합할 필요가 있다.

또한 관리자 / 직원 권한에 따라  
각각 다른 챗봇 환경 또는 기능 범위로 접근 가능하도록  
권한 기반 인증 구조를 설계해야 한다.

#### 3. 첨부파일 처리 및 배포 환경 통합 (File Handling & Deployment)
현재 팝업 서비스에서는 공지 작성 시  
텍스트뿐만 아니라 이미지 파일 업로드 및 팝업 발송이 가능하도록 구현되어 있다.  
그러나 노티가드 서비스의 기존 DB 구조에는  
이미지(첨부파일)를 저장하기 위한 컬럼이 존재하지 않는다.

따라서 DB 통합 시,  
공지 데이터와 함께 이미지 메타데이터를 저장할 수 있는 구조 설계가 필요하다.

또한 팝업 서비스는 현재  
로컬 `uploads/` 경로에 파일을 저장하는 방식이므로,  
Railway 등 클라우드 환경에서 재배포 시  
파일 유실 또는 경로 오류가 발생할 수 있는 위험이 있다.  
이에 따라 배포 환경을 고려한  
공통 파일 저장 전략에 대한 검토가 필요하다.

---

## 🐛 문제 해결 (Troubleshooting)

### 요약 기능 오류
- `POTENS_API_KEY` 미설정 시 RuntimeError 발생  
→ `.env` 또는 배포 환경변수 확인 필요

### 첨부 이미지가 팝업에 안 보임
- 첨부는 `uploads/`에 저장되며 DB에는 file_path로 기록됩니다.
- 파일이 실제로 존재하는지 확인하세요.

### 팝업이 중복으로 열리거나 dialog 오류 발생
- Streamlit은 dialog 중첩이 제한되므로,
  요약 dialog는 **state로 트리거 후 dialog 밖에서 단독 호출** 구조로 구성되어 있습니다.

---

## 📚 개발 문서 (Documentation)

상세한 기술 문서는 `docs/` 폴더를 참조하세요.

### 주요 문서
- **`docs/DEPLOYMENT_COMPLETE.md`** - 최종 배포 완료 문서 ✅
- **`docs/CLAUDE.md`** - 로컬 개발 환경 설정 가이드
- **`docs/RAILWAY_ENV_SETUP.md`** - Railway 환경변수 설정 가이드
- **`docs/README_2026-01-03.md`** - 전체 기능 개발 상세 문서
- **`docs/CHANGELOG_2026-01-04.md`** - 챗봇 시스템 개선 및 버그 수정 상세 문서 ✨

### 기능별 문서
- `docs/CHATBOT_MODAL_IMPLEMENTATION.md` - 챗봇 모달 구현
- `docs/CRUD_IMPLEMENTATION.md` - 게시판 CRUD 구현
- `docs/R2_STORAGE_SETUP.md` - Cloudflare R2 설정

### 배포 관련
- `docs/RAILWAY_DEPLOY_GUIDE.md` - Railway 배포 가이드
- `docs/FINAL_DEPLOYMENT_SUMMARY.md` - 배포 요약

### 문제 해결
- `docs/TROUBLESHOOTING.md` - 트러블슈팅 가이드
- `docs/BUGFIX_ENV_LOADING.md` - 환경변수 버그 수정

> ⚠️ **주의**: `docs/` 폴더는 민감한 API 키와 환경변수 정보를 포함하므로 Git에서 제외됩니다.

---

## 👥 Contributors
- **개발 (Development)**: 효성전기 프로젝트 팀
- **기획 (Planning)**: 효성전기 IT팀

---

## 📄 라이선스 (License)
이 프로젝트는 내부 MVP 프로젝트입니다.
This project is an internal MVP project.

---

**Version**: v1.1 (Chatbot Enhancement)
**Last Updated**: 2026-01-04
**Deployment**: Railway ✅ 
