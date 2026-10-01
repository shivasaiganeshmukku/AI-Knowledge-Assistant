import time

from google import genai
from google.genai import errors

from config import GEMINI_API_KEY


if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured")


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# Generate Response
# ============================================================

def generate_response(prompt):

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            return response.text

        except errors.ClientError as e:

            if e.code == 429:

                print(
                    f"Gemini API error: 429 RESOURCE_EXHAUSTED. {e}"
                )

                raise

            if e.code == 503:

                print(
                    f"Gemini API error: 503 UNAVAILABLE. {e}"
                )

                if attempt < 2:
                    time.sleep(5)
                    continue

                raise

            print(
                f"Gemini API client error: {e}"
            )

            raise

        except errors.ServerError as e:

            print(
                f"Gemini API server error: {e}"
            )

            if attempt < 2:
                time.sleep(5)
                continue

            raise

        except Exception as e:

            print(
                f"Unexpected Gemini error: {e}"
            )

            raise


# ============================================================
# Generate Embedding
# ============================================================

def generate_embedding(text):

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values