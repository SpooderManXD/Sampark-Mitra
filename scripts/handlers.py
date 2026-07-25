"""
Sampark Mitra - Event handlers & client-side JS

Domain: the Gradio event-handler pipeline (routing between home/orb
pages, running the audio and image pipelines through STT -> Gemma ->
TTS) plus the GLOBAL_JS blob that drives mic capture, geolocation and
image upload in the browser. This is the glue between backend.py
(services/data) and pages.py (HTML rendering).
"""

import os
import base64
import tempfile

import gradio as gr
from pydub import AudioSegment

from backend import (
    default_session_state,
    transcribe,
    ask_gemma,
    resolve_location,
    generate_audio_file,
    parse_tags,
    LANG_CODE_MAP,
    LANG_READY_MAP,
)
from pages import build_home_page, build_orb_page

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

// ── Sound-reactive orb via Web Audio API ──
// Runs on every page render; polls for the orb + audio elements.
var _orbAudioCtx  = null;
var _orbAnalyser  = null;
var _orbRafId     = null;
var _orbAudioEl   = null;
var _orbAttached  = false;

// Smoothing state for the orb visualiser
var _orbSmoothed = 0;

function _orbAnimate() {
    if (!_orbAnalyser) return;
    var orb = document.getElementById('main-orb');
    if (!orb) { _orbRafId = null; return; }

    var data = new Uint8Array(_orbAnalyser.frequencyBinCount);
    _orbAnalyser.getByteFrequencyData(data);

    // Weight bass frequencies more heavily for dramatic impact
    var sum = 0, weightedSum = 0, totalWeight = 0;
    for (var i = 0; i < data.length; i++) {
        var w = (data.length - i) / data.length; // bass = higher weight
        weightedSum += data[i] * w;
        totalWeight += w * 255;
        sum += data[i];
    }
    var rawNorm = weightedSum / totalWeight; // 0–1, bass-weighted

    // Smooth with fast attack, slow decay (makes it feel alive)
    if (rawNorm > _orbSmoothed) {
        _orbSmoothed = _orbSmoothed * 0.3 + rawNorm * 0.7; // fast attack
    } else {
        _orbSmoothed = _orbSmoothed * 0.85 + rawNorm * 0.15; // slow decay
    }
    var norm = _orbSmoothed;

    // Punch: apply a power curve to exaggerate loud moments
    var punch = Math.pow(norm, 0.55);

    var t     = Date.now() / 1000;

    // Scale: idle ~1, loud peaks up to 1.75
    var scale = 1 + punch * 0.75 + norm * 0.10;

    // Border-radius: dramatic shape morphing driven by punch
    var r1 = 50 + punch * 38 * Math.sin(t * 5.2);
    var r2 = 50 - punch * 36 * Math.cos(t * 4.1);
    var r3 = 50 + punch * 34 * Math.sin(t * 6.3 + 1.2);
    var r4 = 50 - punch * 32 * Math.cos(t * 5.7 + 0.8);

    // Translation: orb bounces around with sound
    var tx = punch * 40 * Math.sin(t * 5.5 + norm);
    var ty = punch * 35 * Math.cos(t * 4.2 + norm * 1.3);

    // Glow: inner tight glow + huge outer bloom
    var g1   = Math.round(60  + punch * 220);
    var g2   = Math.round(120 + punch * 350);
    var g3   = Math.round(200 + punch * 500);
    var a1   = (0.7  + punch * 0.30).toFixed(2);
    var a2   = (0.30 + punch * 0.55).toFixed(2);
    var a3   = (0.10 + punch * 0.35).toFixed(2);

    // Brightness/hue shift on the orb gradient during loud moments
    var brightness = 1 + punch * 0.6;
    var saturate   = 1 + punch * 0.9;

    orb.style.transform    = 'translate('+tx+'px,'+ty+'px) scale('+scale+')';
    orb.style.borderRadius = r1+'% '+r2+'% '+r3+'% '+r4+'% / '+r2+'% '+r1+'% '+r4+'% '+r3+'%';
    orb.style.boxShadow    =
        '0 0 '+g1+'px rgba(124,58,237,'+a1+'),' +
        '0 0 '+g2+'px rgba(6,182,212,'+a2+'),' +
        '0 0 '+g3+'px rgba(167,139,250,'+a3+'),' +
        'inset 0 0 40px rgba(0,0,0,.2)';
    orb.style.filter = 'brightness('+brightness+') saturate('+saturate+')';

    _orbRafId = requestAnimationFrame(_orbAnimate);
}

function _orbStopAnimate() {
    if (_orbRafId) { cancelAnimationFrame(_orbRafId); _orbRafId = null; }
    _orbSmoothed = 0;
    var orb = document.getElementById('main-orb');
    if (orb) {
        orb.style.transform    = '';
        orb.style.borderRadius = '';
        orb.style.boxShadow    = '';
        orb.style.filter       = '';
    }
}

