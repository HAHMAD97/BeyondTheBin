import os
import numpy as np
import sounddevice as sd
import soundfile as sf
import asyncio
import threading
import queue
from dataclasses import dataclass

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


# ---------------- DATA CLASSES ----------------
@dataclass
class GenerationRequest:
    text: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future = None

@dataclass
class PlaybackRequest:
    is_file: bool                 # True for mp3, False for raw TTS audio
    audio_data: any               # filepath (str) OR numpy array of audio
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future = None


# ---------------- QUEUES ----------------
# Holds texts waiting to be converted by ElevenLabs (Async level)
generation_queue = asyncio.Queue()

# Holds raw audio waiting to be physically played (OS Thread level)
playback_queue = queue.Queue()


# ---------------- WORKER 1: API GENERATOR (ASYNC) ----------------
async def tts_generation_worker():
    """
    Pulls text from the generation queue, fetches audio from ElevenLabs as fast
    as possible, and drops the raw audio into the playback queue.
    """
    while True:
        req: GenerationRequest = await generation_queue.get()

        try:
            # We run the blocking ElevenLabs network call in a background thread
            # so it doesn't freeze our async loop.
            def fetch_audio():
                audio_stream = tts_client.text_to_speech.convert(
                    text=req.text,
                    voice_id="wDl9tTl7DVZA5R5l74ro",
                    model_id="eleven_multilingual_v2",
                    output_format="pcm_16000",
                )
                audio_bytes = b"".join(audio_stream)
                return np.frombuffer(audio_bytes, dtype=np.int16)

            raw_audio_np = await asyncio.to_thread(fetch_audio)

            # As soon as it's downloaded, push it to the playback queue
            playback_queue.put(PlaybackRequest(
                is_file=False,
                audio_data=raw_audio_np,
                loop=req.loop,
                future=req.future
            ))

        except Exception as e:
            print(f"ElevenLabs Generation Error: {e}")
            # If network fails, we must release the wait lock to prevent the app from hanging
            if req.future and req.loop:
                req.loop.call_soon_threadsafe(req.future.set_result, False)

        finally:
            generation_queue.task_done()


# ---------------- WORKER 2: OS AUDIO PLAYER (THREAD) ----------------
def audio_playback_worker(q: queue.Queue):
    """
    Runs in a single dedicated OS thread.
    Pulls raw audio and plays it sequentially. Zero overlap, zero network delay.
    """
    while True:
        req: PlaybackRequest = q.get()

        try:
            if req.is_file:
                # Play local file (like intro mp3)
                data, samplerate = sf.read(req.audio_data)
                sd.play(data, samplerate)
                sd.wait()
            else:
                # Play pre-downloaded ElevenLabs audio
                sd.play(req.audio_data, samplerate=16000)
                sd.wait()

        except Exception as e:
            print(f"Audio Playback Error: {e}")

        finally:
            # Wake up the main loop if wait=True was used
            if req.future and req.loop:
                req.loop.call_soon_threadsafe(req.future.set_result, True)

        q.task_done()


# ---------------- OUTPUT WRAPPERS ----------------
async def play_audio_file(filename, wait=True):
    loop = asyncio.get_running_loop()
    future = loop.create_future() if wait else None

    # Skips generation, goes straight to playback
    playback_queue.put(PlaybackRequest(is_file=True, audio_data=filename, loop=loop, future=future))

    if wait:
        await future


async def say(text, tts=True, wait=False):
    print(f"TRASHCAN: {text}\n")
    if not tts:
        return

    loop = asyncio.get_running_loop()
    future = loop.create_future() if wait else None

    # Pushes to the generation queue instantly
    await generation_queue.put(GenerationRequest(text=text, loop=loop, future=future))

    if wait:
        # Pauses until the PLAYBACK worker finishes playing it and signals back
        await future


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
    # We now play the intro through the exact same queue as the TTS!
    # This prevents the intro from overlapping with the first TTS line.
    await play_audio_file("trashcan_intro.mp3")

    await say("Place an item in front of me and I'll tell you where it goes!")

    # Push blocking sensor read to a thread pool
    await asyncio.to_thread(distance_sensor.wait_for_item)

    # Talk IN THE BACKGROUND while classifying
    await say("Item detected. Analyzing waste based on Toronto 2026 Rules...")

    # Push blocking camera logic to a thread pool
    item = await asyncio.to_thread(classify_current_item)

    if not item:
        await say("Could not classify item.", tts=False)
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    await say("Analysis complete.")
    await say(item.sass)
    await say(f'Bin classification "{item.bin}"')

    if item.bin.upper() == "ACCIDENTAL":
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    if item.bin.upper() == "TRASH":
        # Talk IN THE BACKGROUND while motor moves
        await say("Trash detected. Opening!")

        await asyncio.to_thread(move_steps, STEPS, DIRECTION, DELAY)
        await asyncio.to_thread(distance_sensor.wait_for_item_removed)
        return

    await say("Do you have anything to say about that?")

    argument_count = 0

    while argument_count < MAX_ARGUMENTS:
        user_text = await asyncio.to_thread(listen_once)

        if not user_text:
            continue

        print(f"\nUSER: {user_text}")

        response = await respond_to_user(item, user_text)

        await say(response)

        if any(word in user_text.lower() for word in ["stop", "fine", "ok", "whatever"]):
            await say("Conversation terminated. Don't test me again.")
            break

        argument_count += 1

    if argument_count >= MAX_ARGUMENTS:
        await say("I've repeated myself too many times. I'm done arguing.")

    await asyncio.to_thread(distance_sensor.wait_for_item_removed)


# ---------------- ENTRY ----------------
async def main():
    generation_task = asyncio.create_task(tts_generation_worker())

    try:
        while True:
            await run_trashcan_ai()
    except asyncio.CancelledError:
        pass
    finally:
        generation_task.cancel()


if __name__ == "__main__":
    # Start the dedicated OS thread for audio BEFORE starting the async loop
    audio_thread = threading.Thread(target=audio_playback_worker, args=(playback_queue,), daemon=True)
    audio_thread.start()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSmart trashcan stopped.")