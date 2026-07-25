import base64
import io
import os
import wave
import pyaudio
from sarvamai import SarvamAI

api_key = os.environ.get("SARVAM_API_KEY")
client = SarvamAI(api_subscription_key=api_key)


def speech(text: str, lang: str = "hi-IN"):
    """
    Converts text to speech using Sarvam AI and plays it through the speakers.
    """
    try:
        # Default fallback if language detection failed
        if not lang:
            lang = "hi-IN"

        response = client.text_to_speech.convert(
            model="bulbul:v3",
            text=text,
            target_language_code=lang,
            speaker="shubh",
        )

        # Extract base64 audio payload from response
        if hasattr(response, "audios") and response.audios:
            audio_data = base64.b64decode(response.audios[0])

            # Play audio in real-time
            wf = wave.open(io.BytesIO(audio_data), "rb")
            p = pyaudio.PyAudio()

            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
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
            p.terminate()

    except Exception as e:
        print(f"Error playing TTS: {e}")