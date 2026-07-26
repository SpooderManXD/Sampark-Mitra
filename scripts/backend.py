"""
Sampark Mitra - Backend services & data

Domain: STT/TTS/LLM client wrappers, geocoding, language data, and the
small pure-python helpers (parse_tags, session-state factory) used by
the rest of the app. No Gradio UI code lives here.
"""

import os
import base64
import tempfile

from geopy.geocoders import Nominatim
from sarvamai import SarvamAI

# ---------------------------------------------------------------------------
# BACKEND IMPORTS
# ---------------------------------------------------------------------------
try:
    from gemma_inference import ask_gemma
except ImportError:
    print("Warning: gemma_inference.py not found. Using mock.")
    def ask_gemma(msg, image_path=None, session_id="default"):
        return "[TRIAGE_COMPLETE] System offline. Please seek nearest medical aid."

try:
    from sarvam_STT import transcribe as _transcribe_raw

    def transcribe(fp):
        """Wrapper that normalises the return value and surfaces real errors."""
        try:
            result = _transcribe_raw(fp)
        except Exception as exc:
            print(f"[STT] Exception from sarvam_STT.transcribe: {exc}")
            return None, None

        # Handle different return shapes gracefully
        if result is None:
            print("[STT] transcribe() returned None")
            return None, None

        if isinstance(result, (list, tuple)):
            transcript = result[0] if len(result) > 0 else None
            lang       = result[1] if len(result) > 1 else None
        elif isinstance(result, dict):
            transcript = result.get("transcript") or result.get("text") or result.get("result")
            lang       = result.get("language_code") or result.get("lang")
        else:
            transcript = str(result).strip() if result else None
            lang       = None

        if not transcript or not str(transcript).strip():
            print(f"[STT] Empty transcript received. Raw result was: {result!r}")
            return None, None

        print(f"[STT] transcript={transcript!r}  lang={lang!r}")
        return str(transcript).strip(), lang

except ImportError:
    print("Warning: sarvam_STT.py not found. Using mock.")
    def transcribe(fp):
        return "Mock transcript for testing", "hi-IN"

# ---------------------------------------------------------------------------
# CLIENTS & GLOBALS
# ---------------------------------------------------------------------------
sarvam_key    = os.environ.get("SARVAM_API_KEY")
sarvam_client = SarvamAI(api_subscription_key=sarvam_key) if sarvam_key else None
geolocator    = Nominatim(user_agent="sampark_mitra_app")

