import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

BUCKET_NAME = os.getenv("AWS_S3_BUCKET")


def upload_video_to_s3(file_bytes: bytes, filename: str, content_type: str):
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f"vkyc_videos/{filename}",
        Body=file_bytes,
        ContentType=content_type
    )

    return f"s3://{BUCKET_NAME}/vkyc_videos/{filename}"
