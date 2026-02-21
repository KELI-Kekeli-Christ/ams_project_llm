"""
Blueprints des routes de l'API Pepper Hotel
"""
from .chat import bp as chat_bp
from .audio import bp as audio_bp
from .reservation import bp as reservation_bp
from .face import bp as face_bp
from .qr_scan import bp as qr_scan_bp
from .email_routes import bp as email_bp
from .pages import bp as pages_bp
from .tablet import bp as tablet_bp

__all__ = [
    'chat_bp',
    'audio_bp',
    'reservation_bp',
    'face_bp',
    'qr_scan_bp',
    'email_bp',
    'pages_bp',
    'tablet_bp',
]