function _orbInitAnalyser(audioEl) {
    try {
        if (!_orbAudioCtx) {
            _orbAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (_orbAudioCtx.state === 'suspended') _orbAudioCtx.resume();
        var src = _orbAudioCtx.createMediaElementSource(audioEl);
        _orbAnalyser = _orbAudioCtx.createAnalyser();
        _orbAnalyser.fftSize = 64;
        src.connect(_orbAnalyser);
        src.connect(_orbAudioCtx.destination);
        _orbAttached = true;
    } catch(e) {
        console.warn('[Orb] AudioContext error:', e);
    }
}

function _orbTryAttach() {
    // Look for a fresh audio element (Gradio replaces the DOM on each update)
    var audioEl = document.querySelector('#audio_output audio, audio[src]');
    if (!audioEl || audioEl === _orbAudioEl) {
        setTimeout(_orbTryAttach, 600);
        return;
    }
    _orbAudioEl  = audioEl;
    _orbAttached = false;
    _orbAnalyser = null;

    audioEl.addEventListener('play', function() {
        if (!_orbAttached) _orbInitAnalyser(audioEl);
        if (_orbAnalyser) _orbAnimate();
    });
    audioEl.addEventListener('pause', _orbStopAnimate);
    audioEl.addEventListener('ended', _orbStopAnimate);

    if (!audioEl.paused && audioEl.currentTime > 0) {
        if (!_orbAttached) _orbInitAnalyser(audioEl);
        if (_orbAnalyser) _orbAnimate();
    }
    // Keep polling so we pick up audio elements injected after page-nav
    setTimeout(_orbTryAttach, 1200);
}

// Start polling once DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _orbTryAttach);
} else {
    _orbTryAttach();
}

