"""
Sampark Bhai - Rural Emergency Triage Hub UI (Dynamic Language Back Button)
Integrates:
  - Gemma AI Health Triage simulation / live fallback
  - Sarvam STT & TTS fallback handling
  - Interactive Floating Language Dashboard & Wavy Orb View
"""

import os
import json
import base64
import tempfile
import gradio as gr
from google import genai
from google.genai import types
from geopy.geocoders import Nominatim
from sarvamai import SarvamAI

# ---------------------------------------------------------------------------
# 1. SETUP CLIENTS
# ---------------------------------------------------------------------------
google_key = os.environ.get("GOOGLE_API_KEY")
sarvam_key = os.environ.get("SARVAM_API_KEY")

gemma_client = genai.Client(
    api_key=google_key,
    http_options=types.HttpOptions(timeout=30_000)
) if google_key else None

sarvam_client = SarvamAI(api_subscription_key=sarvam_key) if sarvam_key else None
geolocator = Nominatim(user_agent="sampark_bhai_app")

MODEL_NAME = "gemma-4-26b-a4b-it"

SYSTEM_PROMPT = """
You are Rural Health Triage AI.
You ONLY perform medical triage.
You NEVER diagnose diseases.
Understand all Indian languages, regional dialects, and mixed language inputs.
Keep replies under 80 words. Reply in the same language as the user.
"""

# ---------------------------------------------------------------------------
# 2. SUPPORTED LANGUAGES, POSITIONS & BACK BUTTON TRANSLATIONS
# ---------------------------------------------------------------------------
LANGUAGES = [
    {"word": "शुरू करें",     "lang": "Hindi",     "back": "वापस जाएं",      "top": "15%", "left": "12%", "delay": "0s",   "rot": "-4deg"},
    {"word": "தொடங்கு",       "lang": "Tamil",     "back": "முகப்பு",       "top": "22%", "left": "75%", "delay": "0.5s", "rot": "5deg"},
    {"word": "ప్రారంభించు",    "lang": "Telugu",    "back": "హోమ్",         "top": "35%", "left": "8%",  "delay": "1.2s", "rot": "-3deg"},
    {"word": "ప్రారంభిసి",    "lang": "Kannada",   "back": "ಮುಖಪುಟ",       "top": "70%", "left": "15%", "delay": "0.8s", "rot": "6deg"},
    {"word": "শুরু করুন",     "lang": "Bengali",   "back": "হোমে ফিরুন",    "top": "18%", "left": "45%", "delay": "1.5s", "rot": "-2deg"},
    {"word": "સ્ટાર્ટ કરો",   "lang": "Gujarati",  "back": "પાછા જાઓ",     "top": "75%", "left": "78%", "delay": "0.3s", "rot": "-5deg"},
    {"word": "सुरू करा",      "lang": "Marathi",   "back": "मुख्यपृष्ठ",    "top": "62%", "left": "48%", "delay": "1.0s", "rot": "4deg"},
    {"word": "ਸ਼ੁਰੂ ਕਰੋ",    "lang": "Punjabi",   "back": "ਵਾਪਸ ਜਾਓ",     "top": "40%", "left": "82%", "delay": "1.7s", "rot": "-6deg"},
    {"word": "ଆରମ୍ଭ କରନ୍ତୁ", "lang": "Odia",      "back": "ମୂଳପୃଷ୍ଠା",   "top": "80%", "left": "35%", "delay": "0.6s", "rot": "3deg"},
    {"word": "শুরু কৰক",      "lang": "Assamese",  "back": "ঘূৰি যাওক",    "top": "50%", "left": "20%", "delay": "1.4s", "rot": "-4deg"},
    {"word": "Click to Start", "lang": "English",  "back": "Back Home",     "top": "82%", "left": "60%", "delay": "0.9s", "rot": "2deg"},
]

session_history = []

# ---------------------------------------------------------------------------
# 3. CORE BACKEND PIPELINE (WITH FALLBACKS)
# ---------------------------------------------------------------------------
def resolve_location(lat=21.1938, lon=81.2849):
    """Converts coordinates to location string via GeoPy with fallback."""
    try:
        location = geolocator.reverse(f"{lat}, {lon}")
        address = location.raw.get('address', {})
        place = (
            address.get('village') or 
            address.get('town') or 
            address.get('city') or 
            address.get('subdistrict') or 
            "Local Area"
        )
        state = address.get('state', '')
        return f"{place}, {state}".strip(", ")
    except Exception:
        return "Local Clinic Area, Chhattisgarh (Offline Default)"


