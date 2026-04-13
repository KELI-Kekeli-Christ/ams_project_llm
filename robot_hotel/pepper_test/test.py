# -*- coding: utf-8 -*-
from gtts import gTTS
from naoqi import ALProxy
from pydub import AudioSegment
import os

ip_pepper = "192.168.13.222"

# 1️⃣ Générer TTS MP3
text = u"مرحبا كيف حالك"
tts = gTTS(text=text, lang="ar")
tts.save("arabic.mp3")

# 2️⃣ Convertir en WAV
sound = AudioSegment.from_mp3("arabic.mp3")
sound.export("arabic.wav", format="wav")

# 3️⃣ Copier WAV sur Pepper
os.system("scp arabic.wav nao@{}:/home/nao/arabic.wav".format(ip_pepper))

# 4️⃣ Jouer sur Pepper
audio = ALProxy("ALAudioPlayer", ip_pepper, 9559)
file_id = audio.playFile("/home/nao/arabic.wav")
print("Lecture du fichier, ID:", file_id)