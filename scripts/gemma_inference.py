import os
import re
import mimetypes
from google import genai
from google.genai import types

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=100_000),
)

MODEL = "gemma-4-26b-a4b-it"

# Grounding tool: lets Gemma itself issue a live Google Search when it needs
# real-world info (here: real nearby hospitals/clinics). No geopy, no Overpass,
# no code-side lookup — the model decides when to call it and what to search for.
_search_tool = types.Tool(google_search=types.GoogleSearch())

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
   - If the user's location was provided (e.g., [Location: <place>]), use the
     Google Search tool available to you to look up 2-3 real, currently-operating
     hospitals or clinics near that location, and list their names in your reply.
     Only use facility names the search tool actually returns — never invent one.
   - If location is "None" or not provided, politely ask the user to share their
     village, town, city, or district so the nearest facility can be found for them.
"""

# Session-scoped histories. Using a single module-level list (as before) means every
# concurrent user shares one conversation — this dict keeps each session isolated.
# can pass a session_id (e.g. from gr.State/browser session); if it doesn't,
# everything falls back to a single "default" session so existing calls still work.
_histories = {}


def _get_history(session_id: str):
    return _histories.setdefault(session_id, [])


def _extract_location(user_message: str):
    match = re.search(r"\[Location:\s*([^\]]+)\]", user_message)
    return match.group(1).strip() if match else None


def ask_gemma(user_message: str, image_path: str = None, session_id: str = "default") -> str:
    """
    Sends user message (and optional image filepath) to Gemma model and returns reply.
    `session_id` isolates conversation history per user/session; defaults to "default"
    so this stays a drop-in replacement if the caller doesn't pass one.

    Google Search grounding is enabled on every call so Gemma can look up real nearby
    hospitals/clinics itself once triage completes (per SYSTEM_PROMPT rule 8). Gemma
    decides on its own whether/when to actually call the tool, so ordinary triage
    turns aren't slowed down — only the final "triage complete" turn typically is.
    """
    history = _get_history(session_id)

    user_parts = []

    if image_path and os.path.exists(image_path):
        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(image_path, "rb") as f:
                img_bytes = f.read()

            image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            user_parts.append(image_part)
            print(f"[Gemma] Successfully attached image from path: {image_path}")
        except Exception as e:
            print(f"[Gemma] Error loading image: {e}")

    user_parts.append(types.Part.from_text(text=user_message))

    history.append(types.Content(role="user", parts=user_parts))

    try:
        print("Sending request to Gemma API...")
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                tools=[_search_tool],
            ),
        )
        reply = response.text
    except Exception as e:
        print(f"\nError during Gemma API call: {e}")
        history.pop()
        return "क्षमा करें, एक तकनीकी समस्या आ गई है।"

    # Optional: log what Gemma actually searched for / grounded on, useful for
    # debugging the "triage complete -> nearby facilities" turns.
    try:
        candidate = response.candidates[0]
        grounding = getattr(candidate, "grounding_metadata", None)
        if grounding and getattr(grounding, "grounding_chunks", None):
            sources = [
                chunk.web.title
                for chunk in grounding.grounding_chunks
                if getattr(chunk, "web", None)
            ]
            if sources:
                print(f"[Gemma] Grounded on: {', '.join(sources)}")
    except Exception:
        pass

    history.append(types.Content(role="model", parts=[types.Part.from_text(text=reply)]))

    return reply