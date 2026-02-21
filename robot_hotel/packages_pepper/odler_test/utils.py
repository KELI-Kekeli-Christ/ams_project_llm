# -*- coding: utf-8 -*-
"""
Fonctions utilitaires pour le script Pepper
"""

import sys
import unicodedata
import socket
import requests
import json
import time

# HTML escape helper with compatibility fallback (Python2/3)
try:
    import html as _html_mod
    def escape_html(s):
        if s is None:
            return ''
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='ignore')
        return _html_mod.escape(s)
except Exception:
    try:
        import cgi as _cgi
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            return _cgi.escape(s, quote=True)
    except Exception:
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            s = str(s)
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')


def safe_print(msg, *args):
    """Print safely to stdout handling environments with ASCII-only encodings.

    Compatible with Python 2 and 3. Avoids using `print(..., **kwargs)` which
    can be a syntax error under Python 2 where `print` is a statement.
    """
    import sys
    try:
        text = msg.format(*args) if args else msg
    except Exception:
        try:
            text = str(msg)
        except Exception:
            text = repr(msg)

    try:
        # Prefer writing str to stdout (Python 3)
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            # Try writing bytes to buffer if available (Python 3)
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
                sys.stdout.buffer.flush()
            else:
                # Python 2 fallback: encode to utf-8 then write
                sys.stdout.write(text.encode("utf-8", errors="replace") + "\n")
                sys.stdout.flush()
        except Exception:
            try:
                sys.stdout.write(repr(text) + "\n")
                sys.stdout.flush()
            except Exception:
                pass


def transliterate_to_ascii(text):
    """Return an ASCII-only approximation of `text` by removing diacritics."""
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        nkfd = unicodedata.normalize('NFKD', text)
        return nkfd.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        try:
            return str(text)
        except Exception:
            return repr(text)


def force_utf8(s):
    """Force a value to a UTF-8-safe string for Python2/3 environments.

    Returns a unicode `str` on Python 3 (decoded UTF-8) or a UTF-8 encoded
    `str`/`bytes` on Python 2 as appropriate. If conversion fails, returns
    an empty string.
    """
    try:
        if s is None:
            return ""
        # Detect Python2
        try:
            unicode  # type: ignore
            is_py2 = True
        except NameError:
            is_py2 = False

        if is_py2:
            try:
                if isinstance(s, unicode):  # type: ignore
                    return s.encode('utf-8')
                elif isinstance(s, str):
                    try:
                        return s.decode('utf-8', 'ignore').encode('utf-8')
                    except Exception:
                        return s
            except Exception:
                return ""
        else:
            # Python 3: ensure we return a str (unicode)
            if isinstance(s, bytes):
                return s.decode('utf-8', 'ignore')
            elif isinstance(s, str):
                return s
            else:
                return str(s)
    except Exception:
        return ""


def get_local_ip_for_robot(robot_ip):
    """
    Obtient l'IP locale de la machine pour que le robot puisse y accéder
    
    Args:
        robot_ip: IP du robot pour déterminer l'interface réseau à utiliser
    
    Returns:
        str: IP locale de la machine
    """
    try:
        import socket
        # Se connecter au robot pour déterminer l'interface réseau locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((robot_ip, 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        # Fallback: essayer de trouver l'IP locale
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # Vérifier si c'est une IP valide (pas 127.0.0.1)
            if local_ip != "127.0.0.1":
                return local_ip
        except:
            pass
        return "127.0.0.1"  # Dernier recours


def map_language_code_to_ald_label(code):
    """Map common ISO language codes to ALTextToSpeech language labels.

    Returns a label expected by ALTextToSpeech.setLanguage (best-effort).
    """
    # Import ici pour éviter les imports circulaires
    try:
        from config import ROBOT_CONFIG
    except ImportError:
        # Fallback si config n'est pas disponible
        ROBOT_CONFIG = {"language": "French"}
    
    try:
        if not code:
            return ROBOT_CONFIG.get("language", "French")
        s = str(code).lower()
        if s.startswith('fr'):
            return 'French'
        if s.startswith('en'):
            return 'English'
        if s.startswith('es'):
            return 'Spanish'
        if s.startswith('de'):
            return 'German'
        if s.startswith('it'):
            return 'Italian'
        if s.startswith('pt'):
            return 'Portuguese'
        if s.startswith('nl'):
            return 'Dutch'
        if s.startswith('ru'):
            return 'Russian'
        if s.startswith('ja'):
            return 'Japanese'
        if s.startswith('ko'):
            return 'Korean'
        if s.startswith('zh'):
            return 'Chinese'
        # Fallback: return configured default
        return ROBOT_CONFIG.get("language", "French")
    except Exception:
        return ROBOT_CONFIG.get("language", "French")


def post_file_with_retries(url, files, attempts=3, timeout=None):
    """
    Post a file with simple retry logic on timeout/connection errors.
    Returns the `requests.Response` or `None` if all attempts fail.
    """
    # Import ici pour éviter les imports circulaires
    try:
        from config import API_CONFIG
        if timeout is None:
            timeout = API_CONFIG.get("timeout", 60)
    except ImportError:
        if timeout is None:
            timeout = 60  # Valeur par défaut

    for i in range(attempts):
        try:
            return requests.post(url, files=files, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if i < attempts - 1:
                backoff = 1 + i * 2
                time.sleep(backoff)
                continue
            return None
        except Exception as e:
            safe_print("❌ Erreur lors de l'envoi du fichier: {}".format(e))
            import traceback
            traceback.print_exc()
            return None