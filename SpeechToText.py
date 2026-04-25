import os
import queue
import sounddevice as sd
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types

# --- 1. CONFIGURATION ---
# Ensure your credentials.json is in the same folder
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

PROJECT_ID = "bearhacks-2026"  # <--- UPDATE THIS
LOCATION = "northamerica-northeast1"
RECOGNIZER_ID = "smart-trashcan"

# This must match your "smart-trashcan" recognizer settings
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms chunks


class MicStream:
    def __init__(self):
        self.buffer = queue.Queue()

    def callback(self, indata, frames, time, status):
        if status:
            print(f"Audio Status: {status}")
        self.buffer.put(bytes(indata))

    def generator(self):
        while True:
            chunk = self.buffer.get()
            if chunk is None: return
            yield chunk


def main():
    # 2. POINT TO THE MONTREAL ENDPOINT
    # If we don't set the api_endpoint, it defaults to 'global' and fails
    client_options = {"api_endpoint": f"{LOCATION}-speech.googleapis.com"}
    client = SpeechClient(client_options=client_options)

    # 3. CONSTRUCT THE RESOURCE PATH
    recognizer_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/{RECOGNIZER_ID}"

    # Configuration for the stream
    # Note: Since the recognizer already has the model/language, we just need the streaming config
    streaming_config = cloud_speech_types.StreamingRecognitionConfig(
        config=cloud_speech_types.RecognitionConfig(
            # Optional: Overriding features like punctuation if you didn't set them in Console
            features=cloud_speech_types.RecognitionFeatures(
                enable_automatic_punctuation=True,
            )
        )
    )

    mic = MicStream()

    # 4. START THE MICROPHONE
    # Note: dtype='int16' matches LINEAR16 encoding
    with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16',
                           channels=1, callback=mic.callback):

        print(f"--- Listening (Montreal Region: {LOCATION}) ---")

        def request_generator():
            # Initial request: Setup
            yield cloud_speech_types.StreamingRecognizeRequest(
                recognizer=recognizer_path,
                streaming_config=streaming_config,
            )
            # Subsequent requests: Audio data
            for audio_chunk in mic.generator():
                yield cloud_speech_types.StreamingRecognizeRequest(audio=audio_chunk)

        # 5. STREAM TO GOOGLE
        responses = client.streaming_recognize(requests=request_generator())

        try:
            for response in responses:
                for result in response.results:
                    transcript = result.alternatives[0].transcript

                    if result.is_final:
                        print(f"\n[MESSAGE]: {transcript}")
                        # -------------------------------------------------------
                        # HACKATHON GOAL: Send 'transcript' to LLM here!
                        # -------------------------------------------------------
                    else:
                        # Print interim results (overwriting the same line)
                        print(f"[HEARING]: {transcript}", end="\r")

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()