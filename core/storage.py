"""
Cloudflare R2 Storage Module
Railway 배포 시 파일 업로드를 R2에 저장
"""
import os
import boto3
from botocore.client import Config
from typing import Optional, BinaryIO
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Cloudflare R2 설정
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "notiguard-files")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # 커스텀 도메인 또는 R2.dev URL

# Railway 환경 감지 (DATABASE_URL이 있으면 Railway 환경)
IS_RAILWAY = bool(os.getenv("DATABASE_URL"))

def get_r2_client():
    """Cloudflare R2 S3 호환 클라이언트 생성"""
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
        raise ValueError("R2 환경변수가 설정되지 않았습니다.")

    # R2 엔드포인트 구성
    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    return boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto'  # R2는 자동 리전
    )


def upload_file_to_r2(
    file_data: BinaryIO,
    filename: str,
    folder: str = "uploads",
    content_type: Optional[str] = None
) -> str:
    """
    파일을 Cloudflare R2에 업로드

    Args:
        file_data: 파일 데이터 (BytesIO 또는 file object)
        filename: 저장할 파일명
        folder: 폴더명 (S3 prefix)
        content_type: MIME 타입

    Returns:
        str: 업로드된 파일의 공개 URL
    """
    from urllib.parse import quote

    s3 = get_r2_client()

    # S3 키 생성 (폴더/파일명)
    s3_key = f"{folder}/{filename}"

    # 업로드 옵션
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type

    # R2에 업로드
    s3.upload_fileobj(
        file_data,
        R2_BUCKET_NAME,
        s3_key,
        ExtraArgs=extra_args
    )

    # 공개 URL 반환 (URL 인코딩 적용)
    # quote(s3_key, safe='/') - 슬래시는 인코딩하지 않음
    encoded_key = quote(s3_key, safe='/')

    if R2_PUBLIC_URL:
        # 커스텀 도메인이 있으면 사용
        return f"{R2_PUBLIC_URL}/{encoded_key}"
    else:
        # R2.dev 공개 URL
        return f"https://pub-{R2_ACCOUNT_ID}.r2.dev/{encoded_key}"


def download_file_from_r2(s3_key: str) -> bytes:
    """
    R2에서 파일 다운로드

    Args:
        s3_key: S3 키 (예: "uploads/file.pdf")

    Returns:
        bytes: 파일 데이터
    """
    s3 = get_r2_client()

    response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=s3_key)
    return response['Body'].read()


def delete_file_from_r2(s3_key: str) -> bool:
    """
    R2에서 파일 삭제

    Args:
        s3_key: S3 키

    Returns:
        bool: 성공 여부
    """
    try:
        s3 = get_r2_client()
        s3.delete_object(Bucket=R2_BUCKET_NAME, Key=s3_key)
        return True
    except Exception as e:
        print(f"R2 파일 삭제 실패: {e}")
        return False


def get_file_url(s3_key: str) -> str:
    """
    S3 키로부터 공개 URL 생성

    Args:
        s3_key: S3 키

    Returns:
        str: 공개 URL
    """
    from urllib.parse import quote

    # URL 인코딩 적용
    encoded_key = quote(s3_key, safe='/')

    if R2_PUBLIC_URL:
        return f"{R2_PUBLIC_URL}/{encoded_key}"
    else:
        return f"https://pub-{R2_ACCOUNT_ID}.r2.dev/{encoded_key}"


# ===== 로컬/Railway 자동 감지 저장 함수 =====

def save_file(
    file_data: BinaryIO,
    filename: str,
    folder: str = "uploads",
    content_type: Optional[str] = None
) -> str:
    """
    환경에 따라 자동으로 로컬 또는 R2에 저장

    Args:
        file_data: 파일 데이터
        filename: 파일명
        folder: 폴더명
        content_type: MIME 타입

    Returns:
        str: 파일 경로 또는 URL
    """
    if IS_RAILWAY:
        # Railway 환경 → R2에 저장
        return upload_file_to_r2(file_data, filename, folder, content_type)
    else:
        # 로컬 환경 → 디스크에 저장
        upload_dir = Path(folder)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_data.read())

        return str(file_path)


def get_file(file_path_or_url: str) -> bytes:
    """
    환경에 따라 자동으로 로컬 또는 R2에서 파일 읽기

    Args:
        file_path_or_url: 로컬 경로 또는 R2 URL

    Returns:
        bytes: 파일 데이터
    """
    if file_path_or_url.startswith("http"):
        # R2 공개 URL → HTTP로 직접 다운로드
        import requests

        try:
            response = requests.get(file_path_or_url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"HTTP 다운로드 실패, S3 API 시도: {e}")
            # HTTP 실패 시 S3 API로 다운로드 시도
            s3_key = "/".join(file_path_or_url.split("/")[-2:])  # "uploads/file.pdf"
            return download_file_from_r2(s3_key)
    else:
        # 로컬 파일
        with open(file_path_or_url, 'rb') as f:
            return f.read()
