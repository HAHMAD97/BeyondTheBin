import os
import queue
import sounddevice as sd
from dotenv import load_dotenv

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types

# -----------------------------
# ENV SETUP
# -----------------------------
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

PROJECT_ID = "bearhacks-2026"
LOCATION = "northamerica-northeast1"
RECOGNIZER_ID = "smart-trashcan"

RATE = 16000
CHUNK = int(RATE / 10)


# -----------------------------
# MICROPHONE STREAM HANDLER
# -----------------------------
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
            if chunk is None:
                return
            yield chunk


# -----------------------------
# MAIN FUNCTION YOU IMPORT
# -----------------------------
def listen_once():
    """
    Listens to the microphone until it gets a FINAL transcript.
    Returns the recognized speech as a string.
    """

    client_options = {"api_endpoint": f"{LOCATION}-speech.googleapis.com"}
    client = SpeechClient(client_options=client_options)

    recognizer_path = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/{RECOGNIZER_ID}"
    )

    streaming_config = cloud_speech_types.StreamingRecognitionConfig(
        config=cloud_speech_types.RecognitionConfig(
            features=cloud_speech_types.RecognitionFeatures(
                enable_automatic_punctuation=True,
            )
        )
    )

    mic = MicStream()

    with sd.RawInputStream(
        samplerate=RATE,
        blocksize=CHUNK,
        dtype="int16",
        channels=1,
        callback=mic.callback,
    ):

        def request_generator():
            # First request = config
            yield cloud_speech_types.StreamingRecognizeRequest(
                recognizer=recognizer_path,
                streaming_config=streaming_config,
            )

            # Audio stream
            for audio_chunk in mic.generator():
                yield cloud_speech_types.StreamingRecognizeRequest(audio=audio_chunk)

        responses = client.streaming_recognize(requests=request_generator())

        for response in responses:
            for result in response.results:
                if result.is_final:
                    return result.alternatives[0].transcript.lower()

    return None


# -----------------------------
# TEST
# -----------------------------
if __name__ == "__main__":
    print("Listening...")
    text = listen_once()
    print(f"You said: {text}")