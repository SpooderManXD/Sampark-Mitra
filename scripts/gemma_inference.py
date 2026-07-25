from sarvam_STT import transcribe
from sarvam_TTS import speech
from google import genai
from google.genai import types
import os

api_key = os.environ.get("GOOGLE_API_KEY")
client=genai.Client(api_key=api_key)


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
"""

history = []


def ask_gemma(user_message: str):

    history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    response = client.models.generate_content(
        model=MODEL,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        )
    )

    reply = response.text

    history.append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    return reply


def process_reply(reply: str, lang: str):
    """Processes Gemma's response tags and triggers speech output."""
    clean_text = reply

    if "[REQUEST_IMAGE]" in reply:
        print("\n📷 IMAGE REQUIRED")
        clean_text = reply.replace("[REQUEST_IMAGE]", "").strip()

    elif "[EMERGENCY]" in reply:
        print("\n🚨 EMERGENCY")
        clean_text = reply.replace("[EMERGENCY]", "").strip()

    elif "[TRIAGE_COMPLETE]" in reply:
        print("\n✅ TRIAGE COMPLETE")
        clean_text = reply.replace("[TRIAGE_COMPLETE]", "").strip()

    else:
        print("\n🤖 Assistant")

    print(clean_text)
    # Speak the output text
    speech(clean_text, lang)


def main():

    print("Health Assistant Started")

    while True:

        result = transcribe()
        text = result[0]
        lang = result[1]

        if not text:
            continue

        print("\nYou:", text)

        if text.lower() in ["exit", "quit", "stop"]:
            break

        reply = ask_gemma(text)

        process_reply(reply, lang)


if __name__ == "__main__":
    main()