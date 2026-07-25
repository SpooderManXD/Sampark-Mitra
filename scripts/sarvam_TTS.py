from sarvamai import SarvamAI
import os
from gemma_inference import ask_gemma, main

api_key = os.environ.get("SARVAM_API_KEY")
client = SarvamAI(api_subscription_key=api_key)


def speech(text: str):
    response = client.text_to_speech.convert( model="bulbul:v3",
                                            text=text,
                                            target_language_code="hi-IN",
                                            speaker="shubh",
                                            )
    return response





