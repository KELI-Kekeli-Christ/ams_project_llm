# -*- coding: utf-8 -*-
"""
Utilitaires : affichage, encodage, réseau
"""
import sys
import unicodedata

# HTML escape (Python2/3)
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
    """Print safely to stdout (ASCII-only environments)."""
    try:
        text = msg.format(*args) if args else msg
    except Exception:
        try:
            text = str(msg)
        except Exception:
            text = repr(msg)
    # Remplacer les caracteres non-ASCII (Python 2 unicode ou Python 3 str avec accents)
    try:
        if text is None:
            text = ""
        elif text:
            text = transliterate_to_ascii(text)
    except Exception:
        try:
            t = text if text is not None else ""
            b = t.encode('ascii', errors='replace')
            text = b.decode('ascii') if sys.version_info[0] >= 3 else b
        except Exception:
            text = "(encoding error)"
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except (UnicodeEncodeError, UnicodeDecodeError):
        try:
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
                sys.stdout.buffer.flush()
            else:
                sys.stdout.write(text.encode("utf-8", errors="replace").decode("utf-8") + "\n")
                sys.stdout.flush()
        except Exception:
            try:
                safe_text = str(text).encode('ascii', errors='replace').decode('ascii')
                sys.stdout.write(safe_text + "\n")
                sys.stdout.flush()
            except Exception:
                pass


def transliterate_to_ascii(text):
    """Return ASCII-only approximation by removing diacritics."""
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
    """Force value to UTF-8-safe string (Python2/3)."""
    try:
        if s is None:
            return ""
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
            if isinstance(s, bytes):
                return s.decode('utf-8', 'ignore')
            elif isinstance(s, str):
                return s
            else:
                return str(s)
    except Exception:
        return ""


def get_local_ip_for_robot(robot_ip):
    """Obtient l'IP locale pour que le robot puisse accéder à l'API."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((robot_ip, 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and local_ip != "127.0.0.1":
            return local_ip
    except Exception:
        pass

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and local_ip != "127.0.0.1":
            return local_ip
    except Exception:
        pass

    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and local_ip != "127.0.0.1":
            return local_ip
    except Exception:
        pass

    return "127.0.0.1"


def map_language_code_to_ald_label(code):
    """Map ISO language code to ALTextToSpeech label."""
    from config import ROBOT_CONFIG
    try:
        if not code:
            return ROBOT_CONFIG.get("language", "French")
        s = str(code).lower()
        mapping = {
            'fr': 'French', 'en': 'English', 'es': 'Spanish', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'ru': 'Russian',
            'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
        }
        for prefix, label in mapping.items():
            if s.startswith(prefix):
                return label
        return ROBOT_CONFIG.get("language", "French")
    except Exception:
        return ROBOT_CONFIG.get("language", "French")
