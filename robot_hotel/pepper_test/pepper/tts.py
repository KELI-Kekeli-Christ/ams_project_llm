#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text-to-Speech module for pepper_test.
Handles TTS functionality for the Pepper robot.
"""

def safe_say(robot, text, language=None):
    """Call robot.say safely: ensure utf-8 str and fallback to ASCII transliteration.

    Returns True on success, False on failure.
    """
    from utils.helpers import transliterate_to_ascii, force_utf8
    
    try:
        text = force_utf8(text)

        try:
            if language is not None:
                res = robot.say(text, language=language)
            else:
                res = robot.say(text)
            print("safe_say: called robot.say (tts exists={})".format(bool(getattr(robot, 'tts', None))))
            return True
        except UnicodeEncodeError:
            # fallback to ASCII-only
            safe_text = transliterate_to_ascii(text)
            try:
                if language is not None:
                    robot.say(safe_text, language=language)
                else:
                    robot.say(safe_text)
                print("safe_say: used ASCII fallback")
                return True
            except Exception:
                print("safe_say: failed to call robot.say after fallback")
                return False
        except Exception as e:
            print("safe_say: robot.say raised {}".format(repr(e)))
            return False
    except Exception as e:
        print("safe_say: error preparing text: {}".format(repr(e)))
        return False

