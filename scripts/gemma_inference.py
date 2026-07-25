import os
import mimetypes
from google import genai
from google.genai import types

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=30_000),
)

MODEL = "gemma-4-26b-a4b-it"

SYSTEM_PROMPT = """
You are Rural Health Triage AI.

You ONLY perform medical triage.
You NEVER diagnose diseases.

Understand:
- All Indian languages
- Regional dialects
- Mixed languages
- Speech transcription mistakes

Rules:
1. Ask ONLY ONE follow-up question at a time.
2. If a visible symptom is mentioned (rash, swelling, burn, wound, injury, eye problem, mouth problem, skin disease, etc.), immediately reply with:

[REQUEST IMAGE]

followed by a short explanation asking for a clear image.

3. Once enough information has been collected, begin your reply with ONE of these tags:

[TRIAGE COMPLETE]
or
[EMERGENCY]

4. Never use any other tags.

5. Keep replies under 80 words.

6. Reply in the same language as the user.

7. Must complete triage in 10 questions.

8. AT THE END OF TRIAGE ([TRIAGE COMPLETE] or [EMERGENCY]):
   - Check if user location is provided in the prompt (e.g., [Location: <place>]).
   - IF LOCATION IS PROVIDED: Use the Google Search tool to find real nearby Primary Health Centers (PHCs), clinics, or hospitals in that location, and suggest 1-2 actual hospital/clinic names.
   - IF LOCATION IS "None" OR NOT PROVIDED: Politely ask the user to tell you their village, town, city, or district name so you can find the nearest clinic or hospital for them.
"""

history = []


def ask_gemma(user_message: str, image_path: str = None) -> str:
    """
    Sends user message (and optional image filepath) to Gemma model and returns reply.
    """
    user_parts = []

    # If an image is provided, read bytes and create a valid SDK Part object
    if image_path and os.path.exists(image_path):
        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(image_path, "rb") as f:
                img_bytes = f.read()

            image_part = types.Part.from_bytes(
                data=img_bytes,
                mime_type=mime_type
            )
            user_parts.append(image_part)
            print(f"[Gemma] Successfully attached image from path: {image_path}")
        except Exception as e:
            print(f"[Gemma] Error loading image: {e}")

    # Append text part
    user_parts.append({"text": user_message})

    history.append({
        "role": "user",
        "parts": user_parts
    })

    try:
        print("Sending request to Gemma API with Search Tool...")
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            )
        )
        reply = response.text
    except Exception as e:
        print(f"\nError during Gemma API call: {e}")
        history.pop()
        return "क्षमा करें, एक तकनीकी समस्या आ गई है।"

    history.append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    return reply