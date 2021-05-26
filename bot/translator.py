import os
from google.cloud.translate import TranslationServiceAsyncClient

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getcwd() + f"/{os.getenv('GOOGLE_PROJECT_CREDS_FILENAME', '')}"

client = TranslationServiceAsyncClient()
parent = f"projects/{os.getenv('GOOGLE_PROJECT_API', '')}/locations/global"


async def translate(input_text: str):
    response = await client.translate_text(
        request={
            "parent": parent,
            "contents": [input_text],
            "mime_type": "text/plain",  # mime types: text/plain, text/html
            "target_language_code": "en-US",
        }
    )
    result = response.translations[0]
    if result.detected_language_code == "en":
        return None, None
    return result.translated_text, result.detected_language_code
