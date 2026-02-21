"""
WebSocket pour l'appel vocal (icône téléphone).
Vous parlez → serveur transcrit + chat → réponse texte → lue en audio sur votre appareil (TTS navigateur).
Activé si ENABLE_REALTIME_VOICE_CALL=true.
"""
import base64
import json
import os
import tempfile
from flask import current_app
from flask_sock import Sock

sock = Sock()


def init_realtime_voice_ws(app):
    """Enregistre la route WebSocket sur l'app Flask."""
    sock.init_app(app)

    @sock.route("/ws/realtime-voice")
    def realtime_voice_ws(ws):
        if not current_app.config.get("ENABLE_REALTIME_VOICE_CALL", False):
            ws.send(json.dumps({"type": "error", "message": "Realtime voice call is disabled"}))
            return
        session_id = None
        audio_chunks = []
        last_audio_mime = ""

        def send_error(msg):
            try:
                ws.send(json.dumps({"type": "error", "message": msg}))
            except Exception:
                pass

        try:
            while True:
                raw = ws.receive()
                if raw is None:
                    break
                try:
                    msg = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    send_error("Invalid message format")
                    continue
                typ = msg.get("type")
                if typ == "init":
                    session_id = msg.get("session_id") or None
                    ws.send(json.dumps({"type": "ready", "session_id": session_id}))
                    continue
                if typ == "audio":
                    data = msg.get("data")
                    if data:
                        audio_chunks.append(data)
                    if msg.get("mime"):
                        last_audio_mime = msg.get("mime", "")
                    continue
                if typ == "end_turn":
                    if not audio_chunks:
                        # Aucun audio envoyé (seuil, silence) : pas de message parlé
                        ws.send(json.dumps({
                            "type": "response_done",
                            "full_text": "",
                            "session_id": session_id
                        }))
                        audio_chunks = []
                        continue
                    try:
                        audio_b64 = "".join(audio_chunks)
                        audio_bytes = base64.b64decode(audio_b64)
                    except Exception as e:
                        send_error(f"Invalid audio data: {e}")
                        audio_chunks = []
                        continue
                    audio_chunks = []
                    mime = (last_audio_mime or "").lower()
                    suffix = ".mp4" if "mp4" in mime else ".webm"
                    last_audio_mime = ""
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                            f.write(audio_bytes)
                            tmp_path = f.name
                        model = current_app.config.get("whisper_model")
                        if not model:
                            send_error("Whisper model not available")
                            continue
                        from services.whisper import transcribe_audio
                        result = transcribe_audio(model, file=tmp_path)
                        text = (result.get("text") or "").strip()
                        if not text or len(text) < 2:
                            # Transcription vide (audio sous le seuil) : pas de message parlé
                            ws.send(json.dumps({
                                "type": "response_done",
                                "full_text": "",
                                "session_id": session_id
                            }))
                            continue
                        from services.chat import chat_stream, chat
                        full_response = None
                        try:
                            for chunk, full in chat_stream(user_message=text, session_id=session_id):
                                if chunk:
                                    try:
                                        ws.send(json.dumps({"type": "response_chunk", "text": chunk}))
                                    except Exception:
                                        break
                                if full is not None:
                                    full_response = full
                        except Exception:
                            resp = chat(user_message=text, session_id=session_id)
                            data = resp.get_json() if hasattr(resp, "get_json") and resp else None
                            if data and data.get("response"):
                                try:
                                    ws.send(json.dumps({"type": "response", "text": data["response"], "session_id": data.get("session_id", session_id)}))
                                except Exception:
                                    pass
                            continue
                        if full_response is not None:
                            sid = session_id
                            try:
                                ws.send(json.dumps({
                                    "type": "response_done",
                                    "full_text": full_response,
                                    "session_id": sid
                                }))
                            except Exception:
                                pass
                        else:
                            try:
                                ws.send(json.dumps({
                                    "type": "response_done",
                                    "full_text": "",
                                    "session_id": session_id
                                }))
                            except Exception:
                                pass
                    except Exception as e:
                        send_error(str(e))
                    finally:
                        if tmp_path and os.path.isfile(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    continue
                send_error("Unknown message type")
        except Exception as e:
            send_error(str(e))
