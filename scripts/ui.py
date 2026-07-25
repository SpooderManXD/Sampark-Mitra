"""
Sampark Mitra - Rural Emergency Triage Hub UI

Pipeline:
  1. Home page: click language word
  2. Orb page: shows "press to talk" in chosen language
  3. User records via mic or uploads a photo if requested
  4. On stop/upload: transcribe_file() / image -> ask_gemma() -> generate_audio_file() -> playback
"""

import os
import base64
import tempfile
import gradio as gr
from geopy.geocoders import Nominatim
from sarvamai import SarvamAI

# ---------------------------------------------------------------------------
# BACKEND IMPORTS
# ---------------------------------------------------------------------------
try:
    from gemma_inference import ask_gemma
except ImportError:
    print("Warning: gemma_inference.py not found. Using mock.")
    def ask_gemma(msg, image_path=None):
        return "[TRIAGE_COMPLETE] System offline. Please seek nearest medical aid."

try:
    from sarvam_STT import transcribe
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
        "triage_ready": "स्वास्थ्य ट्राइएज के लिए तैयार",
        "top": "15%", "left": "12%", "delay": "0s",   "rot": "-4deg"
    },
    {
        "word": "தொடங்கு",       "lang": "Tamil",    "code": "ta-IN",
        "back": "முகப்பு",      "press": "பேச அழுத்தவும்",        "upload": "படம் அனுப்பவும்",
        "triage_ready": "சுகாதார சோதனைக்கு தயார்",
        "top": "22%", "left": "75%", "delay": "0.5s", "rot": "5deg"
    },
    {
        "word": "ప్రారంభించు",    "lang": "Telugu",   "code": "te-IN",
        "back": "హోమ్",         "press": "మాట్లాడటానికి నొక్కండి", "upload": "ఫోటో పంపండి",
        "triage_ready": "ఆరోగ్య ట్రయాజ్‌కు సిద్ధంగా ఉంది",
        "top": "35%", "left": "8%",  "delay": "1.2s", "rot": "-3deg"
    },
    {
        "word": "ಪ್ರಾರಂಭಿಸಿ",    "lang": "Kannada",  "code": "kn-IN",
        "back": "ಮುಖಪುಟ",       "press": "ಮಾತನಾಡಲು ಒತ್ತಿರಿ",       "upload": "ಚಿತ್ರ ಕಳುಹಿಸಿ",
        "triage_ready": "ಆರೋಗ್ಯ ತ್ರಿಯಾಜ್‌ಗೆ ಸಿದ್ಧ",
        "top": "70%", "left": "15%", "delay": "0.8s", "rot": "6deg"
    },
    {
        "word": "শুরু করুন",     "lang": "Bengali",  "code": "bn-IN",
        "back": "হোমে ফিরুন",   "press": "কথা বলতে চাপুন",       "upload": "ছবি পাঠান",
        "triage_ready": "স্বাস্থ্য ট্রাইয়াজের জন্য প্রস্তুত",
        "top": "18%", "left": "45%", "delay": "1.5s", "rot": "-2deg"
    },
    {
        "word": "સ્ટાર્ટ કરો",   "lang": "Gujarati", "code": "gu-IN",
        "back": "પાછા જાઓ",     "press": "બોલવા માટે દબાવો",      "upload": "ફોટો મોકલો",
        "triage_ready": "સ્વાસ્થ્ય ટ્રાઇએજ માટે તૈયાર",
        "top": "75%", "left": "78%", "delay": "0.3s", "rot": "-5deg"
    },
    {
        "word": "सुरू करा",      "lang": "Marathi",  "code": "mr-IN",
        "back": "मुख्यपृष्ठ",   "press": "बोलण्यासाठी दाबा",      "upload": "फोटो पाठवा",
        "triage_ready": "आरोग्य ट्रायेजसाठी तयार",
        "top": "62%", "left": "48%", "delay": "1.0s", "rot": "4deg"
    },
    {
        "word": "ਸ਼ੁਰੂ ਕਰੋ",    "lang": "Punjabi",  "code": "pa-IN",
        "back": "ਵਾਪਸ ਜਾਓ",    "press": "ਗੱਲ ਕਰਨ ਲਈ ਦਬਾਓ",      "upload": "ਫੋਟੋ ਭੇਜੋ",
        "triage_ready": "ਸਿਹਤ ਟ੍ਰਾਈਏਜ ਲਈ ਤਿਆਰ",
        "top": "40%", "left": "82%", "delay": "1.7s", "rot": "-6deg"
    },
    {
        "word": "ଆରମ୍ଭ କରନ୍ତୁ", "lang": "Odia",     "code": "od-IN",
        "back": "ମୂଳପୃଷ୍ଠା",   "press": "କଥା ହେବାକୁ ଦବାନ୍ତୁ",     "upload": "ଫଟୋ ପଠାନ୍ତୁ",
        "triage_ready": "ସ୍ୱାସ୍ଥ୍ୟ ଟ୍ରାଇଏଜ ପାଇଁ ପ୍ରସ୍ତୁତ",
        "top": "80%", "left": "35%", "delay": "0.6s", "rot": "3deg"
    },
    {
        "word": "শুরু কৰক",      "lang": "Assamese", "code": "as-IN",
        "back": "ঘূৰি যাওক",    "press": "কথা পাতিবলৈ টিপক",      "upload": "ছবি পঠিয়াওক",
        "triage_ready": "স্বাস্থ্য ট্ৰাইয়েজৰ বাবে সাজু",
        "top": "50%", "left": "20%", "delay": "1.4s", "rot": "-4deg"
    },
    {
        "word": "Click to Start", "lang": "English", "code": "en-IN",
        "back": "Back Home",     "press": "Press to Talk",        "upload": "Upload Photo",
        "triage_ready": "Ready for Health Triage",
        "top": "82%", "left": "60%", "delay": "0.9s", "rot": "2deg"
    },
]

