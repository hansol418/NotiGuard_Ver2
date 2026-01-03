# Railway 환경변수 설정 가이드

## 필수 환경변수 목록

Railway 대시보드 또는 CLI를 통해 다음 환경변수를 설정해야 합니다.

### 1. 데이터베이스 (자동 설정)
```bash
DATABASE_URL=postgresql://...
```
- **설명**: PostgreSQL 데이터베이스 연결 URL
- **설정 방법**: Railway에서 PostgreSQL 서비스 추가 시 자동으로 설정됨
- **필수**: ✅ Yes

---

### 2. AI 챗봇 (POTENS API)
```bash
POTENS_API_KEY=Q1QJ6jIOTp0369I9PXCFa3GxMyzY4hHh
POTENS_API_URL=https://api.potens.ai/v1/chat/completions
RESPONSE_TIMEOUT=30
```
- **설명**: POTENS AI 챗봇 API 인증 및 설정
- **필수**: ✅ Yes (챗봇 기능 사용 시)
- **기본값**:
  - `POTENS_API_URL`: https://api.potens.ai/v1/chat/completions
  - `RESPONSE_TIMEOUT`: 30

---

### 3. Cloudflare R2 스토리지
```bash
R2_ACCOUNT_ID=0dc39b053d6ec32088191ddbabcd40be
R2_ACCESS_KEY_ID=1bf722054c3ed6018841ca3128593003
R2_SECRET_ACCESS_KEY=f18ff1a1e342e2b979c6d4ebd80fa5b25a0f2ab22565613387e39ed8bb332098
R2_BUCKET_NAME=notiguard-files
R2_PUBLIC_URL=
```
- **설명**: 첨부파일 저장용 Cloudflare R2 Object Storage
- **필수**: ✅ Yes (첨부파일 업로드 기능 사용 시)
- **R2_PUBLIC_URL**: 선택사항 (커스텀 도메인이 있는 경우)

---

## 설정 방법

### 방법 1: Railway CLI (권장)

```bash
# 1. Railway 프로젝트 링크
railway link

# 2. 환경변수 설정
# 데이터베이스 (PostgreSQL 서비스 추가 시 자동 설정)

# AI 챗봇
railway variables set POTENS_API_KEY=Q1QJ6jIOTp0369I9PXCFa3GxMyzY4hHh
railway variables set POTENS_API_URL=https://api.potens.ai/v1/chat/completions
railway variables set RESPONSE_TIMEOUT=30

# Cloudflare R2
railway variables set R2_ACCOUNT_ID=0dc39b053d6ec32088191ddbabcd40be
railway variables set R2_ACCESS_KEY_ID=1bf722054c3ed6018841ca3128593003
railway variables set R2_SECRET_ACCESS_KEY=f18ff1a1e342e2b979c6d4ebd80fa5b25a0f2ab22565613387e39ed8bb332098
railway variables set R2_BUCKET_NAME=notiguard-files
railway variables set R2_PUBLIC_URL=

# 3. 변수 확인
railway variables

# 4. 배포
railway up
```

---

### 방법 2: Railway 웹 대시보드

1. **Railway 대시보드 접속**
   - https://railway.app/dashboard

2. **프로젝트 선택**
   - NotiGuard 프로젝트 클릭

3. **서비스 선택**
   - Streamlit 앱 서비스 클릭

4. **Variables 탭 클릭**
   - 상단 메뉴에서 "Variables" 클릭

5. **환경변수 추가**
   - "New Variable" 버튼 클릭
   - 각 변수를 아래와 같이 추가:

   ```
   변수명: POTENS_API_KEY
   값: Q1QJ6jIOTp0369I9PXCFa3GxMyzY4hHh

   변수명: POTENS_API_URL
   값: https://api.potens.ai/v1/chat/completions

   변수명: RESPONSE_TIMEOUT
   값: 30

   변수명: R2_ACCOUNT_ID
   값: 0dc39b053d6ec32088191ddbabcd40be

   변수명: R2_ACCESS_KEY_ID
   값: 1bf722054c3ed6018841ca3128593003

   변수명: R2_SECRET_ACCESS_KEY
   값: f18ff1a1e342e2b979c6d4ebd80fa5b25a0f2ab22565613387e39ed8bb332098

   변수명: R2_BUCKET_NAME
   값: notiguard-files

   변수명: R2_PUBLIC_URL
   값: (비워둠 또는 커스텀 도메인)
   ```

6. **저장 및 재배포**
   - 변수 저장 시 자동으로 재배포됨

---

## PostgreSQL 데이터베이스 추가

Railway에 PostgreSQL 서비스가 없는 경우:

### CLI 방법:
```bash
railway add --database postgres
```

### 웹 대시보드 방법:
1. 프로젝트 페이지에서 "New" 클릭
2. "Database" 선택
3. "PostgreSQL" 선택
4. 자동으로 `DATABASE_URL` 환경변수 생성됨

---

## 데이터베이스 초기화

환경변수 설정 후 데이터베이스 테이블 생성:

```bash
# Railway 쉘 접속
railway run python init_railway_db.py
```

또는 배포 후 자동 실행 (Procfile에 설정됨):
```
release: python init_railway_db.py
web: streamlit run app.py --server.port $PORT
```

---

## 환경변수 확인

### CLI:
```bash
# 모든 변수 확인
railway variables

# 특정 변수 확인
railway variables get POTENS_API_KEY
```

### 웹 대시보드:
- 프로젝트 > 서비스 > Variables 탭

---

## 보안 주의사항

⚠️ **중요**: 환경변수에는 민감한 정보가 포함되어 있습니다.

- ✅ `.env` 파일은 `.gitignore`에 추가됨 (Git에 업로드되지 않음)
- ✅ Railway 환경변수는 암호화되어 저장됨
- ❌ API 키를 코드에 직접 하드코딩하지 마세요
- ❌ 환경변수를 공개 저장소에 커밋하지 마세요

---

## 트러블슈팅

### 문제 1: "Database connection failed"
**해결**: `DATABASE_URL` 환경변수가 설정되어 있는지 확인
```bash
railway variables get DATABASE_URL
```

### 문제 2: "챗봇 응답이 없음"
**해결**: `POTENS_API_KEY`가 올바른지 확인
```bash
railway variables get POTENS_API_KEY
```

### 문제 3: "첨부파일 업로드 실패"
**해결**: R2 환경변수가 모두 설정되어 있는지 확인
```bash
railway variables | grep R2_
```

### 문제 4: "환경변수 변경이 반영되지 않음"
**해결**: 변수 변경 후 수동으로 재배포
```bash
railway up --detach
```

---

## 배포 체크리스트

배포 전 확인사항:

- [ ] PostgreSQL 서비스 추가됨
- [ ] `DATABASE_URL` 자동 설정됨
- [ ] `POTENS_API_KEY` 설정됨
- [ ] `POTENS_API_URL` 설정됨
- [ ] `RESPONSE_TIMEOUT` 설정됨
- [ ] `R2_ACCOUNT_ID` 설정됨
- [ ] `R2_ACCESS_KEY_ID` 설정됨
- [ ] `R2_SECRET_ACCESS_KEY` 설정됨
- [ ] `R2_BUCKET_NAME` 설정됨
- [ ] `init_railway_db.py` 실행됨 (테이블 생성)
- [ ] 앱이 정상적으로 실행됨

---

## 참고 문서

- Railway 환경변수: https://docs.railway.app/develop/variables
- Railway PostgreSQL: https://docs.railway.app/databases/postgresql
- Cloudflare R2: https://developers.cloudflare.com/r2/

---

*마지막 업데이트: 2026-01-03*
