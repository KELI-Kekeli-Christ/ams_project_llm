from naoqi import ALProxy

audio = ALProxy("ALAudioPlayer", "192.168.13.222", 9559)
print("connection reussie")
audio.playFile("http://10.126.3.163:8001/arabic")