def ask_gemma_triage(user_message):
    """Executes Gemma triage, falling back to a safe mock response if keys are missing."""
    if not gemma_client:
        return {
            "tag": "[TRIAGE_COMPLETE]",
            "clean_text": "API Key not detected. Mock Triage Mode: Please keep the patient stable, clear airways, and proceed to the nearest community health center."
        }

    session_history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    try:
        response = gemma_client.models.generate_content(
            model=MODEL_NAME,
            contents=session_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            )
        )
        reply = response.text
        session_history.append({"role": "model", "parts": [{"text": reply}]})

        tag = "NORMAL"
        clean_text = reply

        if "[REQUEST_IMAGE]" in reply:
            tag = "[REQUEST_IMAGE]"
            clean_text = reply.replace("[REQUEST_IMAGE]", "").strip()
        elif "[EMERGENCY]" in reply:
            tag = "[EMERGENCY]"
            clean_text = reply.replace("[EMERGENCY]", "").strip()
        elif "[TRIAGE_COMPLETE]" in reply:
            tag = "[TRIAGE_COMPLETE]"
            clean_text = reply.replace("[TRIAGE_COMPLETE]", "").strip()

        return {
            "tag": tag,
            "clean_text": clean_text
        }

    except Exception as e:
        if session_history:
            session_history.pop()
        return {
            "tag": "ERROR",
            "clean_text": f"Gemma API error: {str(e)}. Proceed to nearest medical aid hub."
        }


def generate_sarvam_tts(text, lang_code="hi-IN"):
    """Generates audio file via Sarvam AI TTS, falling back gracefully if offline."""
    if not sarvam_client or not text:
        return None
    
    try:
        response = sarvam_client.text_to_speech.convert(
            model="bulbul:v3",
            text=text,
            target_language_code=lang_code if lang_code else "hi-IN",
            speaker="shubh"
        )
        if hasattr(response, "audios") and response.audios:
            raw_audio = base64.b64decode(response.audios[0])
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file.write(raw_audio)
            temp_file.close()
            return temp_file.name
    except Exception as e:
        print(f"TTS Fallback Warning: {e}")
    return None

# ---------------------------------------------------------------------------
# 4. HTML BUILDERS
# ---------------------------------------------------------------------------
def build_home_page():
    scattered_buttons = ""
    for item in LANGUAGES:
        # Pass both trigger action and the localized back button label to JS
        payload = f"{item['lang']}||{item['back']}"
        scattered_buttons += f"""
        <div class="scattered-tag" 
             style="top: {item['top']}; left: {item['left']}; animation-delay: {item['delay']}; --rot: {item['rot']};" 
             onclick="sendTrigger('{payload}')">
            <span class="word">{item['word']}</span>
            <small class="lang-label">{item['lang']}</small>
        </div>
        """

    return f"""
    <style>
        .home-container {{
            position: relative;
            min-height: 85vh;
            width: 100%;
            background: linear-gradient(135deg, #023047, #219ebc, #8ecae6, #028090, #00b4d8);
            background-size: 400% 400%;
            animation: waterFlowWave 15s ease infinite;
            border-radius: 20px;
            color: white;
            overflow: hidden;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        @keyframes waterFlowWave {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        .center-hero {{
            position: absolute;
            top: 48%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            z-index: 2;
            pointer-events: none;
        }}
        .home-title {{
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 0.2rem;
            background: linear-gradient(to right, #ffffff, #caf0f8, #90e0ef);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
            text-shadow: 0 4px 20px rgba(0, 119, 182, 0.4);
        }}
        .home-subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
            color: #e0f2fe;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        .scattered-tag {{
            position: absolute;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.35);
            padding: 12px 22px;
            border-radius: 30px;
            cursor: pointer;
            z-index: 5;
            display: flex;
            flex-direction: column;
            align-items: center;
            box-shadow: 0 8px 32px 0 rgba(0, 50, 80, 0.3);
            animation: floatWater 5s infinite ease-in-out;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform: rotate(var(--rot, 0deg));
        }}
        .scattered-tag:hover {{
            background: rgba(255, 255, 255, 0.35);
            border-color: #ffffff;
            box-shadow: 0 0 35px rgba(144, 224, 239, 0.8);
            transform: scale(1.15) translateY(-6px) rotate(var(--rot, 0deg)) !important;
        }}
        .scattered-tag .word {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
        }}
        .scattered-tag .lang-label {{
            font-size: 0.75rem;
            color: #e0f2fe;
            margin-top: 2px;
            font-weight: 500;
        }}
        @keyframes floatWater {{
            0%, 100% {{ transform: translateY(0px) rotate(var(--rot, 0deg)); }}
            50% {{ transform: translateY(-12px) rotate(var(--rot, 0deg)); }}
        }}
    </style>

    <div class="home-container">
        <div class="center-hero">
            <h1 class="home-title">Sampark Bhai</h1>
            <p class="home-subtitle">Tap any regional button to start emergency triage assistant</p>
        </div>

        {scattered_buttons}
    </div>
    """

