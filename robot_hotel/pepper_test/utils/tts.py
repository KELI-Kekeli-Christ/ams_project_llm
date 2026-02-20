# -*- coding: utf-8 -*-
"""
Synthèse vocale sécurisée pour le robot
"""
from .helpers import safe_print, transliterate_to_ascii


def safe_say(robot, text, language=None):
    """Call robot.say safely. Convertit le texte en ASCII pour eviter UnicodeEncodeError avec le TTS NAOqi."""
    try:
        # Ne pas utiliser str(text) sur unicode en Python 2 -> provoque UnicodeEncodeError
        if text is None:
            text = ""
        elif isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        # else: garder tel quel (unicode/str)
        # Translitterer IMMEDIATEMENT avant toute autre operation
        text = transliterate_to_ascii(text)
        if not text or not text.strip():
            return False
        try:
            if language is not None:
                robot.say(text, language=language)
            else:
                robot.say(text)
            safe_print("safe_say: called robot.say (tts exists={})", bool(getattr(robot, 'tts', None)))
            return True
        except Exception as e:
            safe_print("safe_say: robot.say raised {}", repr(e))
            return False
    except Exception as e:
        safe_print("safe_say: error preparing text: {}", repr(e))
        return False
