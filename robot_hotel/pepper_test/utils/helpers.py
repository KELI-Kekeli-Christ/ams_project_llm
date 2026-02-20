#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper utilities for pepper_test module.
Contains safe_print, escape_html, transliterate_to_ascii, force_utf8, etc.
"""

import sys
import unicodedata


def safe_print(msg, *args):
    """Print safely to stdout handling environments with ASCII-only encodings.

    Compatible with Python 2 and 3. Avoids using `print(..., **kwargs)` which
    can be a syntax error under Python 2 where `print` is a statement.
    """
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
            return s.replace('&', '&amp;').replace('<', '<').replace('>', '>').replace('"', '"').replace("'", '&#x27;')


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


# Check if OpenCV is available
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    # safe_print is defined above, but we need to avoid circular import
    print("OpenCV (cv2) non disponible. Le scan QR code utilisera le téléchargement direct depuis l'URL si disponible.")
    print("Pour installer OpenCV: pip install opencv-python")

