import pvporcupine
import pyaudio

porcupine = pvporcupine.create(keywords=["hello"])  # or custom keyword

pa = pyaudio.PyAudio()
stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

print("Listening...")

while True:
    pcm = stream.read(porcupine.frame_length)
    pcm = list(pcm)

    result = porcupine.process(pcm)

    if result >= 0:
        print("Wake word detected!")
        # 👉 Send command to Pepper