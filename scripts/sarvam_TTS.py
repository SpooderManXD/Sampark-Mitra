import base64
import io
import os
import wave
import pyaudio
from sarvamai import SarvamAI

api_key = os.environ.get("SARVAM_API_KEY")
client = SarvamAI(api_subscription_key=api_key)

# Global PyAudio instance to prevent Windows PortAudio thread deadlocks
AUDIO_PY = pyaudio.PyAudio()

def speech(text: str, lang: str = "hi-IN"):
    try:
        if not lang:
            lang = "hi-IN"

        response = client.text_to_speech.convert(
            model="bulbul:v3",
            text=text,
            target_language_code=lang,
            speaker="shubh",
        )

        if hasattr(response, "audios") and response.audios:
            audio_data = base64.b64decode(response.audios[0])
            wf = wave.open(io.BytesIO(audio_data), "rb")

            stream = AUDIO_PY.open(
                format=AUDIO_PY.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )

            data = wf.readframes(1024)
            while len(data) > 0:
                stream.write(data)
                data = wf.readframes(1024)

            stream.stop_stream()
            stream.close()

    except Exception as e:
        print(f"Error playing TTS: {e}")