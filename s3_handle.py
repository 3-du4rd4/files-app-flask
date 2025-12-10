import boto3
from dotenv import load_dotenv
import sys
import os

load_dotenv()

BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_S3_REGION = os.getenv('AWS_DEFAULT_REGION')
BUCKET_PATH = os.getenv('S3_BUCKET_PATH')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

def load_s3(access_key, secret_key):
    try:
        if access_key is None or secret_key is None:
            raise ValueError("Chaves de acesso AWS inválidas.")
        
        s3 = boto3.client(
            's3',
            region_name=AWS_S3_REGION,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        print("Conexão com S3 estabelecida com sucesso.")
        return s3
    except Exception as e:
        print(f"Erro ao conectar ao S3: {e}", file=sys.stderr)
        sys.exit(1)
    
