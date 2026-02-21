"""
Routes Pages : accueil, test, location
"""
from flask import Blueprint, request, render_template
from services.location import get_heure_date

bp = Blueprint('pages', __name__)


@bp.route("/")
def home():
    """Page d'accueil de l'API"""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pepper Robot - Hôtel</title>
        <style>
            body {
                font-family: 'Inter', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #8b5cf6 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 100%;
            }
            h1 { color: #333; margin-bottom: 10px; }
            p { color: #666; margin-bottom: 30px; }
            .btn {
                display: inline-block;
                padding: 15px 30px;
                border-radius: 30px;
                text-decoration: none;
                font-weight: bold;
                font-size: 16px;
                margin: 10px;
                transition: transform 0.2s;
            }
            .btn:hover { transform: translateY(-2px); }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #8b5cf6 100%);
                color: white;
            }
            .btn-secondary {
                background: #f0f0f0;
                color: #333;
            }
            .links { margin-top: 30px; }
            .links a {
                display: block;
                color: #667eea;
                margin: 10px 0;
                text-decoration: none;
            }
            .links a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Pepper Robot</h1>
            <p>Serveur en ligne. Accédez aux interfaces:</p>
            
            <a href="/test" class="btn btn-primary">🧪 Interface de Test</a>
            <a href="/tablet" class="btn btn-primary">📱 Tablette Pepper (réservation audio)</a>
            <a href="/chat" class="btn btn-secondary">💬 Chat</a>
            <a href="/chat/qrcode/html" class="btn btn-secondary">📱 QR Code Chatbot</a>
            <a href="/api-docs" class="btn btn-secondary">📚 API Docs</a>
            
            <div class="links">
                <a href="/tablet">Ouvrir l'interface tablette (micro + wake word)</a>
                <a href="/test">Tester le robot sans matériel</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@bp.route("/location", methods=["GET"])
def handle_location():
    """Retourne l'heure et la date actuelles"""
    return get_heure_date()


@bp.route("/test")
def robot_test_interface():
    """Interface de test web pour le robot Pepper"""
    return render_template('robot_test.html')
