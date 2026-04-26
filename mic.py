import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

sample_rate = 16000
seconds = 3

audio = sd.rec(
    int(seconds * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype="int16"
)
sd.wait()

write("recording.wav", sample_rate, audio)