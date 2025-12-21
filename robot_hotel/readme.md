#installer ollama
'curl -fsSL https://ollama.com/install.sh | sh'

#whisper
pip install fastapi uvicorn python-multipart
pip install git+https://github.com/ggerganov/whisper.cpp.git#subdirectory=bindings/python
