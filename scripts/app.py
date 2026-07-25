"""
Sampark Mitra - Rural Emergency Triage Hub UI

Entry point: wires up the Gradio Blocks app (hidden router/audio/image
inputs, the display page, and the autoplay audio output) from the
pieces defined in the other three modules, then launches it.

Pipeline:
  1. Home page: click language word
  2. Orb page: shows "press to talk" in chosen language
  3. User records via mic or uploads a photo if requested
  4. On stop/upload: transcribe_file() / image -> ask_gemma() -> generate_audio_file() -> playback

Run with: python app.py
"""

import gradio as gr

from backend import default_session_state
from pages import build_home_page, CSS
from handlers import GLOBAL_JS, handle_route, handle_audio_b64, handle_image_b64

# ---------------------------------------------------------------------------
# GRADIO LAYOUT
# ---------------------------------------------------------------------------
# --- FIX: Gradio 6.0 CSS/JS moved to launch() ---
with gr.Blocks(title="Sampark Mitra") as demo:

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

    
    session_state = gr.State(value=default_session_state())

    hidden_trigger_btn.click(
        fn=handle_route,
        inputs=[router_input, session_state],
        outputs=[display_page, audio_output, audio_output, session_state]
    )

    audio_submit_btn.click(
        fn=handle_audio_b64,
        inputs=[audio_b64_input, session_state],
        outputs=[display_page, audio_output, session_state]
    )

    image_submit_btn.click(
        fn=handle_image_b64,
        inputs=[image_b64_input, session_state],
        outputs=[display_page, audio_output, session_state]
    )

if __name__ == "__main__":
    demo.launch(css=CSS, js=GLOBAL_JS)