def build_orb_page(back_label="Back Home"):
    return f"""
    <style>
        .orb-screen {{
            min-height: 85vh;
            background: linear-gradient(135deg, #023047, #219ebc, #8ecae6, #028090, #00b4d8);
            background-size: 400% 400%;
            animation: waterFlowWave 15s ease infinite;
            color: white;
            border-radius: 20px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            font-family: system-ui, -apple-system, sans-serif;
            position: relative;
            overflow: hidden;
        }}
        .orb-header {{
            width: 100%;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            z-index: 10;
        }}
        .orb-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: auto 0;
            z-index: 5;
        }}
        .wavy-orb {{
            width: 200px;
            height: 200px;
            background: radial-gradient(circle at 30% 30%, #38bdf8, #818cf8, #c084fc, #ec4899);
            box-shadow: 0 0 60px rgba(56, 189, 248, 0.8), 0 0 100px rgba(192, 132, 252, 0.5);
            animation: orbBreathe 3s ease-in-out infinite alternate, orbWave 8s linear infinite;
        }}
        @keyframes orbBreathe {{
            0% {{
                transform: scale(0.9);
                box-shadow: 0 0 40px rgba(56, 189, 248, 0.6), 0 0 80px rgba(192, 132, 252, 0.4);
            }}
            100% {{
                transform: scale(1.2);
                box-shadow: 0 0 100px rgba(56, 189, 248, 0.95), 0 0 160px rgba(192, 132, 252, 0.8);
            }}
        }}
        @keyframes orbWave {{
            0% {{ border-radius: 50% 50% 50% 50% / 50% 50% 50% 50%; }}
            25% {{ border-radius: 65% 35% 60% 40% / 40% 60% 35% 65%; }}
            50% {{ border-radius: 40% 60% 35% 65% / 60% 35% 65% 40%; }}
            75% {{ border-radius: 55% 45% 70% 30% / 30% 70% 45% 55%; }}
            100% {{ border-radius: 50% 50% 50% 50% / 50% 50% 50% 50%; }}
        }}
    </style>

    <div class="orb-screen">
        <div class="orb-header">
            <button onclick="sendTrigger('__HOME__')" style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 10px 22px; border-radius: 20px; cursor: pointer; backdrop-filter: blur(8px); font-weight: 600; font-size: 0.95rem;">{back_label}</button>
        </div>

        <div class="orb-container">
            <div class="wavy-orb"></div>
        </div>

        <div></div>
    </div>
    """

GLOBAL_JS = """
function sendTrigger(val) {
    const container = document.getElementById('router_input');
    const input = container ? (container.querySelector('textarea') || container.querySelector('input')) : null;
    if (input) {
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
        ) || Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        );
        if (nativeSetter && nativeSetter.set) {
            nativeSetter.set.call(input, val);
        } else {
            input.value = val;
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    const btn = document.querySelector('#hidden_trigger_btn button, #hidden_trigger_btn');
    if (btn) {
        btn.click();
    }
}
"""

# ---------------------------------------------------------------------------
# 5. ROUTER HANDLER
# ---------------------------------------------------------------------------
def handle_route(trigger):
    if trigger == "__HOME__":
        session_history.clear()
        return build_home_page(), None

    if "||" in trigger:
        parts = trigger.split("||")
        lang_name = parts[0]
        back_label = parts[1]
        
        location_str = resolve_location()
        data = ask_gemma_triage(f"New medical emergency report initiated in {lang_name} from location: {location_str}")
        audio_file = generate_sarvam_tts(data.get("clean_text", ""))
        return build_orb_page(back_label=back_label), audio_file

    return build_orb_page(), None

# ---------------------------------------------------------------------------
# 6. GRADIO LAYOUT
# ---------------------------------------------------------------------------
custom_css = """
footer {display: none !important;}
#router_input, #hidden_trigger_btn {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    opacity: 0 !important;
    pointer-events: none !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
}
"""

with gr.Blocks(title="Sampark Bhai", css=custom_css, js=GLOBAL_JS) as demo:
    
    router_input = gr.Textbox(elem_id="router_input", visible=True)
    hidden_trigger_btn = gr.Button(elem_id="hidden_trigger_btn", visible=True)
    
    display_page = gr.HTML(value=build_home_page())
    audio_output = gr.Audio(label="Output Voice", autoplay=True, visible=False)

    hidden_trigger_btn.click(
        fn=handle_route,
        inputs=[router_input],
        outputs=[display_page, audio_output]
    )

if __name__ == "__main__":
    demo.launch()