LANG_CODE_MAP         = {item["lang"]: item["code"]         for item in LANGUAGES}
LANG_PRESS_MAP        = {item["lang"]: item["press"]        for item in LANGUAGES}
LANG_BACK_MAP         = {item["lang"]: item["back"]         for item in LANGUAGES}
LANG_UPLOAD_MAP       = {item["lang"]: item["upload"]       for item in LANGUAGES}
LANG_TRIAGE_READY_MAP = {item["lang"]: item["triage_ready"] for item in LANGUAGES}

# Mutable session state
_session = {
    "lang_code": "hi-IN",
    "back_label": "Back Home",
    "press_label": "Press to Talk",
    "upload_label": "Upload Photo",
    "triage_ready": "Ready for Health Triage"
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


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
def build_home_page():
    buttons_html = ""
    for item in LANGUAGES:
        payload = f"{item['lang']}||{item['back']}||{item['press']}||{item['upload']}"
        buttons_html += (
            f'<div class="scattered-tag" '
            f'style="top:{item["top"]};left:{item["left"]};'
            f'animation-delay:{item["delay"]};--rot:{item["rot"]};" '
            f'onclick="sendTrigger(\'{payload}\')">'
            f'<span class="word">{item["word"]}</span>'
            f'<small class="lang-label">{item["lang"]}</small>'
            f'</div>'
        )

    return f"""
<style>
  .home-container {{
    position:relative; min-height:100vh; width:100%;
    background:linear-gradient(135deg,#02060f 0%,#050d1f 25%,#060818 50%,#030b16 75%,#020810 100%);
    background-size:400% 400%;
    animation:bgShift 20s ease infinite;
    color:white; overflow:hidden;
    font-family:system-ui,-apple-system,sans-serif;
  }}
  @keyframes bgShift {{
    0%{{background-position:0% 50%}} 50%{{background-position:100% 50%}} 100%{{background-position:0% 50%}}
  }}

  .home-blob1 {{
    position:absolute; width:600px; height:600px; border-radius:50%;
    background:radial-gradient(circle,rgba(109,40,217,.18) 0%,transparent 65%);
    top:-180px; left:-150px; pointer-events:none;
    animation:blobDrift1 16s ease-in-out infinite alternate;
  }}
  .home-blob2 {{
    position:absolute; width:480px; height:480px; border-radius:50%;
    background:radial-gradient(circle,rgba(6,182,212,.12) 0%,transparent 65%);
    bottom:-120px; right:-100px; pointer-events:none;
    animation:blobDrift2 19s ease-in-out infinite alternate;
  }}
  @keyframes blobDrift1 {{ to{{ transform:translate(60px,45px) scale(1.1); }} }}
  @keyframes blobDrift2 {{ to{{ transform:translate(-50px,-40px) scale(1.08); }} }}

  .center-hero {{
    position:absolute; top:48%; left:50%;
    transform:translate(-50%,-50%);
    text-align:center; z-index:2; pointer-events:none;
  }}
  .home-title {{
    font-size:3.5rem; font-weight:900; margin-bottom:.25rem;
    background:linear-gradient(90deg,#a78bfa,#22d3ee,#60a5fa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; letter-spacing:-1px;
  }}
  .home-subtitle {{
    font-size:1rem; color:rgba(186,230,253,.6); font-weight:300;
  }}
  .home-hint {{
    margin-top:20px; font-size:.75rem; letter-spacing:.16em;
    text-transform:uppercase; color:rgba(139,92,246,.5);
    animation:hintBlink 2.8s ease-in-out infinite;
  }}
  @keyframes hintBlink {{ 0%,100%{{opacity:.3}} 50%{{opacity:.9}} }}

  .scattered-tag {{
    position:absolute;
    background:rgba(109,40,217,.1);
    backdrop-filter:blur(14px);
    border:1px solid rgba(139,92,246,.3);
    padding:12px 22px; border-radius:30px;
    cursor:pointer; z-index:5;
    display:flex; flex-direction:column; align-items:center;
    box-shadow:0 8px 32px rgba(0,0,30,.5);
    animation:floatTag 5s infinite ease-in-out;
    transition:all .3s cubic-bezier(.175,.885,.32,1.275);
    transform:rotate(var(--rot,0deg));
  }}
  .scattered-tag:hover {{
    background:rgba(139,92,246,.28);
    border-color:rgba(167,139,250,.8);
    box-shadow:0 0 35px rgba(139,92,246,.55);
    transform:scale(1.12) translateY(-6px) rotate(var(--rot,0deg));
  }}
  @keyframes floatTag {{
    0%,100% {{ transform:translateY(0) rotate(var(--rot,0deg)); }}
    50%      {{ transform:translateY(-12px) rotate(var(--rot,0deg)); }}
  }}
  .word      {{ font-size:1.1rem; font-weight:700; color:#f3e8ff; }}
  .lang-label{{ font-size:.68rem; color:rgba(196,181,253,.55); margin-top:3px; }}

  /* ── Mobile: stack tags in a scrollable grid instead of scattered absolute ── */
  @media (max-width:600px) {{
    .home-title {{ font-size:2.2rem; }}
    .home-subtitle {{ font-size:.85rem; }}
    .scattered-tag {{
      position:relative !important;
      top:auto !important; left:auto !important;
      transform:none !important;
      animation:floatTagMobile 4s infinite ease-in-out;
    }}
    .center-hero {{ position:relative; top:auto; left:auto;
      transform:none; padding:2.5rem 1rem 1rem;
      text-align:center; pointer-events:none;
    }}
    .home-container {{
      display:flex; flex-direction:column; align-items:center;
      min-height:100vh; overflow-y:auto;
      padding-bottom:2rem;
    }}
    .home-blob1, .home-blob2 {{ display:none; }}
    /* Grid of language buttons */
    .lang-grid {{
      display:grid;
      grid-template-columns:repeat(2,1fr);
      gap:12px; padding:0 1rem; width:100%; box-sizing:border-box;
    }}
    .scattered-tag {{ width:100%; justify-content:center; }}
    @keyframes floatTagMobile {{
      0%,100% {{ transform:translateY(0); }}
      50%      {{ transform:translateY(-5px); }}
    }}
  }}
</style>

<div class="home-container">
  <div class="home-blob1"></div>
  <div class="home-blob2"></div>
  <div class="center-hero">
    <h1 class="home-title">Sampark Mitra</h1>
    <p class="home-subtitle">AI-powered emergency assistant for rural India</p>
    <p class="home-hint">Tap any word to begin</p>
  </div>
  {buttons_html}
  <!-- Mobile grid (hidden on desktop via CSS, visible on mobile) -->
  <div class="lang-grid" id="lang-grid-mobile" style="display:none">
    {buttons_html}
  </div>
</div>
<script>
(function(){{
  function applyLayout() {{
    var isMobile = window.innerWidth <= 600;
    var desktop  = document.querySelectorAll('.home-container > .scattered-tag');
    var grid     = document.getElementById('lang-grid-mobile');
    if (!grid) return;
    if (isMobile) {{
      desktop.forEach(function(el) {{ el.style.display = 'none'; }});
      grid.style.display = 'grid';
    }} else {{
      desktop.forEach(function(el) {{ el.style.display = ''; }});
      grid.style.display = 'none';
    }}
  }}
  applyLayout();
  window.addEventListener('resize', applyLayout);
}})();
</script>"""


# ---------------------------------------------------------------------------
# ORB PAGE
# ---------------------------------------------------------------------------
def build_orb_page(tag="NORMAL", response_text="",
                   back_label="Back Home", press_label="Press to Talk",
                   upload_label="Upload Photo", mic_state="idle",
                   triage_ready_label="Ready for Health Triage"):
    tag_color = {
        "[EMERGENCY]":      "#ef4444",
        "[REQUEST IMAGE]":  "#f59e0b",
        "[TRIAGE COMPLETE]":"#10b981"
    }.get(tag, "#a78bfa")

    # Show triage-ready label only on first load (no response yet, idle state)
    interaction_started = bool(response_text) or mic_state in ("recording", "processing")
    triage_ready_html = ""
    if not interaction_started:
        triage_ready_html = f'<div class="triage-ready-label" id="triage-ready-label">{triage_ready_label}</div>'

    status_card = ""
    if response_text:
        clean = response_text.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        status_card = f"""
        <div class="status-card">
          <div class="status-tag-label" style="color:{tag_color}">
            {tag.replace("[","").replace("]","")}
          </div>
          <div class="status-body">{clean}</div>
        </div>"""

    # Image Upload Button displayed when model requests image
    upload_btn_html = ""
    if tag == "[REQUEST IMAGE]":
        upload_btn_html = f"""
        <input type="file" id="img_file_input" accept="image/*" style="display:none;" onchange="sendImageToGradio(this)" />
        <button class="img-btn" onclick="document.getElementById('img_file_input').click()">
          {upload_label}
        </button>
        """

    if mic_state == "recording":
        btn_label    = "Recording... tap to stop"
        btn_style    = "mic-btn mic-btn-recording"
        orb_anim     = "orb-speaking"
        status_label = "Listening..."
    elif mic_state == "processing":
        btn_label    = "Processing..."
        btn_style    = "mic-btn mic-btn-processing"
        orb_anim     = "orb-speaking"
        status_label = "Processing..."
    else:
        btn_label    = press_label
        btn_style    = "mic-btn mic-btn-idle"
        orb_anim     = "orb-idle"
        status_label = ""

    status_label_html = (
        f'<div class="orb-status-label">{status_label}</div>'
        if status_label else ""
    )

    return f"""
<style>
  @keyframes bgShift {{
    0%{{background-position:0% 50%}} 50%{{background-position:100% 50%}} 100%{{background-position:0% 50%}}
  }}
  .orb-screen {{
    min-height:100vh; width:100%;
    background:linear-gradient(135deg,#06000f,#0d0433,#001230,#00081e);
    background-size:400% 400%;
    animation:bgShift 18s ease infinite;
    color:white; padding:1.5rem;
    display:flex; flex-direction:column; align-items:center;
    justify-content:space-between; box-sizing:border-box;
    font-family:system-ui,-apple-system,sans-serif;
    position:relative; overflow:hidden;
  }}
  .orb-header {{
    width:100%; display:flex;
    justify-content:space-between; align-items:center; z-index:10;
    flex-wrap:wrap; gap:8px;
  }}
  .orb-logo {{
    font-size:1.05rem; font-weight:700;
    background:linear-gradient(90deg,#a78bfa,#22d3ee);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
  }}
  .back-btn {{
    background:rgba(109,40,217,.15); border:1px solid rgba(139,92,246,.35);
    color:rgba(196,181,253,.85); padding:9px 20px; border-radius:20px;
    cursor:pointer; font-weight:600; font-size:.88rem;
    font-family:system-ui,-apple-system,sans-serif;
    transition:all .2s;
  }}
  .back-btn:hover {{
    background:rgba(139,92,246,.3); color:#f3e8ff;
    box-shadow:0 0 18px rgba(139,92,246,.4);
  }}

  .orb-body {{
    display:flex; flex-direction:column; align-items:center;
    justify-content:center; flex:1; z-index:5; gap:16px;
    padding:16px 0; width:100%;
  }}

  /* Triage-ready label above orb */
  .triage-ready-label {{
    font-size:1.1rem; font-weight:600; letter-spacing:.04em;
    text-align:center;
    background:linear-gradient(90deg,#a78bfa,#22d3ee,#60a5fa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
    animation:triageReadyPulse 2.5s ease-in-out infinite;
    padding:0 1rem;
  }}
  @keyframes triageReadyPulse {{
    0%,100%{{opacity:.7;transform:scale(1);}}
    50%{{opacity:1;transform:scale(1.03);}}
  }}

  /* Orb wrapper for sound-reactive JS manipulation */
  .orb-wrapper {{
    position:relative; display:flex; align-items:center; justify-content:center;
  }}

  .wavy-orb {{
    width:190px; height:190px;
    background:radial-gradient(circle at 34% 32%,
      #ddd6fe 0%,#7c3aed 25%,#1d4ed8 55%,#0891b2 78%,#0e7490 100%);
    box-shadow:0 0 60px rgba(124,58,237,.65),0 0 120px rgba(6,182,212,.25),
               inset 0 0 40px rgba(0,0,0,.25);
    position:relative;
    transition:box-shadow .1s ease;
  }}
  .wavy-orb::before {{
    content:''; position:absolute; top:13%; left:17%;
    width:30%; height:20%; border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,.38) 0%,transparent 70%);
  }}

  .orb-idle {{
    animation:orbIdle 5s ease-in-out infinite;
  }}
  @keyframes orbIdle {{
    0%  {{border-radius:50%;transform:translate(0,0) scale(1);}}
    14% {{border-radius:54% 46% 52% 48%/48% 52% 48% 52%;transform:translate(7px,-9px) scale(1.016);}}
    28% {{border-radius:47% 53% 45% 55%/53% 47% 55% 45%;transform:translate(-6px,5px) scale(.987);}}
    42% {{border-radius:53% 47% 55% 45%/45% 55% 47% 53%;transform:translate(9px,7px) scale(1.011);}}
    57% {{border-radius:45% 55% 50% 50%/55% 45% 52% 48%;transform:translate(-8px,-6px) scale(.993);}}
    71% {{border-radius:52% 48% 48% 52%/50% 50% 53% 47%;transform:translate(5px,10px) scale(1.008);}}
    85% {{border-radius:49% 51% 53% 47%/47% 53% 49% 51%;transform:translate(-4px,-3px) scale(.996);}}
    100%{{border-radius:50%;transform:translate(0,0) scale(1);}}
  }}

  /* CSS-driven speaking animation (fallback / recording) */
  .orb-speaking {{
    animation:orbSpeak .45s ease-in-out infinite;
    box-shadow:0 0 80px rgba(124,58,237,.85),0 0 150px rgba(6,182,212,.4),
               inset 0 0 40px rgba(0,0,0,.2) !important;
  }}
  @keyframes orbSpeak {{
    0%  {{border-radius:50%; transform:scale(1);}}
    20% {{border-radius:42% 58% 55% 45%/58% 42% 58% 42%; transform:scale(.78) translateY(12px);}}
    40% {{border-radius:58% 42% 42% 58%/42% 58% 42% 58%; transform:scale(1.22) translateY(-14px);}}
    60% {{border-radius:45% 55% 60% 40%/55% 45% 55% 45%; transform:scale(.82) translateX(10px);}}
    80% {{border-radius:55% 45% 40% 60%/45% 55% 45% 55%; transform:scale(1.18) translateX(-12px);}}
    100%{{border-radius:50%; transform:scale(1);}}
  }}

  /* Sound-reactive: class added by JS while audio plays */
  .orb-sound-reactive {{
    animation:none !important;
  }}

  .orb-status-label {{
    font-size:.8rem; letter-spacing:.12em; text-transform:uppercase;
    color:rgba(34,211,238,.8);
    animation:statusBlink 1s ease-in-out infinite;
  }}
  @keyframes statusBlink {{ 0%,100%{{opacity:.5}} 50%{{opacity:1}} }}

  .mic-btn {{
    padding:16px 40px; border-radius:100px;
    font-size:1rem; font-weight:600; letter-spacing:.03em;
    font-family:system-ui,-apple-system,sans-serif;
    cursor:pointer; border:none; transition:all .25s ease;
    min-width:220px; text-align:center;
  }}
  .mic-btn-idle {{
    background:linear-gradient(135deg,#7c3aed,#0891b2);
    color:white;
    box-shadow:0 4px 30px rgba(124,58,237,.5);
  }}
  .mic-btn-idle:hover {{
    transform:translateY(-3px);
    box-shadow:0 8px 40px rgba(124,58,237,.7);
  }}
  .mic-btn-recording {{
    background:linear-gradient(135deg,#dc2626,#b91c1c);
    color:white;
    box-shadow:0 4px 30px rgba(220,38,38,.6);
    animation:recordPulse 1.2s ease-in-out infinite;
  }}
  @keyframes recordPulse {{
    0%,100%{{box-shadow:0 4px 30px rgba(220,38,38,.5);}}
    50%    {{box-shadow:0 4px 50px rgba(220,38,38,.9);}}
  }}
  .mic-btn-processing {{
    background:rgba(109,40,217,.25);
    border:1px solid rgba(139,92,246,.4) !important;
    color:rgba(196,181,253,.6);
    cursor:not-allowed;
  }}

  .img-btn {{
    padding:14px 32px; border-radius:100px;
    font-size:.95rem; font-weight:600;
    background:linear-gradient(135deg,#f59e0b,#d97706);
    color:white; border:none; cursor:pointer;
    box-shadow:0 4px 25px rgba(245,158,11,.4);
    transition:all .2s ease;
  }}
  .img-btn:hover {{
    transform:translateY(-2px);
    box-shadow:0 6px 35px rgba(245,158,11,.6);
  }}

  .status-card {{
    background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.15);
    border-radius:16px; padding:1.2rem; width:100%; max-width:520px;
    backdrop-filter:blur(12px); text-align:center;
    box-sizing:border-box;
  }}
  .status-tag-label {{
    font-weight:700; font-size:.85rem; margin-bottom:8px;
    text-transform:uppercase; letter-spacing:.08em;
  }}
  .status-body {{
    font-size:1rem; line-height:1.55; color:rgba(226,232,240,.9);
  }}

  .estrip {{
    width:100%; padding:10px 0 0; display:flex; justify-content:center;
    flex-wrap:wrap; gap:12px 24px;
    border-top:1px solid rgba(139,92,246,.15);
  }}
  .enum {{ font-size:.72rem; color:rgba(186,230,253,.4); letter-spacing:.06em; }}
  .enum strong {{ color:rgba(186,230,253,.75); }}

  /* ── Mobile responsive ── */
  @media (max-width:600px) {{
    .orb-screen {{ padding:1rem .75rem; }}
    .wavy-orb {{ width:150px; height:150px; }}
    .triage-ready-label {{ font-size:.95rem; }}
    .mic-btn {{ padding:14px 28px; font-size:.92rem; min-width:180px; }}
    .status-card {{ padding:1rem .85rem; }}
    .status-body {{ font-size:.9rem; }}
    .orb-body {{ gap:14px; }}
    .estrip {{ gap:10px 18px; padding:8px 0 0; }}
    .enum {{ font-size:.68rem; }}
  }}
  @media (max-width:380px) {{
    .wavy-orb {{ width:130px; height:130px; }}
    .triage-ready-label {{ font-size:.85rem; }}
    .mic-btn {{ min-width:160px; padding:12px 20px; font-size:.85rem; }}
  }}
</style>

<div class="orb-screen">
  <div class="orb-header">
    <div class="orb-logo">Sampark Mitra</div>
    <button class="back-btn" onclick="sendTrigger('__HOME__')">{back_label}</button>
  </div>

  <div class="orb-body">
    {triage_ready_html}
    <div class="orb-wrapper">
      <div class="wavy-orb {orb_anim}" id="main-orb"></div>
    </div>
    {status_label_html}
    <button class="{btn_style}" id="mic-toggle-btn" onclick="handleMicClick()">
      {btn_label}
    </button>
    {upload_btn_html}
    {status_card}
  </div>

  <div class="estrip">
    <span class="enum"><strong>112</strong> Emergency</span>
    <span class="enum"><strong>108</strong> Ambulance</span>
    <span class="enum"><strong>101</strong> Fire</span>
    <span class="enum"><strong>100</strong> Police</span>
  </div>
</div>

<script>
(function() {{
  // ── Sound-reactive orb via Web Audio API ──
  var _audioCtx = null;
  var _analyser = null;
  var _rafId    = null;
  var _orbEl    = null;

  function initAudioAnalyser(audioEl) {{
    if (!audioEl) return;
    try {{
      if (!_audioCtx) {{
        _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }}
      // Resume if suspended (mobile autoplay policy)
      if (_audioCtx.state === 'suspended') _audioCtx.resume();

      var src  = _audioCtx.createMediaElementSource(audioEl);
      _analyser = _audioCtx.createAnalyser();
      _analyser.fftSize = 64;
      src.connect(_analyser);
      src.connect(_audioCtx.destination);
    }} catch(e) {{
      console.warn('[Orb] AudioContext error:', e);
    }}
  }}

  function animateOrb() {{
    if (!_analyser || !_orbEl) return;
    var data = new Uint8Array(_analyser.frequencyBinCount);
    _analyser.getByteFrequencyData(data);

    // Average amplitude across bins
    var sum = 0;
    for (var i = 0; i < data.length; i++) sum += data[i];
    var avg = sum / data.length; // 0–255

    // Map amplitude to large visual motion
    var t    = Date.now() / 1000;
    var norm = avg / 255;            // 0–1

    // Scale: 0.72 – 1.38 (huge swing when loud)
    var scale   = 1 + norm * 0.60 - (1 - norm) * 0.10;
    // Border radius morphs aggressively with amplitude
    var r1 = 50 + norm * 24;
    var r2 = 50 - norm * 22;
    var r3 = 50 + norm * 18 * Math.sin(t * 3.1);
    var r4 = 50 - norm * 20 * Math.cos(t * 2.7);
    // Translate: orb bounces around when loud
    var tx = norm * 22 * Math.sin(t * 4.5);
    var ty = norm * 18 * Math.cos(t * 3.8);

    var glow1 = Math.round(60  + norm * 120);
    var glow2 = Math.round(120 + norm * 200);
    var alpha1 = (0.65 + norm * 0.35).toFixed(2);
    var alpha2 = (0.25 + norm * 0.45).toFixed(2);

    _orbEl.style.transform     = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
    _orbEl.style.borderRadius  = r1+'% '+r2+'% '+r3+'% '+r4+'% / '+r2+'% '+r1+'% '+r4+'% '+r3+'%';
    _orbEl.style.boxShadow     = '0 0 '+glow1+'px rgba(124,58,237,'+alpha1+'),0 0 '+glow2+'px rgba(6,182,212,'+alpha2+'),inset 0 0 40px rgba(0,0,0,.2)';

    _rafId = requestAnimationFrame(animateOrb);
  }}

  function stopOrbAnimation() {{
    if (_rafId) {{ cancelAnimationFrame(_rafId); _rafId = null; }}
    if (_orbEl) {{
      _orbEl.style.transform    = '';
      _orbEl.style.borderRadius = '';
      _orbEl.style.boxShadow    = '';
      _orbEl.classList.remove('orb-sound-reactive');
    }}
  }}

  function attachOrbToAudio() {{
    // Find hidden gradio audio element
    var audioEl = document.querySelector('#audio_output audio, audio');
    if (!audioEl) {{
      setTimeout(attachOrbToAudio, 400);
      return;
    }}
    _orbEl = document.getElementById('main-orb');
    if (!_orbEl) return;

    initAudioAnalyser(audioEl);

    audioEl.addEventListener('play', function() {{
      _orbEl.classList.add('orb-sound-reactive');
      animateOrb();
    }});
    audioEl.addEventListener('pause',  stopOrbAnimation);
    audioEl.addEventListener('ended',  stopOrbAnimation);

    // If audio is already playing (autoplay fired before we attached)
    if (!audioEl.paused) {{
      _orbEl.classList.add('orb-sound-reactive');
      animateOrb();
    }}
  }}

  // Kick off once DOM is ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', attachOrbToAudio);
  }} else {{
    attachOrbToAudio();
  }}
}})();
</script>"""


# ---------------------------------------------------------------------------
# JAVASCRIPT
# ---------------------------------------------------------------------------
GLOBAL_JS = """
var _userLat = null;
var _userLon = null;

// Request location permission on load if available
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        _userLat = pos.coords.latitude;
        _userLon = pos.coords.longitude;
    }, function(err) {
        console.log("Geolocation permission not granted/failed:", err);
    });
}

function sendTrigger(val) {
    const container = document.getElementById('router_input');
    const input = container
        ? (container.querySelector('textarea') || container.querySelector('input'))
        : null;
    if (input) {
        const proto = Object.getPrototypeOf(input);
        const desc  = Object.getOwnPropertyDescriptor(proto, 'value');
        if (desc && desc.set) desc.set.call(input, val);
        else input.value = val;
        input.dispatchEvent(new Event('input',  {bubbles:true}));
        input.dispatchEvent(new Event('change', {bubbles:true}));
    }
    const btn = document.querySelector('#hidden_trigger_btn button, #hidden_trigger_btn');
    if (btn) btn.click();
}

var _mediaRecorder = null;
var _audioChunks   = [];
var _isRecording   = false;

function handleMicClick() {
    if (_isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Microphone access is not supported by this browser.');
        return;
    }
    navigator.mediaDevices.getUserMedia({audio: true})
        .then(function(stream) {
            _audioChunks   = [];
            _isRecording   = true;
            
            var options = {};
            if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm')) {
                options = { mimeType: 'audio/webm' };
            }
            
            _mediaRecorder = new MediaRecorder(stream, options);

            _mediaRecorder.ondataavailable = function(e) {
                if (e.data && e.data.size > 0) _audioChunks.push(e.data);
            };

            _mediaRecorder.onstop = function() {
                _isRecording = false;
                stream.getTracks().forEach(function(t) { t.stop(); });
                var blob = new Blob(_audioChunks, {type: 'audio/webm'});
                sendAudioToGradio(blob);
            };

            _mediaRecorder.start();

            var btn = document.getElementById('mic-toggle-btn');
            if (btn) {
                btn.textContent = 'Recording... tap to stop';
                btn.className   = 'mic-btn mic-btn-recording';
            }
        })
        .catch(function(err) {
            alert('Could not access microphone: ' + err.message);
        });
}

function stopRecording() {
    if (_mediaRecorder && _isRecording) {
        _isRecording = false;
        _mediaRecorder.stop();
        var btn = document.getElementById('mic-toggle-btn');
        if (btn) {
            btn.textContent = 'Processing...';
            btn.className   = 'mic-btn mic-btn-processing';
            btn.disabled    = true;
        }
    }
}

function sendAudioToGradio(blob) {
    var reader = new FileReader();
    reader.onloadend = function() {
        var base64Audio = reader.result;
        // Append latitude & longitude if captured
        if (_userLat && _userLon) {
            base64Audio = base64Audio + "||" + _userLat + "||" + _userLon;
        }
        var container = document.getElementById('audio_b64_input');
        var input     = container
            ? (container.querySelector('textarea') || container.querySelector('input'))
            : null;
        if (input) {
            var proto = Object.getPrototypeOf(input);
            var desc  = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) desc.set.call(input, base64Audio);
            else input.value = base64Audio;
            input.dispatchEvent(new Event('input',  {bubbles:true}));
            input.dispatchEvent(new Event('change', {bubbles:true}));
        }
        var pipeBtn = document.querySelector('#audio_submit_btn button, #audio_submit_btn');
        if (pipeBtn) pipeBtn.click();
    };
    reader.readAsDataURL(blob);
}

function sendImageToGradio(inputElem) {
    if (!inputElem.files || !inputElem.files[0]) return;
    var file = inputElem.files[0];
    var reader = new FileReader();
    reader.onloadend = function() {
        var base64Img = reader.result;
        if (_userLat && _userLon) {
            base64Img = base64Img + "||" + _userLat + "||" + _userLon;
        }
        var container = document.getElementById('image_b64_input');
        var input     = container
            ? (container.querySelector('textarea') || container.querySelector('input'))
            : null;
        if (input) {
            var proto = Object.getPrototypeOf(input);
            var desc  = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) desc.set.call(input, base64Img);
            else input.value = base64Img;
            input.dispatchEvent(new Event('input',  {bubbles:true}));
            input.dispatchEvent(new Event('change', {bubbles:true}));
        }
        var imgBtn = document.querySelector('#image_submit_btn button, #image_submit_btn');
        if (imgBtn) imgBtn.click();
    };
    reader.readAsDataURL(file);
}
"""


# ---------------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------------
def handle_route(trigger):
    global _session

    if trigger == "__HOME__":
        return build_home_page(), gr.update(visible=False), None

    if "||" in trigger:
        parts        = trigger.split("||")
        lang_name    = parts[0]
        back_label   = parts[1] if len(parts) > 1 else "Back Home"
        press_label  = parts[2] if len(parts) > 2 else "Press to Talk"
        upload_label = parts[3] if len(parts) > 3 else "Upload Photo"
        lang_code    = LANG_CODE_MAP.get(lang_name, "hi-IN")
        triage_ready = LANG_TRIAGE_READY_MAP.get(lang_name, "Ready for Health Triage")

        _session["lang_code"]    = lang_code
        _session["back_label"]   = back_label
        _session["press_label"]  = press_label
        _session["upload_label"] = upload_label
        _session["triage_ready"] = triage_ready

        orb = build_orb_page(
            back_label=back_label,
            press_label=press_label,
            upload_label=upload_label,
            mic_state="idle",
            triage_ready_label=triage_ready
        )
        return orb, gr.update(visible=True), None

    return build_home_page(), gr.update(visible=False), None


def handle_audio_b64(audio_b64: str):
    global _session

    lang_code    = _session.get("lang_code",    "hi-IN")
    back_label   = _session.get("back_label",   "Back Home")
    press_label  = _session.get("press_label",  "Press to Talk")
    upload_label = _session.get("upload_label", "Upload Photo")
    triage_ready = _session.get("triage_ready", "Ready for Health Triage")

    def error_page(msg):
        return (
            build_orb_page(
                response_text=msg,
                back_label=back_label,
                press_label=press_label,
                upload_label=upload_label,
                mic_state="idle",
                triage_ready_label=triage_ready
            ),
            None
        )

    if not audio_b64 or len(audio_b64) < 100:
        return error_page("No audio received. Please try again.")

    lat, lon = None, None
    if "||" in audio_b64:
        parts = audio_b64.split("||")
        audio_b64 = parts[0]
        try:
            lat = float(parts[1])
            lon = float(parts[2])
        except Exception:
            pass

    if "," in audio_b64:
        audio_b64 = audio_b64.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(audio_b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tmp.write(raw_bytes)
        tmp.close()
        filepath = tmp.name
    except Exception as e:
        print(f"[Audio] File write error: {e}")
        return error_page("Could not save audio. Please try again.")

    print(f"[Pipeline] Running STT on {filepath}")
    transcript, detected_lang = transcribe(filepath)

    if not transcript:
        return error_page(
            "Could not understand the audio. Please speak clearly and try again."
        )

    if detected_lang:
        lang_code = detected_lang
        _session["lang_code"] = lang_code

    print(f"[Pipeline] Transcript={transcript!r}  Lang={lang_code!r}")

    location_str = resolve_location(lat, lon)
    location_tag = f"[Location: {location_str}]" if location_str else "[Location: None]"
    
    full_prompt  = f"{transcript}\n{location_tag}"
    print(f"[Pipeline] Calling Gemma with prompt: {full_prompt}")
    raw_reply = ask_gemma(full_prompt)
    tag, clean = parse_tags(raw_reply)
    print(f"[Pipeline] Gemma tag={tag!r}: {clean[:80]!r}")

    print("[Pipeline] Generating TTS...")
    audio_out = generate_audio_file(clean, lang_code=lang_code)

    orb = build_orb_page(
        tag=tag,
        response_text=clean,
        back_label=back_label,
        press_label=press_label,
        upload_label=upload_label,
        mic_state="idle",
        triage_ready_label=triage_ready
    )
    return orb, audio_out


def handle_image_b64(image_b64: str):
    global _session

    lang_code    = _session.get("lang_code",    "hi-IN")
    back_label   = _session.get("back_label",   "Back Home")
    press_label  = _session.get("press_label",  "Press to Talk")
    upload_label = _session.get("upload_label", "Upload Photo")
    triage_ready = _session.get("triage_ready", "Ready for Health Triage")

    if not image_b64 or len(image_b64) < 100:
        return build_orb_page(
            response_text="No image received.",
            back_label=back_label,
            press_label=press_label,
            upload_label=upload_label,
            triage_ready_label=triage_ready
        ), None

    lat, lon = None, None
    if "||" in image_b64:
        parts = image_b64.split("||")
        image_b64 = parts[0]
        try:
            lat = float(parts[1])
            lon = float(parts[2])
        except Exception:
            pass

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(image_b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(raw_bytes)
        tmp.close()
        img_path = tmp.name
    except Exception as e:
        print(f"[Image] Decoding error: {e}")
        return build_orb_page(
            response_text="Failed to process image.",
            back_label=back_label,
            press_label=press_label,
            upload_label=upload_label,
            triage_ready_label=triage_ready
        ), None

    location_str = resolve_location(lat, lon)
    location_tag = f"[Location: {location_str}]" if location_str else "[Location: None]"

    full_prompt  = f"Here is the photo of the symptom.\n{location_tag}"
    print(f"[Pipeline] Passing image ({img_path}) to Gemma...")
    raw_reply = ask_gemma(full_prompt, image_path=img_path)
    tag, clean = parse_tags(raw_reply)

    audio_out = generate_audio_file(clean, lang_code=lang_code)

    orb = build_orb_page(
        tag=tag,
        response_text=clean,
        back_label=back_label,
        press_label=press_label,
        upload_label=upload_label,
        mic_state="idle",
        triage_ready_label=triage_ready
    )
    return orb, audio_out


# ---------------------------------------------------------------------------
# GRADIO LAYOUT & FULL-PAGE CSS
# ---------------------------------------------------------------------------
CSS = """
/* Reset body and outer containers to remove black margins */
html, body, .gradio-container, .main, .contain, #component-0 {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 100vh !important;
    background-color: #02060f !important;
    border: none !important;
    overflow-x: hidden;
}

/* Remove black top margin / header lines */
.app, .gap, div[class^="svelte-"], .wrap, .container, .block {
    margin-top: 0 !important;
    padding-top: 0 !important;
    border-top: none !important;
}
.gradio-container > .main > .wrap {
    padding: 0 !important;
    gap: 0 !important;
}

/* Hide processing/loading overlay and progress bar */
.progress-bar, .eta-bar, .generating, .loader,
div.generating, .wrap.generating,
.progress-text, .progress-level, .progress-level-inner,
.meta-text, .eta, .loading {
    display: none !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Hide the Gradio audio component frontend */
#audio_output, .audio-container, [data-testid="audio"],
.component-wrapper:has(audio), gradio-audio, .gr-audio {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}

footer {display:none !important;}

#router_input, #hidden_trigger_btn, #audio_b64_input, #audio_submit_btn, #image_b64_input, #image_submit_btn {
    position:fixed !important; left:-9999px !important; top:-9999px !important;
    opacity:0 !important; pointer-events:none !important;
    height:0 !important; width:0 !important; overflow:hidden !important;
}
"""

with gr.Blocks(title="Sampark Mitra", css=CSS, js=GLOBAL_JS) as demo:

    router_input       = gr.Textbox(elem_id="router_input",       visible=True)
    hidden_trigger_btn = gr.Button("go", elem_id="hidden_trigger_btn", visible=True)

    audio_b64_input    = gr.Textbox(elem_id="audio_b64_input",    visible=True)
    audio_submit_btn   = gr.Button("submit_audio", elem_id="audio_submit_btn", visible=True)

    image_b64_input    = gr.Textbox(elem_id="image_b64_input",    visible=True)
    image_submit_btn   = gr.Button("submit_image", elem_id="image_submit_btn", visible=True)

    display_page = gr.HTML(value=build_home_page())
    audio_output = gr.Audio(
        label="Sampark Mitra Response",
        autoplay=True,
        visible=False,
        elem_id="audio_output"
    )

    hidden_trigger_btn.click(
        fn=handle_route,
        inputs=[router_input],
        outputs=[display_page, audio_output, audio_output]
    )

    audio_submit_btn.click(
        fn=handle_audio_b64,
        inputs=[audio_b64_input],
        outputs=[display_page, audio_output]
    )

    image_submit_btn.click(
        fn=handle_image_b64,
        inputs=[image_b64_input],
        outputs=[display_page, audio_output]
    )

if __name__ == "__main__":
    demo.launch()