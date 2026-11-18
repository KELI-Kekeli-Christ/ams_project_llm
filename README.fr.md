<p align="center">
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.fr.md"><b>Français</b></a>
  &nbsp;·&nbsp;
  <a href="README.es.md">Español</a>
</p>

Espace assistant hôtel : services FastAPI, application robot, vision (YOLO et détection de visages) et Whisper. Son `README.md` est la carte des dossiers.

```bash
python -m venv env && source env/bin/activate
pip install -r ams_project_llm/requirements.txt
uvicorn main:app --reload
```

Lancez uvicorn depuis le dossier qui contient le `main.py` FastAPI nommé dans le README. `robot_hotel` démarre avec `python main.py`. Les tests utilisent `pytest`.

---


La documentation anglaise déjà présente dans ce dépôt reste dans le fichier anglais.
