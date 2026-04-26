import os
import numpy as np
import sounddevice as sd
import asyncio

from ImageLLM import classify_current_item
from SpeechToText import listen_once
from MotorManual import move_steps
from DistanceDetection import trash_distance_sensor

from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

# ---------------- CONFIG ----------------
MAX_ARGUMENTS = 4
MODEL_ID = "gemma-4-26b-a4b-it"

client = genai.Client(api_key=os.getenv("GEMMA_KEY"))
tts_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_KEY"))

STEPS = 2048  # 180 degrees
DIRECTION = "forward"
DELAY = 0.0008

# Distance sensor setup
distance_sensor = trash_distance_sensor(
    echo_pin=20,
    trigger_pin=21,
    target_cm=20,
    tolerance_cm=5,
    hold_seconds=1,
)


# ---------------- TTS ----------------
def speak_sync(text):
    """
    Synchronous TTS generation and playback.
    We will run this in a background thread.
    """
    audio_stream = tts_client.text_to_speech.convert(
        text=text,
        voice_id="wDl9tTl7DVZA5R5l74ro",
        model_id="eleven_multilingual_v2",
        output_format="pcm_16000",
    )

    audio_bytes = b"".join(audio_stream)
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

    sd.play(audio_np, samplerate=16000)
    sd.wait()  # Blocking, but safe because we put it in a thread later


# ---------------- OUTPUT WRAPPER ----------------
async def say(text, tts=True, wait=True):
    """
    Async wrapper.
    If wait=True, it blocks until speech finishes.
    If wait=False, speech plays in the background while code continues.
    """
    print(f"TRASHCAN: {text}\n")
    if tts:
        if wait:
            # Wait for the audio to finish playing before moving to the next line
            await asyncio.to_thread(speak_sync, text)
        else:
            # "Fire and forget" - starts talking and immediately moves to the next line
            asyncio.create_task(asyncio.to_thread(speak_sync, text))


# ---------------- LLM ----------------
async def respond_to_user(item_data, user_input):
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
- Be short (max 4 sentences)
"""
    # Using Google GenAI's async client (.aio)
    response = await client.aio.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=120,
        ),
    )

    return response.text


# ---------------- MAIN LOOP ----------------
async def run_trashcan_ai():
    data, samplerate = sf.read("trashcan_intro.mp3")

    sd.play(data, samplerate)
    sd.wait()  # waits until playback finishes

    # Push blocking sensor read to a thread
    await asyncio.to_thread(distance_sensor.wait_for_item)

    # Talk IN THE BACKGROUND while classifying the item!
    await say("Item detected. Analyzing waste based on Toronto 2026 Rules...", wait=False)

    # Push blocking camera/image logic to a thread
    item = await asyncio.to_thread(classify_current_item)

    if not item:
        await say("Could not classify item.", tts=False)
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    await say("Analysis complete.", wait=False)
    await say(item.sass, wait=True)
    await say(f'Bin classification "{item.bin}"', wait=True)

    if item.bin.upper() == "ACCIDENTAL":
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    if item.bin.upper() == "TRASH":
        # Talk IN THE BACKGROUND while the motor moves!
        await say("Trash detected. Opening!", wait=False)

        # Push blocking motor movement to a thread
        await asyncio.to_thread(move_steps, STEPS, DIRECTION, DELAY)

        # Wait until the object/person moves away
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    await say("Do you have anything to say about that?", wait=True)

    argument_count = 0

    while argument_count < MAX_ARGUMENTS:
        # We MUST wait for the mic to listen, so we await the thread
        user_text = await asyncio.to_thread(listen_once)

        if not user_text:
            continue

        print(f"\nUSER: {user_text}")

        response = await respond_to_user(item, user_text)

        # We wait=True here so it doesn't try to listen to the user while it is still talking
        await say(response, wait=True)

        if any(word in user_text.lower() for word in ["stop", "fine", "ok", "whatever"]):
            await say("Conversation terminated. Don't test me again.", wait=True)
            break

        argument_count += 1

    if argument_count >= MAX_ARGUMENTS:
        await say("I've repeated myself too many times. I'm done arguing.")

    # Prevent same item from instantly triggering the next loop
    await asyncio.to_thread(distance_sensor.wait_for_item_removed)

    await say("Waiting for item...", tts=False)


# ---------------- ENTRY ----------------
async def main():
    # Wait=False so it can boot up other tasks if needed while talking
    await say("Place an item in front of me and I'll tell you where it goes!")

    try:
        while True:
            await run_trashcan_ai()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        # This starts the async event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSmart trashcan stopped.")