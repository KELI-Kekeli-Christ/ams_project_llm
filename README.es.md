<p align="center">
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.fr.md">Français</a>
  &nbsp;·&nbsp;
  <a href="README.es.md"><b>Español</b></a>
</p>

Espacio de un asistente de hotel: servicios FastAPI, aplicación de robot, visión (YOLO y detección de caras) y Whisper. Su `README.md` es el mapa de las carpetas.

```bash
python -m venv env && source env/bin/activate
pip install -r ams_project_llm/requirements.txt
uvicorn main:app --reload
```

Ejecuta uvicorn desde la carpeta que contiene el `main.py` de FastAPI nombrado en el README. `robot_hotel` arranca con `python main.py`. Las pruebas usan `pytest`.

---


La documentación en inglés que ya estaba en este repositorio sigue en el archivo en inglés.
