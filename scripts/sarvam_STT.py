import glob
import json
import os
import tempfile
import wave
from sarvamai import SarvamAI

api_sarvam = os.environ.get("SARVAM_API_KEY")
svm = SarvamAI(api_subscription_key=api_sarvam) if api_sarvam else None


def transcribe(filepath):
    """
    Transcribes an audio file using Sarvam AI STT API.

    :param filepath: Path to the WAV audio file passed from ui.py
    :return: Tuple of (transcript_text, detected_lang)
    """
    global svm
    if svm is None and os.environ.get("SARVAM_API_KEY"):
        svm = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))

    if svm is None:
        print("[STT Error] SARVAM_API_KEY environment variable is not set.")
        return None, None

    if not filepath or not os.path.exists(filepath):
        print(f"[STT Error] Audio file not found at path: {filepath}")
        return None, None

    # Calculate audio duration in seconds
    try:
        with wave.open(filepath, "rb") as wf:
            duration = wf.getnframes() / float(wf.getframerate())
    except Exception as e:
        print(f"[STT Warning] Could not read WAV header ({e}). Defaulting to sync mode.")
        duration = 0.0

    print(f"[STT] Processing audio file: {filepath} ({duration:.2f} seconds)")

    transcript_text = None
    detected_lang = None

    # Handle Audio <= 30 seconds (Synchronous API)
    if duration <= 30:
        print("[STT] Using Synchronous API...")
        try:
            with open(filepath, "rb") as audio_file:
                response = svm.speech_to_text.transcribe(
                    file=audio_file, model="saaras:v3", mode="transcribe"
                )

            if isinstance(response, dict):
                transcript_text = response.get("transcript")
                detected_lang = response.get("language_code")
            else:
                transcript_text = getattr(response, "transcript", None)
                detected_lang = getattr(response, "language_code", None)

        except Exception as e:
            print(f"[STT Error] Synchronous API call failed: {e}")

    # Handle Audio > 30 seconds (Batch Job API)
    else:
        print("[STT] Audio > 30s. Switching to Sarvam Batch API...")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                job = svm.speech_to_text_job.create_job(
                    model="saaras:v3", mode="transcribe"
                )
                job.upload_files(file_paths=[filepath])
                job.start()

                print("[STT] Batch job started. Waiting for completion...")
                job.wait_until_complete()

                job.download_outputs(output_dir=temp_dir)

                json_files = glob.glob(os.path.join(temp_dir, "*.json"))
                if json_files:
                    with open(json_files[0], "r", encoding="utf-8") as f:
                        batch_data = json.load(f)

                    if isinstance(batch_data, dict):
                        transcript_text = batch_data.get("transcript", "")
                        detected_lang = batch_data.get("language_code")
                    elif isinstance(batch_data, list) and len(batch_data) > 0:
                        transcript_text = batch_data[0].get("transcript", "")
                        detected_lang = batch_data[0].get("language_code")
                else:
                    print("[STT Error] No output JSON files found from batch job.")

        except Exception as e:
            print(f"[STT Error] Batch job execution failed: {e}")

    return transcript_text, detected_lang