#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fonctions utilitaires génériques pour le projet Pepper.

Ce module regroupe notamment :
- un print sécurisé (`safe_print`) pour les environnements avec encodage ASCII,
- une translittération vers l'ASCII (`transliterate_to_ascii`),
- un helper pour faire parler le robot en gérant proprement l'UTF-8 (`safe_say`).
"""

import sys
import unicodedata


def safe_print(msg, *args):
    """Print en toute sécurité en gérant les environnements ASCII-only.

    Compatible Python 2/3, évite d'utiliser `print(..., **kwargs)` qui peut
    être invalide en Python 2.
    """
    try:
        text = msg.format(*args) if args else msg
    except Exception:
        try:
            text = str(msg)
        except Exception:
            text = repr(msg)

    try:
        # Python 3: écrire une str directement
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            # Essayer d'écrire des bytes sur buffer si disponible (Python 3)
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
                sys.stdout.buffer.flush()
            else:
                # Fallback Python 2: encoder en utf-8 puis écrire
                sys.stdout.write(text.encode("utf-8", errors="replace") + "\n")
                sys.stdout.flush()
        except Exception:
            try:
                sys.stdout.write(repr(text) + "\n")
                sys.stdout.flush()
            except Exception:
                # Dernier recours: abandonner silencieusement
                pass


def transliterate_to_ascii(text):
    """Retourne une approximation ASCII de `text` en supprimant les diacritiques."""
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        nkfd = unicodedata.normalize("NFKD", text)
        return nkfd.encode("ascii", "ignore").decode("ascii")
    except Exception:
        try:
            return str(text)
        except Exception:
            return repr(text)


def safe_say(robot, text, language=None):
    """Appelle `robot.say` en sécurité: garantit une str UTF-8 et fallback ASCII.

    Retourne True en cas de succès, False sinon.
    """
    try:
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8")
            except Exception:
                text = text.decode("utf-8", errors="ignore")
        else:
            text = str(text)

        try:
            if language is not None:
                robot.say(text, language=language)
            else:
                robot.say(text)
            # Si robot.say retourne une valeur, on l'ignore : on considère que ça a fonctionné
            safe_print(
                "safe_say: called robot.say (tts exists={})",
                bool(getattr(robot, "tts", None)),
            )
            return True
        except UnicodeEncodeError:
            # Fallback ASCII-only
            safe_text = transliterate_to_ascii(text)
            try:
                if language is not None:
                    robot.say(safe_text, language=language)
                else:
                    robot.say(safe_text)
                safe_print("safe_say: used ASCII fallback")
                return True
            except Exception:
                safe_print("safe_say: failed to call robot.say after fallback")
                return False
        except Exception as e:
            safe_print("safe_say: robot.say raised {}", repr(e))
            return False
    except Exception as e:
        safe_print("safe_say: error preparing text: {}", repr(e))
        return False

