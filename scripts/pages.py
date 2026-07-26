"""
Sampark Mitra - UI page builders

Domain: pure HTML/CSS page rendering. Builds the two full-page HTML
blobs (home page with the language picker, and the orb/conversation
page) plus the global CSS injected into the Gradio Blocks app. No
Gradio event-handling or backend/API logic lives here.
"""

from backend import LANGUAGES

# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
def build_home_page():
    buttons_html = ""
    mobile_buttons_html = ""

    for item in LANGUAGES:
        payload = f"{item['lang']}||{item['back']}||{item['press']}||{item['upload']}||{item['recording']}||{item['processing']}"
        buttons_html += (
            f'<div class="scattered-tag" '
            f'style="top:{item["top"]};left:{item["left"]};'
            f'animation-delay:{item["delay"]};--rot:{item["rot"]};" '
            f'onclick="sendTrigger(\'{payload}\')">'
            f'<span class="word">{item["word"]}</span>'
            f'<small class="lang-label">{item["lang"]}</small>'
            f'</div>'
        )
        mobile_buttons_html += (
            f'<div class="scattered-tag" onclick="sendTrigger(\'{payload}\')">'
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

  /* Mobile grid layout */
  #lang-grid-mobile {{
    display:none;
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%);
    grid-template-columns:1fr 1fr;
    gap:10px; z-index:5; width:90vw; max-width:340px;
    margin-top:60px;
  }}
  #lang-grid-mobile .scattered-tag {{
    position:static; animation:none;
    transform:none !important; --rot:0deg;
    width:100%; text-align:center;
    padding:10px 8px; border-radius:16px;
  }}
  #lang-grid-mobile .scattered-tag:active {{
    background:rgba(139,92,246,.38);
    transform:scale(.96) !important;
  }}
  .home-title   {{ font-size:2.2rem; }}
  .home-subtitle{{ font-size:.85rem; }}
  @media (max-width:600px) {{
    .home-title   {{ font-size:1.8rem; }}
    .center-hero  {{ top:18%; transform:translate(-50%,0); }}
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
  <div id="lang-grid-mobile">
    {mobile_buttons_html}
  </div>
</div>"""


# ---------------------------------------------------------------------------
# ORB PAGE
# ---------------------------------------------------------------------------
def build_orb_page(tag="NORMAL", response_text="",
                   back_label="Back Home", press_label="Press to Talk",
                   upload_label="Upload Photo", mic_state="idle",
                   ready_label="Ready for Health Triage", show_ready=True,
                   recording_label="Recording... tap to stop",
                   processing_label="Processing..."):
    tag_color = {
        "[EMERGENCY]":      "#ef4444",
        "[REQUEST IMAGE]":  "#f59e0b",
        "[TRIAGE COMPLETE]":"#10b981"
    }.get(tag, "#a78bfa")

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
        btn_label    = recording_label
        btn_style    = "mic-btn mic-btn-recording"
        orb_anim     = "orb-speaking"
        status_label = "Listening..."
    elif mic_state == "processing":
        btn_label    = processing_label
        btn_style    = "mic-btn mic-btn-processing"
        orb_anim     = "orb-speaking"
        status_label = processing_label
    else:
        btn_label    = press_label
        btn_style    = "mic-btn mic-btn-idle"
        orb_anim     = "orb-idle"
        status_label = ""

    status_label_html = (
        f'<div class="orb-status-label">{status_label}</div>'
        if status_label else ""
    )

    # "Ready for Health Triage" label — only shown before interaction begins
    ready_html = ""
    if show_ready and not response_text:
        ready_html = f'<div class="ready-label" id="ready-label">{ready_label}</div>'

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
    flex-wrap: nowrap; gap: 8px;
  }}
  .orb-logo {{
    font-size:1.05rem; font-weight:700;
    background:linear-gradient(90deg,#a78bfa,#22d3ee);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; white-space:nowrap;
  }}
  .back-btn {{
    background:rgba(109,40,217,.15); border:1px solid rgba(139,92,246,.35);
    color:rgba(196,181,253,.85); padding:8px 16px; border-radius:20px;
    cursor:pointer; font-weight:600; font-size:.82rem;
    font-family:system-ui,-apple-system,sans-serif;
    transition:all .2s; white-space:nowrap; flex-shrink:0;
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

  /* ── Ready for Health Triage label ── */
  .ready-label {{
    font-size:1.15rem; font-weight:600; letter-spacing:.04em;
    text-align:center;
    background:linear-gradient(90deg,#a78bfa,#22d3ee,#a78bfa);
    background-size:200% auto;
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
    animation:shimmerText 3s linear infinite, fadeInDown .6s ease both;
    padding:0 1rem;
  }}
  @keyframes shimmerText {{
    0%{{background-position:0% center}} 100%{{background-position:200% center}}
  }}
  @keyframes fadeInDown {{
    from{{opacity:0;transform:translateY(-12px)}} to{{opacity:1;transform:translateY(0)}}
  }}

  .wavy-orb {{
    width:190px; height:190px;
    background:radial-gradient(circle at 34% 32%,
      #ddd6fe 0%,#7c3aed 25%,#1d4ed8 55%,#0891b2 78%,#0e7490 100%);
    box-shadow:0 0 60px rgba(124,58,237,.65),0 0 120px rgba(6,182,212,.25),
               inset 0 0 40px rgba(0,0,0,.25);
    position:relative; border-radius:50%; flex-shrink:0;
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

  .orb-speaking {{
    animation:orbSpeak .45s ease-in-out infinite;
    box-shadow:0 0 100px rgba(124,58,237,.95),0 0 200px rgba(6,182,212,.55),
               0 0 300px rgba(124,58,237,.25), inset 0 0 40px rgba(0,0,0,.2) !important;
  }}
  @keyframes orbSpeak {{
    0%  {{border-radius:50%; transform:scale(1);}}
    25% {{border-radius:44% 56% 52% 48%/56% 44% 48% 52%; transform:scale(.82);}}
    50% {{border-radius:56% 44% 44% 56%/44% 56% 56% 44%; transform:scale(1.22);}}
    75% {{border-radius:48% 52% 56% 44%/52% 48% 44% 56%; transform:scale(.86);}}
    100%{{border-radius:50%; transform:scale(1);}}
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
    min-width:220px; max-width:90vw; text-align:center;
    box-sizing:border-box;
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
    transition:all .2s ease; max-width:90vw;
  }}
  .img-btn:hover {{
    transform:translateY(-2px);
    box-shadow:0 6px 35px rgba(245,158,11,.6);
  }}

  .status-card {{
    background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.15);
    border-radius:16px; padding:1.2rem; width:100%; max-width:520px;
    backdrop-filter:blur(12px); text-align:center; box-sizing:border-box;
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
    gap:16px; flex-wrap:wrap;
    border-top:1px solid rgba(139,92,246,.15);
  }}
  .enum {{ font-size:.72rem; color:rgba(186,230,253,.4); letter-spacing:.06em; }}
  .enum strong {{ color:rgba(186,230,253,.75); }}

  /* ── Mobile responsiveness ── */
  @media (max-width:600px) {{
    .orb-screen {{ padding:1rem .75rem; gap:0; }}
    .orb-logo   {{ font-size:.9rem; }}
    .back-btn   {{ padding:6px 12px; font-size:.78rem; }}
    .wavy-orb   {{ width:140px; height:140px; }}
    .ready-label{{ font-size:.95rem; }}
    .mic-btn    {{ padding:14px 28px; font-size:.92rem; min-width:180px; }}
    .status-card{{ padding:.9rem; max-width:100%; }}
    .status-body{{ font-size:.92rem; }}
    .orb-body   {{ gap:12px; }}
    .estrip     {{ gap:10px; padding:8px 0 0; }}
    .enum       {{ font-size:.65rem; }}
  }}
  @media (max-width:380px) {{
    .wavy-orb   {{ width:115px; height:115px; }}
    .ready-label{{ font-size:.82rem; }}
    .mic-btn    {{ padding:12px 22px; font-size:.85rem; min-width:160px; }}
  }}
</style>

<div class="orb-screen">
  <div class="orb-header">
    <div class="orb-logo">Sampark Mitra</div>
    <button class="back-btn" onclick="sendTrigger('__HOME__')">{back_label}</button>
  </div>

  <div class="orb-body">
    {ready_html}
    <div class="wavy-orb {orb_anim}" id="main-orb"></div>
    {status_label_html}
    <button class="{btn_style}" id="mic-toggle-btn" onclick="handleMicClick()"
      data-idle-label="{press_label}"
      data-recording-label="{recording_label}"
      data-processing-label="{processing_label}">
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
</div>"""



# ---------------------------------------------------------------------------
# GLOBAL CSS
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
