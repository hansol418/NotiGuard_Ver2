"""
이메일 발송 유틸리티
SMTP를 통한 이메일 전송 기능
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD


def send_email(to_email: str, subject: str, content: str) -> bool:
    """
    이메일 발송

    Args:
        to_email: 수신자 이메일
        subject: 제목
        content: 본문 내용

    Returns:
        bool: 성공 여부
    """
    # SMTP 설정 확인
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("⚠️ SMTP 설정 누락: 이메일 전송을 건너뜁니다.")
        print(f"   수신자: {to_email}")
        print(f"   제목: {subject}")
        print(f"   내용 미리보기: {content[:100]}...")
        return False

    try:
        # 이메일 메시지 구성
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(content, 'plain', 'utf-8'))

        # SMTP 서버 연결 및 발송
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # 보안 연결
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✅ 이메일 발송 성공: {to_email}")
        return True

    except Exception as e:
        print(f"❌ 이메일 전송 실패: {str(e)}")
        return False
