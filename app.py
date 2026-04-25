from ImageLLM import classify_current_item
from SpeechToText import listen_once
import os
import numpy as np
import sounddevice as sd

from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

# ---------------- CONFIG ----------------
MAX_ARGUMENTS = 4
MODEL_ID = "gemma-4-26b-a4b-it"

client = genai.Client(api_key=os.getenv("GEMMA_KEY"))
tts_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_KEY"))

# ---------------- TTS ----------------
def speak(text):
    """
    Converts text to speech and plays it.
    (Still blocking, but optimized slightly)
    """
    audio_stream = tts_client.text_to_speech.convert(
        text=text,
        voice_id="CObk84upvxmLAIoMXgyH",
        model_id="eleven_multilingual_v2",
        output_format="pcm_16000"
    )

    audio_bytes = b"".join(audio_stream)
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

    sd.play(audio_np, samplerate=16000)
    sd.wait()


# ---------------- OUTPUT WRAPPER ----------------
def say(text, tts=True):
    print(f"TRASHCAN: {text}")
    if tts:
        speak(text)


# ---------------- LLM ----------------
def respond_to_user(item_data, user_input):

    prompt = f"""
You are a grumpy AI smart trash can in Toronto (2026).

You already classified this item as:
- bin: {item_data.bin}
- explanation: {item_data.sass}

Now the user is arguing with you.

User says:
"{user_input}"

Rules:
- Be consistent with your decision
- If asked "why", explain clearly
- Do NOT repeat yourself
- Be grumpy, short (max 4 sentences)
"""

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=120
        )
    )

    return response.text


# ---------------- MAIN LOOP ----------------
def run_trashcan_ai():

    say("Smart Trashcan Booting...")
    
    item = classify_current_item()

    if not item:
        say("Could not classify item.", tts=False)
        return

    say("Analysis complete.")
    say(item.sass)
    say(f"Bin classification: {item.bin}")
    
    if item.bin.lower() == "accidental":
        return

    # If trash → no need for argument system
    if item.bin.lower() == "trash":
        say("Trash detected. Opening!")
        return

    say("Listening for user response...")

    argument_count = 0

    while argument_count < MAX_ARGUMENTS:

        # STT (blocking but necessary)
        user_text = listen_once()

        if not user_text:
            break

        print(f"\nUSER: {user_text}")

        # small UX improvement (no TTS delay here)
        print("TRASHCAN: Processing input...")

        # LLM call
        response = respond_to_user(item, user_text)

        # speak response
        say(response)

        # exit conditions
        if any(word in user_text.lower() for word in ["stop", "fine", "ok", "whatever"]):
            say("Conversation terminated. Don't test me again.")
            break

        argument_count += 1

    if argument_count >= MAX_ARGUMENTS:
        say("I've repeated myself too many times. I'm done arguing.")


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    run_trashcan_ai()
