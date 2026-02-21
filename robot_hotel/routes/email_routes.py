"""
Routes Configuration Email
"""
from flask import Blueprint, request, jsonify
from services.email import load_email_config, save_email_config

bp = Blueprint('email', __name__)


@bp.route("/email/config", methods=["GET"])
def get_email_config():
    """Récupère la configuration email (sans mot de passe)"""
    config = load_email_config()
    safe_config = {
        "manager_email": config.get("manager_email", ""),
        "smtp_server": config.get("smtp_server", ""),
        "smtp_port": config.get("smtp_port", 587),
        "email_enabled": config.get("email_enabled", True),
        "smtp_username": config.get("smtp_username", ""),
        "smtp_password_configured": bool(config.get("smtp_password", ""))
    }
    return jsonify(safe_config)


@bp.route("/email/config", methods=["PUT", "POST"])
def update_email_config():
    """Met à jour la configuration email"""
    try:
        data = request.get_json()
        config = load_email_config()

        if "manager_email" in data:
            email = data["manager_email"].strip()
            if email and '@' in email:
                config["manager_email"] = email
            else:
                return jsonify({"success": False, "error": "Adresse email invalide"}), 400

        if "smtp_server" in data:
            config["smtp_server"] = data["smtp_server"].strip()
        if "smtp_port" in data:
            config["smtp_port"] = int(data["smtp_port"])
        if "smtp_username" in data:
            config["smtp_username"] = data["smtp_username"].strip()
        if "smtp_password" in data:
            password = data["smtp_password"].strip()
            if password and password != "*":
                config["smtp_password"] = password
        if "email_enabled" in data:
            config["email_enabled"] = bool(data["email_enabled"])

        save_email_config(config)
        return jsonify({
            "success": True,
            "message": "Configuration email mise à jour avec succès",
            "manager_email": config.get("manager_email")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