LANGUAGES = [
    {
        "word": "शुरू करें",     "lang": "Hindi",    "code": "hi-IN",
        "back": "वापस जाएं",    "press": "बात करने के लिए दबाएं", "upload": "फोटो भेजें",
        "ready": "स्वास्थ्य ट्राइएज के लिए तैयार",
        "recording": "रिकॉर्डिंग हो रही है... रोकने के लिए दबाएं", "processing": "प्रोसेस हो रहा है...",
        "top": "15%", "left": "12%", "delay": "0s",   "rot": "-4deg"
    },
    {
        "word": "தொடங்கு",       "lang": "Tamil",    "code": "ta-IN",
        "back": "முகப்பு",      "press": "பேச அழுத்தவும்",        "upload": "படம் அனுப்பவும்",
        "ready": "சுகாதார த்ரியேஜுக்கு தயார்",
        "recording": "பதிவு செய்யப்படுகிறது... நிறுத்த அழுத்தவும்", "processing": "செயலாக்கம் நடைபெறுகிறது...",
        "top": "22%", "left": "75%", "delay": "0.5s", "rot": "5deg"
    },
    {
        "word": "ప్రారంభించు",    "lang": "Telugu",   "code": "te-IN",
        "back": "హోమ్",         "press": "మాట్లాడటానికి నొక్కండి", "upload": "ఫోటో పంపండి",
        "ready": "ఆరోగ్య ట్రయాజ్ కోసం సిద్ధంగా ఉంది",
        "recording": "రికార్డింగ్ జరుగుతోంది... ఆపడానికి నొక్కండి", "processing": "ప్రాసెస్ అవుతోంది...",
        "top": "35%", "left": "8%",  "delay": "1.2s", "rot": "-3deg"
    },
    {
        "word": "ಪ್ರಾರಂಭಿಸಿ",    "lang": "Kannada",  "code": "kn-IN",
        "back": "ಮುಖಪುಟ",       "press": "ಮಾತನಾಡಲು ಒತ್ತಿರಿ",       "upload": "ಚಿತ್ರ ಕಳುಹಿಸಿ",
        "ready": "ಆರೋಗ್ಯ ಟ್ರಯಾಜ್‌ಗೆ ಸಿದ್ಧವಾಗಿದೆ",
        "recording": "ರೆಕಾರ್ಡಿಂಗ್ ಆಗುತ್ತಿದೆ... ನಿಲ್ಲಿಸಲು ಒತ್ತಿರಿ", "processing": "ಪ್ರಕ್ರಿಯೆಗೊಳ್ಳುತ್ತಿದೆ...",
        "top": "70%", "left": "15%", "delay": "0.8s", "rot": "6deg"
    },
    {
        "word": "শুরু করুন",     "lang": "Bengali",  "code": "bn-IN",
        "back": "হোমে ফিরুন",   "press": "কথা বলতে চাপুন",       "upload": "ছবি পাঠান",
        "ready": "স্বাস্থ্য ট্রাইয়েজের জন্য প্রস্তুত",
        "recording": "রেকর্ডিং হচ্ছে... থামাতে চাপুন", "processing": "প্রক্রিয়াকরণ হচ্ছে...",
        "top": "18%", "left": "45%", "delay": "1.5s", "rot": "-2deg"
    },
    {
        "word": "સ્ટાર્ટ કરો",   "lang": "Gujarati", "code": "gu-IN",
        "back": "પાછા જાઓ",     "press": "બોલવા માટે દબાવો",      "upload": "ફોટો મોકલો",
        "ready": "આરોગ્ય ટ્રાઇએજ માટે તૈયાર",
        "recording": "રેકોર્ડિંગ થઈ રહ્યું છે... રોકવા માટે દબાવો", "processing": "પ્રક્રિયા થઈ રહી છે...",
        "top": "75%", "left": "78%", "delay": "0.3s", "rot": "-5deg"
    },
    {
        "word": "सुरू करा",      "lang": "Marathi",  "code": "mr-IN",
        "back": "मुख्यपृष्ठ",   "press": "बोलण्यासाठी दाबा",      "upload": "फोटो पाठवा",
        "ready": "आरोग्य ट्रायेजसाठी तयार",
        "recording": "रेकॉर्डिंग सुरू आहे... थांबवण्यासाठी दाबा", "processing": "प्रक्रिया सुरू आहे...",
        "top": "62%", "left": "48%", "delay": "1.0s", "rot": "4deg"
    },
    {
        "word": "ਸ਼ੁਰੂ ਕਰੋ",    "lang": "Punjabi",  "code": "pa-IN",
        "back": "ਵਾਪਸ ਜਾਓ",    "press": "ਗੱਲ ਕਰਨ ਲਈ ਦਬਾਓ",      "upload": "ਫੋਟੋ ਭੇਜੋ",
        "ready": "ਸਿਹਤ ਟ੍ਰਾਇਏਜ ਲਈ ਤਿਆਰ",
        "recording": "ਰਿਕਾਰਡਿੰਗ ਹੋ ਰਹੀ ਹੈ... ਰੋਕਣ ਲਈ ਦਬਾਓ", "processing": "ਪ੍ਰੋਸੈਸਿੰਗ ਹੋ ਰਹੀ ਹੈ...",
        "top": "40%", "left": "82%", "delay": "1.7s", "rot": "-6deg"
    },
    {
        "word": "ଆରମ୍ଭ କରନ୍ତୁ", "lang": "Odia",     "code": "od-IN",
        "back": "ମୂଳପୃଷ୍ଠା",   "press": "କଥା ହେବାକୁ ଦବାନ୍ତୁ",     "upload": "ଫଟୋ ପଠାନ୍ତୁ",
        "ready": "ସ୍ୱାସ୍ଥ୍ୟ ଟ୍ରାଏଜ ପାଇଁ ପ୍ରସ୍ତୁତ",
        "recording": "ରେକର୍ଡିଂ ହେଉଛି... ବନ୍ଦ କରିବାକୁ ଦବାନ୍ତୁ", "processing": "ପ୍ରକ୍ରିୟାକରଣ ହେଉଛି...",
        "top": "80%", "left": "35%", "delay": "0.6s", "rot": "3deg"
    },
    {
        "word": "শুরু কৰক",      "lang": "Assamese", "code": "as-IN",
        "back": "ঘূৰি যাওক",    "press": "কথা পাতিবলৈ টিপক",      "upload": "ছবি পঠিয়াওক",
        "ready": "স্বাস্থ্য ট্ৰাইয়েজৰ বাবে সাজু",
        "recording": "ৰেকৰ্ডিং হৈ আছে... বন্ধ কৰিবলৈ টিপক", "processing": "প্ৰক্ৰিয়াকৰণ চলি আছে...",
        "top": "50%", "left": "20%", "delay": "1.4s", "rot": "-4deg"
    },
    {
        "word": "Click to Start", "lang": "English", "code": "en-IN",
        "back": "Back Home",     "press": "Press to Talk",        "upload": "Upload Photo",
        "ready": "Ready for Health Triage",
        "recording": "Recording... tap to stop", "processing": "Processing...",
        "top": "82%", "left": "60%", "delay": "0.9s", "rot": "2deg"
    },
]

