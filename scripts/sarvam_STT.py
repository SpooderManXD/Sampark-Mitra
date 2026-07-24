from sarvamai import SarvamAI
import os
import pyaudio
import wave
import keyboard
import time
import glob
import json
import tempfile

api_sarvam = os.environ.get("SARVAM_API_KEY")
svm = SarvamAI(api_subscription_key=api_sarvam)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
OUTPUT_FILENAME = "scripts/recordedFile.wav"

def transcribe():
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILENAME), exist_ok=True)

    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=2,
        frames_per_buffer=CHUNK
    )

    frames = []
    print("Press SPACE to start recording.")
    keyboard.wait('space')
    print("Recording... Press SPACE to stop.")
    time.sleep(0.2)

    while True:
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except KeyboardInterrupt:
            break

        if keyboard.is_pressed('space'):
            print("Stopping recording after brief delay...")
            time.sleep(0.2)
            break

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Write audio frames to disk
    waveFile = wave.open(OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

    # Calculate recorded audio duration in seconds
    with wave.open(OUTPUT_FILENAME, 'rb') as wf:
        duration = wf.getnframes() / float(wf.getframerate())

    print(f"Recorded Audio Duration: {duration:.2f} seconds")

    # Handle Audio <= 30 seconds (Synchronous API)
    if duration <= 30:
        print("Using Synchronous STT API...")
        response = svm.speech_to_text.transcribe(
            file=open(OUTPUT_FILENAME, "rb"),
            model="saaras:v3",
            mode="transcribe"
        )
        transcript_text = (
            response.get("transcript")
            if isinstance(response, dict)
            else getattr(response, "transcript", None)
        )

    # Handle Audio > 30 seconds (Batch Job API)
    else:
        print("Audio exceeds 30 seconds. Switching to Sarvam Batch API...")
        
        # Create temporary directory to hold the downloaded batch result JSON
        with tempfile.TemporaryDirectory() as temp_dir:
            job = svm.speech_to_text_job.create_job(
                model="saaras:v3",
                mode="transcribe"
            )
            job.upload_files(file_paths=[OUTPUT_FILENAME])
            job.start()
            
            print("Batch processing job started. Waiting for completion...")
            job.wait_until_complete()
            
            # Download completed output JSON
            job.download_outputs(output_dir=temp_dir)
            
            # Read transcript from downloaded JSON file
            json_files = glob.glob(os.path.join(temp_dir, "*.json"))
            if json_files:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    batch_data = json.load(f)
                    transcript_text = batch_data.get("transcript", "")
            else:
                transcript_text = None

    return transcript_text

