import os
from PIL import Image
from google import genai
from google.genai import types

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=30_000)
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

[REQUEST_IMAGE]

followed by a short explanation asking for a clear image.

3. Once enough information has been collected, begin your reply with ONE of these tags:

[TRIAGE_COMPLETE]
or
[EMERGENCY]

4. Never use any other tags.

5. Keep replies under 80 words.

6. Reply in the same language as the user.

7. Must complete diagnose in 10 questions.

8. At the end Ask the location of the person and suggest the name of a nearby clinic or hospital they can go to, using google search TOOL.
"""

history = []


def ask_gemma(user_message: str, image_path: str = None) -> str:
    """
    Sends user message (and optional image filepath) to Gemma model and returns reply.
    """
    user_parts = []

    # Attach image if provided
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            user_parts.append(img)
            print(f"[Gemma] Attached image from path: {image_path}")
        except Exception as e:
            print(f"[Gemma] Error loading image: {e}")

    user_parts.append({"text": user_message})

    history.append({
        "role": "user",
        "parts": user_parts
    })

    try:
        print("Sending request to Gemma API...")
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
        # Rollback history so state remains clean
        history.pop()
        return "क्षमा करें, एक तकनीकी समस्या आ गई है।"

    history.append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    return reply