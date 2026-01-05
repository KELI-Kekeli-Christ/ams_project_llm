"""
Service d'envoi d'emails pour notifier le gestionnaire des nouvelles réservations
"""
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, Dict

# Chemin du fichier de configuration
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
    "email_config.json"
)

# Configuration par défaut
DEFAULT_CONFIG = {
    "manager_email": "christlearn834@gmail.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "email_enabled": True
}


def load_email_config() -> Dict:
    """
    Charge la configuration email depuis le fichier JSON
    
    Returns:
        dict: Configuration email
    """
    # Créer le dossier config s'il n'existe pas
    config_dir = os.path.dirname(CONFIG_FILE)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    # Si le fichier n'existe pas, créer avec les valeurs par défaut
    if not os.path.exists(CONFIG_FILE):
        save_email_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Mettre à jour avec les valeurs par défaut si des clés manquent
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de la config email: {e}. Utilisation des valeurs par défaut.")
        return DEFAULT_CONFIG.copy()


def save_email_config(config: Dict):
    """
    Sauvegarde la configuration email dans le fichier JSON
    
    Args:
        config: Dictionnaire de configuration à sauvegarder
    """
    try:
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"✅ Configuration email sauvegardée dans {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de la config email: {e}")


def get_manager_email() -> str:
    """
    Récupère l'adresse email du gestionnaire depuis la configuration
    
    Returns:
        str: Adresse email du gestionnaire
    """
    config = load_email_config()
    return config.get("manager_email", DEFAULT_CONFIG["manager_email"])


def update_manager_email(email: str) -> bool:
    """
    Met à jour l'adresse email du gestionnaire
    
    Args:
        email: Nouvelle adresse email
    
    Returns:
        bool: True si la mise à jour a réussi
    """
    if not email or '@' not in email:
        return False
    
    config = load_email_config()
    config["manager_email"] = email
    save_email_config(config)
    return True


