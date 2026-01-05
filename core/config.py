"""
효성전기 그룹웨어 설정
부서별 담당자 이메일 및 시스템 설정
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 부서 목록 (현재 시스템에서 사용 중인 부서)
DEPARTMENTS = [
    "경영관리본부",
    "연구개발본부",
    "생산본부",
    "영업본부"
]

# 팀 목록 (더미 데이터 기준)
TEAMS = [
    "재경팀",
    "연구1팀",
    "연구2팀",
    "생산팀",
    "품질팀",
    "영업1팀",
    "영업2팀"
]

# 부서별 담당자 이메일 (실제 운영시 수정 필요)
DEPARTMENT_EMAILS = {
    "경영관리본부": "management@hyosung.com",
    "재경팀": "finance@hyosung.com",
    "연구개발본부": "rnd@hyosung.com",
    "연구1팀": "rnd1@hyosung.com",
    "연구2팀": "rnd2@hyosung.com",
    "생산본부": "production@hyosung.com",
    "생산팀": "prod_team@hyosung.com",
    "품질팀": "quality@hyosung.com",
    "영업본부": "sales@hyosung.com",
    "영업1팀": "sales1@hyosung.com",
    "영업2팀": "sales2@hyosung.com",
}

# 이메일 설정
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@hyosung.com")
