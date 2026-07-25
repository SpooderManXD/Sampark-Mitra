import glob
import json
import os
import tempfile
import time
import wave
import keyboard
import pyaudio
from sarvamai import SarvamAI

api_sarvam = os.environ.get("SARVAM_API_KEY")
svm = SarvamAI(api_subscription_key=api_sarvam)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
OUTPUT_FILENAME = "scripts/recordedFile.wav"


def transcribe():
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILENAME), exist_ok=True)

    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=2,
        frames_per_buffer=CHUNK,
    )

    frames = []
    print("Press SPACE to start recording.")
    keyboard.wait("space")
    print("Recording... Press SPACE to stop.")
    time.sleep(0.2)

    while True:
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except KeyboardInterrupt:
            break

        if keyboard.is_pressed("space"):
            print("Stopping recording after brief delay...")
            time.sleep(0.2)
            break

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Write audio frames to disk
    with wave.open(OUTPUT_FILENAME, "wb") as waveFile:
        waveFile.setnchannels(CHANNELS)
        waveFile.setsampwidth(audio.get_sample_size(FORMAT))
        waveFile.setframerate(RATE)
        waveFile.writeframes(b"".join(frames))

    # Calculate recorded audio duration in seconds
    with wave.open(OUTPUT_FILENAME, "rb") as wf:
        duration = wf.getnframes() / float(wf.getframerate())

    print(f"Recorded Audio Duration: {duration:.2f} seconds")

    transcript_text = None
    detected_lang = None

    # Handle Audio <= 30 seconds (Synchronous API)
    if duration <= 30:
        print("Using Synchronous STT API...")
        try:
            with open(OUTPUT_FILENAME, "rb") as audio_file:
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
            print(f"Error during Synchronous STT API call: {e}")

    # Handle Audio > 30 seconds (Batch Job API)
    else:
        print("Audio exceeds 30 seconds. Switching to Sarvam Batch API...")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                job = svm.speech_to_text_job.create_job(
                    model="saaras:v3", mode="transcribe"
                )
                job.upload_files(file_paths=[OUTPUT_FILENAME])
                job.start()

                print(
                    "Batch processing job started. Waiting for completion..."
                )
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
                    print("No output JSON files found from batch job.")

        except Exception as e:
            print(f"Error during Batch STT execution: {e}")

    return transcript_text, detected_lang


if __name__ == "__main__":
    text, lang = transcribe()
    print(f"\nDetected Language: {lang}")
    print(f"Transcript: {text}")