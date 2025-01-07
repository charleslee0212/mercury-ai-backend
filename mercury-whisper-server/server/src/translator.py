from mercury_json import MercuryTranslationRequestJSON
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
import logging
import json

logger = logging.getLogger(__name__)


# AWS Secrets Manager client
def get_secret(secret_name: str, region_name: str = "us-west-1"):
    aws_client = boto3.client("secretsmanager", region_name=region_name)
    try:
        response = aws_client.get_secret_value(
            SecretId=secret_name, VersionStage="AWSCURRENT"
        )
        secret = response["SecretString"]
        return secret
    except ClientError as e:
        logger.error(f"Access secret failed: {e}")


def mercury_translator(request: MercuryTranslationRequestJSON):
    # Retrieve OpenAI API key from Secrets Manager
    secret_name = "openai_api_token"
    secret = get_secret(secret_name)
    api_key = eval(secret).get("openai_api_token")

    openai_client = OpenAI(
        api_key=api_key,
    )

    # Generate translation with OpenAI
    completion = openai_client.chat.completions.create(
        model=request.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a translator that will translate incoming transcriptions to the requested languages. "
                    "You will ONLY respond with JSON. "
                    "Make any corrections necessary to improve the translation. "
                    'JSON format: {"translations":{"en":"Hello world!","ko":"안녕 세상!"}}'
                ),
            },
            {
                "role": "user",
                "content": ('{"transcription":"Hello World!","languages":["ko","es"]}'),
            },
            {
                "role": "assistant",
                "content": ('{"translations":{"ko":"안녕 세상!","es":"¡Hola Mundo!"}}'),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcription": request.transcription,
                        "languages": request.languages,
                    }
                ),
            },
        ],
    )

    return {"status": 200, "completion": completion.choices[0].message.content}