def send_reservation_email(
    reservation_id: str,
    client_name: str,
    client_prenom: str,
    type_chambre: str,
    date_arrivee: str,
    date_depart: str,
    qr_code_path: Optional[str] = None
) -> Dict:
    """
    Envoie un email au gestionnaire pour l'informer d'une nouvelle réservation
    
    Args:
        reservation_id: ID de la réservation
        client_name: Nom du client
        client_prenom: Prénom du client
        type_chambre: Type de chambre (simple, double, suite)
        date_arrivee: Date d'arrivée (format YYYY-MM-DD)
        date_depart: Date de départ (format YYYY-MM-DD)
        qr_code_path: Chemin vers le QR code (optionnel)
    
    Returns:
        dict: Résultat de l'envoi avec status ("success" ou "error") et message
    """
    config = load_email_config()
    
    # Vérifier si l'envoi d'email est activé
    if not config.get("email_enabled", True):
        return {
            "status": "disabled",
            "message": "L'envoi d'emails est désactivé dans la configuration"
        }
    
    manager_email = config.get("manager_email", DEFAULT_CONFIG["manager_email"])
    
    if not manager_email:
        return {
            "status": "error",
            "message": "Aucune adresse email de gestionnaire configurée"
        }
    
    # Si les identifiants SMTP ne sont pas configurés, on envoie juste un message d'avertissement
    smtp_username = config.get("smtp_username", "").strip()
    smtp_password = config.get("smtp_password", "").strip()
    
    if not smtp_username or not smtp_password:
        error_msg = f"Configuration SMTP incomplète. smtp_username='{smtp_username}', smtp_password={'*' * len(smtp_password) if smtp_password else 'vide'}"
        print(f"⚠️ SMTP non configuré. L'email ne peut pas être envoyé.")
        print(f"   {error_msg}")
        print(f"   Pour activer l'envoi d'emails, configurez smtp_username et smtp_password dans {CONFIG_FILE}")
        print(f"   Pour Gmail, smtp_username doit être votre adresse email complète (ex: votre.email@gmail.com)")
        return {
            "status": "error",
            "message": error_msg
        }
    
    try:
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 Nouvelle Réservation - {reservation_id}"
        msg['From'] = smtp_username
        msg['To'] = manager_email
        
        # Message pour la pièce jointe dans le HTML
        attachment_notice = ''
        if qr_code_path:
            attachment_notice = '<p style="margin-top: 15px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;"><strong>📎 Pièce jointe:</strong> Le QR code de la réservation est inclus en pièce jointe à cet email.</p>'
        
        # Corps du message en HTML
        html_body = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
              <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">
                🎉 Nouvelle Réservation Enregistrée
              </h2>
              
              <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="color: #27ae60; margin-top: 0;">Détails de la Réservation</h3>
                
                <table style="width: 100%; border-collapse: collapse;">
                  <tr>
                    <td style="padding: 8px; font-weight: bold; width: 40%;">ID Réservation:</td>
                    <td style="padding: 8px;">{reservation_id}</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 8px; font-weight: bold;">Client:</td>
                    <td style="padding: 8px;">{client_prenom} {client_name}</td>
                  </tr>
                  <tr>
                    <td style="padding: 8px; font-weight: bold;">Type de chambre:</td>
                    <td style="padding: 8px;">{type_chambre.capitalize()}</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 8px; font-weight: bold;">Date d'arrivée:</td>
                    <td style="padding: 8px;">{date_arrivee}</td>
                  </tr>
                  <tr>
                    <td style="padding: 8px; font-weight: bold;">Date de départ:</td>
                    <td style="padding: 8px;">{date_depart}</td>
                  </tr>
                </table>
                
                <p style="margin-top: 20px; padding: 15px; background-color: #e8f5e9; border-left: 4px solid #27ae60; border-radius: 4px;">
                  <strong>💡 Information:</strong> Cette réservation a été créée automatiquement via le système de réservation de l'hôtel.
                </p>
                {attachment_notice}
              </div>
              
              <div style="margin-top: 20px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 4px;">
                <p style="margin: 0; color: #1565c0;">
                  <strong>Date d'envoi:</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        # Partie texte du message (pour les clients email qui ne supportent pas HTML)
        text_body = f"""
Nouvelle Réservation Enregistrée

ID Réservation: {reservation_id}
Client: {client_prenom} {client_name}
Type de chambre: {type_chambre.capitalize()}
Date d'arrivée: {date_arrivee}
Date de départ: {date_depart}

Cette réservation a été créée automatiquement via le système de réservation de l'hôtel.
Date d'envoi: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
        """
        
        # Attacher les parties au message
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Ajouter le QR code en pièce jointe si disponible
        if qr_code_path:
            print(f"🔍 Recherche du QR code: {qr_code_path}")
            qr_file_path = None
            
            # Le chemin peut être relatif ou absolu
            # Si c'est relatif (commence par "app/static/qr/"), construire le chemin absolu
            if qr_code_path.startswith("app/static/qr/"):
                # Chemin relatif depuis le projet FastAPI (ams_project_llm)
                # Construire le chemin absolu depuis robot_hotel vers ams_project_llm
                current_file = os.path.abspath(__file__)  # Chemin absolu du fichier email.py
                current_dir = os.path.dirname(os.path.dirname(current_file))  # robot_hotel/
                parent_dir = os.path.dirname(current_dir)  # ams/
                fastapi_dir = os.path.join(parent_dir, "ams_project_llm")
                qr_file_path = os.path.join(fastapi_dir, qr_code_path)
                # Convertir en chemin absolu
                qr_file_path = os.path.abspath(qr_file_path)
                print(f"📍 Chemin relatif détecté, chemin absolu calculé: {qr_file_path}")
            elif os.path.isabs(qr_code_path):
                qr_file_path = qr_code_path
                print(f"📍 Chemin absolu fourni: {qr_file_path}")
            else:
                # Essayer le chemin tel quel, puis le convertir en absolu
                qr_file_path = os.path.abspath(qr_code_path)
                print(f"📍 Chemin converti en absolu: {qr_file_path}")
            
            if qr_file_path and os.path.exists(qr_file_path):
                try:
                    print(f"📎 Ajout du QR code en pièce jointe: {qr_file_path}")
                    with open(qr_file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    
                    # Nommer la pièce jointe avec le nom du fichier
                    qr_filename = os.path.basename(qr_file_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {qr_filename}'
                    )
                    
                    msg.attach(part)
                    print(f"✅ QR code ajouté en pièce jointe avec succès: {qr_filename}")
                except Exception as e:
                    print(f"❌ Erreur lors de l'ajout du QR code en pièce jointe: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"❌ Fichier QR code non trouvé: {qr_file_path} (chemin original: {qr_code_path})")
                if qr_file_path:
                    print(f"   Répertoire parent existe: {os.path.exists(os.path.dirname(qr_file_path))}")
        else:
            print("ℹ️ Aucun QR code à attacher (qr_code_path est None ou vide)")
        
        # Envoyer l'email
        smtp_server = config.get("smtp_server", DEFAULT_CONFIG["smtp_server"])
        smtp_port = config.get("smtp_port", DEFAULT_CONFIG["smtp_port"])
        
        print(f"📧 Envoi de l'email au gestionnaire ({manager_email})...")
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email envoyé avec succès à {manager_email}")
        
        return {
            "status": "success",
            "message": f"Email envoyé avec succès à {manager_email}",
            "manager_email": manager_email
        }
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Erreur d'authentification SMTP: {e}"
        print(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
    except smtplib.SMTPException as e:
        error_msg = f"Erreur SMTP: {e}"
        print(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
    except Exception as e:
        error_msg = f"Erreur lors de l'envoi de l'email: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": error_msg
        }