// Home-page mobile layout helper (re-runs after every Gradio HTML swap)
function _applyHomeLayout() {
    var isMobile = window.innerWidth <= 600;
    var desktop  = document.querySelectorAll('.home-container > .scattered-tag');
    var grid     = document.getElementById('lang-grid-mobile');
    if (!grid) return;
    if (isMobile) {
        desktop.forEach(function(el) { el.style.display = 'none'; });
        grid.style.display = 'grid';
    } else {
        desktop.forEach(function(el) { el.style.display = ''; });
        grid.style.display = 'none';
    }
}
window.addEventListener('resize', _applyHomeLayout);
// MutationObserver so it fires whenever Gradio swaps the HTML component
(function() {
    var mo = new MutationObserver(function() { _applyHomeLayout(); });
    function _startObs() {
        var target = document.querySelector('.gradio-container') || document.body;
        mo.observe(target, { childList: true, subtree: true });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _startObs);
    else _startObs();
})();
"""



# ---------------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------------
def handle_route(trigger, session_state):
    if session_state is None:
        session_state = default_session_state()

    if trigger == "__HOME__":
        return build_home_page(), gr.update(visible=False), None, session_state

    if "||" in trigger:
        parts        = trigger.split("||")
        lang_name    = parts[0]
        back_label   = parts[1] if len(parts) > 1 else "Back Home"
        press_label  = parts[2] if len(parts) > 2 else "Press to Talk"
        upload_label = parts[3] if len(parts) > 3 else "Upload Photo"
        lang_code    = LANG_CODE_MAP.get(lang_name, "hi-IN")
        ready_label  = LANG_READY_MAP.get(lang_name, "Ready for Health Triage")

        session_state["lang_code"]    = lang_code
        session_state["back_label"]   = back_label
        session_state["press_label"]  = press_label
        session_state["upload_label"] = upload_label
        session_state["ready_label"]  = ready_label

        orb = build_orb_page(
            back_label=back_label,
            press_label=press_label,
            upload_label=upload_label,
            ready_label=ready_label,
            show_ready=True,
            mic_state="idle"
        )
        return orb, gr.update(visible=True), None, session_state

    return build_home_page(), gr.update(visible=False), None, session_state


def handle_audio_b64(audio_b64: str, session_state, request: gr.Request):
    if session_state is None:
        session_state = default_session_state()

    # A stable per-browser-tab id from Gradio's own connection, used to keep each visitor's Gemma triage history separate (see gemma_inference.py session_id).
    session_id = request.session_hash if request else "default"

    lang_code    = session_state.get("lang_code",    "hi-IN")
    back_label   = session_state.get("back_label",   "Back Home")
    press_label  = session_state.get("press_label",  "Press to Talk")
    upload_label = session_state.get("upload_label", "Upload Photo")
    ready_label  = session_state.get("ready_label",  "Ready for Health Triage")

    def error_page(msg):
        return (
            build_orb_page(
                response_text=msg,
                back_label=back_label,
                press_label=press_label,
                upload_label=upload_label,
                ready_label=ready_label,
                show_ready=False,
                mic_state="idle"
            ),
            None,
            session_state
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

        # Write raw bytes to a temp file first (WebM/OGG/etc from browser)
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tmp_in.write(raw_bytes)
        tmp_in.flush()
        tmp_in.close()

        # Convert to WAV using pydub (requires ffmpeg)
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_out.close()
        filepath = tmp_out.name

        try:
            audio_segment = AudioSegment.from_file(tmp_in.name)
            # Sarvam STT works best with 16-bit mono PCM WAV at 16 kHz
            audio_segment = (audio_segment
                             .set_frame_rate(16000)
                             .set_channels(1)
                             .set_sample_width(2))
            # Export with explicit PCM WAV parameters (no compression)
            audio_segment.export(
                filepath, format="wav",
                parameters=["-acodec", "pcm_s16le"]
            )
            print(f"[Audio] Converted to WAV via pydub: {filepath}")
        except Exception as conv_err:
            print(f"[Audio] pydub conversion failed ({conv_err}), trying subprocess ffmpeg...")
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_in.name,
                 "-ar", "16000", "-ac", "1", "-f", "wav", filepath],
                capture_output=True
            )
            if result.returncode != 0 or not os.path.exists(filepath) or os.path.getsize(filepath) < 100:
                print(f"[Audio] ffmpeg stderr: {result.stderr.decode()}")
                # Last resort: write raw bytes and hope transcribe handles it
                with open(filepath, "wb") as f:
                    f.write(raw_bytes)

        try:
            os.unlink(tmp_in.name)
        except Exception:
            pass

        if not os.path.exists(filepath) or os.path.getsize(filepath) < 100:
            return error_page("Could not save audio. Please try again.")

        # Validate WAV has actual audio content (not silent/corrupt)
        try:
            validation = AudioSegment.from_wav(filepath)
            duration_s = len(validation) / 1000.0
            rms        = validation.rms
            print(f"[Audio] WAV validated: {duration_s:.2f}s, rms={rms}")
            if duration_s < 0.3:
                return error_page("Recording was too short. Please hold the button and speak.")
            if rms < 10:
                return error_page("No sound detected. Please check your microphone and try again.")
        except Exception as val_err:
            print(f"[Audio] WAV validation warning: {val_err}")

        print(f"[Audio] WAV file ready: {filepath} ({os.path.getsize(filepath)} bytes)")

    except Exception as e:
        print(f"[Audio] File conversion error: {e}")
        return error_page("Could not save audio. Please try again.")

    print(f"[Pipeline] Running STT on {filepath}")
    transcript, detected_lang = transcribe(filepath)

    if not transcript:
        print(f"[Pipeline] STT returned empty — file={filepath}, size={os.path.getsize(filepath) if os.path.exists(filepath) else 'missing'}")
        return error_page(
            "Could not recognise your speech. Please speak clearly closer to the mic and try again."
        )

    if detected_lang:
        lang_code = detected_lang
        session_state["lang_code"] = lang_code

    print(f"[Pipeline] Transcript={transcript!r}  Lang={lang_code!r}")

    location_str = resolve_location(lat, lon)
    location_tag = f"[Location: {location_str}]" if location_str else "[Location: None]"
    
    full_prompt  = f"{transcript}\n{location_tag}"
    print(f"[Pipeline] Calling Gemma with prompt: {full_prompt}")
    raw_reply = ask_gemma(full_prompt, session_id=session_id)
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
        ready_label=ready_label,
        show_ready=False,
        mic_state="idle"
    )
    return orb, audio_out, session_state


def handle_image_b64(image_b64: str, session_state, request: gr.Request):
    if session_state is None:
        session_state = default_session_state()

    session_id = request.session_hash if request else "default"

    lang_code    = session_state.get("lang_code",    "hi-IN")
    back_label   = session_state.get("back_label",   "Back Home")
    press_label  = session_state.get("press_label",  "Press to Talk")
    upload_label = session_state.get("upload_label", "Upload Photo")
    ready_label  = session_state.get("ready_label",  "Ready for Health Triage")

    if not image_b64 or len(image_b64) < 100:
        return build_orb_page(
            response_text="No image received.",
            back_label=back_label,
            press_label=press_label,
            upload_label=upload_label,
            ready_label=ready_label,
            show_ready=False
        ), None, session_state

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
            ready_label=ready_label,
            show_ready=False
        ), None, session_state

    location_str = resolve_location(lat, lon)
    location_tag = f"[Location: {location_str}]" if location_str else "[Location: None]"

    full_prompt  = f"Here is the photo of the symptom.\n{location_tag}"
    print(f"[Pipeline] Passing image ({img_path}) to Gemma...")
    raw_reply = ask_gemma(full_prompt, image_path=img_path, session_id=session_id)
    tag, clean = parse_tags(raw_reply)

    audio_out = generate_audio_file(clean, lang_code=lang_code)

    orb = build_orb_page(
        tag=tag,
        response_text=clean,
        back_label=back_label,
        press_label=press_label,
        upload_label=upload_label,
        ready_label=ready_label,
        show_ready=False,
        mic_state="idle"
    )
    return orb, audio_out, session_state