LANG_CODE_MAP       = {item["lang"]: item["code"]       for item in LANGUAGES}
LANG_PRESS_MAP      = {item["lang"]: item["press"]      for item in LANGUAGES}
LANG_BACK_MAP       = {item["lang"]: item["back"]       for item in LANGUAGES}
LANG_UPLOAD_MAP     = {item["lang"]: item["upload"]     for item in LANGUAGES}
LANG_READY_MAP      = {item["lang"]: item["ready"]      for item in LANGUAGES}
LANG_RECORDING_MAP  = {item["lang"]: item["recording"]  for item in LANGUAGES}
LANG_PROCESSING_MAP = {item["lang"]: item["processing"] for item in LANGUAGES}

# Per-browser-session state.
# threaded through each handler explicitly instead.
def default_session_state():
    return {
        "lang_code": "hi-IN",
        "back_label": "Back Home",
        "press_label": "Press to Talk",
        "upload_label": "Upload Photo",
        "ready_label": "Ready for Health Triage",
        "recording_label": "Recording... tap to stop",
        "processing_label": "Processing..."
    }

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def resolve_location(lat=None, lon=None):
    """
    Reverse geocodes coordinates to a readable location string.
    Returns None if no location coordinates were captured or if resolution fails.
    """
    if lat is None or lon is None:
        return None
    try:
        loc  = geolocator.reverse(f"{lat}, {lon}")
        if not loc or not loc.raw:
            return None
        addr = loc.raw.get("address", {})
        place = (addr.get("village") or addr.get("town") or
                 addr.get("city")    or addr.get("subdistrict"))
        state = addr.get("state", "")
        if place or state:
            return f"{place or 'Area'}, {state}".strip(", ")
        return None
    except Exception:
        return None


def generate_audio_file(text, lang_code="hi-IN"):
    """
    Produces a WAV file via Sarvam API client for gr.Audio autoplay in browser.
    """
    if not text:
        return None

    if sarvam_client:
        try:
            response = sarvam_client.text_to_speech.convert(
                model="bulbul:v3",
                text=text,
                target_language_code=lang_code or "hi-IN",
                speaker="shubh"
            )
            if hasattr(response, "audios") and response.audios:
                raw  = base64.b64decode(response.audios[0])
                tmp  = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                tmp.write(raw)
                tmp.close()
                return tmp.name
        except Exception as e:
            print(f"[TTS] API client error: {e}")

    return None


def parse_tags(reply):
    tag, text = "NORMAL", reply
    for t in ["[REQUEST IMAGE]", "[REQUEST_IMAGE]", "[EMERGENCY]", "[TRIAGE COMPLETE]", "[TRIAGE_COMPLETE]"]:
        if t in reply:
            tag  = t.replace("_", " ")
            text = reply.replace(t, "").strip()
            break
    return tag, text

