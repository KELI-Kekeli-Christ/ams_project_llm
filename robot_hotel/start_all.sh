#!/bin/bash

###############################################################################
# Script unique pour lancer tous les services Robot Hotel
# - Flask API (port 5000)
# - FastAPI avec Uvicorn (port 8000, optionnel)
# - Streamlit Admin (port 8501)
###############################################################################

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/env"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/services.pid"

# Ports
FLASK_PORT=5000
FASTAPI_PORT=8000
STREAMLIT_PORT=8501

# Créer le dossier de logs
mkdir -p "$LOG_DIR"

# Fonctions utilitaires
print_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Vérifier si un port est utilisé
check_port() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Arrêter les services
stop_services() {
    print_info "Arrêt des services..."
    
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p $pid > /dev/null 2>&1; then
                kill $pid 2>/dev/null
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    for port in $FLASK_PORT $FASTAPI_PORT $STREAMLIT_PORT; do
        if check_port $port; then
            lsof -ti:$port | xargs kill -9 2>/dev/null
        fi
    done
    
    pkill -f "streamlit run" 2>/dev/null
    print_success "Services arrêtés"
}

# Gérer Ctrl+C
trap stop_services SIGINT SIGTERM

# Vérifier l'environnement virtuel
activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Environnement virtuel non trouvé: $VENV_DIR"
        exit 1
    fi
    source "$VENV_DIR/bin/activate" || exit 1
    print_success "Environnement virtuel activé"
}

# Vérifier les dépendances
check_deps() {
    python -c "import flask" 2>/dev/null || { print_error "Flask non installé"; exit 1; }
    python -c "import streamlit" 2>/dev/null || { print_error "Streamlit non installé"; exit 1; }
    print_success "Dépendances OK"
}

# Vérifier les ports
check_ports() {
    for port in $FLASK_PORT $FASTAPI_PORT $STREAMLIT_PORT; do
        if check_port $port; then
            print_warning "Port $port déjà utilisé"
            read -p "Arrêter les services existants? (o/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[OoYy]$ ]]; then
                stop_services
                sleep 2
            else
                exit 1
            fi
            break
        fi
    done
}

# Démarrer Flask
start_flask() {
    print_info "Démarrage Flask API (port $FLASK_PORT)..."
    cd "$SCRIPT_DIR"
    nohup python main.py > "$LOG_DIR/flask.log" 2>&1 &
    echo $! >> "$PID_FILE"
    sleep 3
    if check_port $FLASK_PORT; then
        print_success "Flask démarré → http://localhost:$FLASK_PORT"
    else
        print_error "Flask n'a pas démarré. Logs: $LOG_DIR/flask.log"
    fi
}

# Démarrer FastAPI
start_fastapi() {
    FASTAPI_DIR="$(dirname "$SCRIPT_DIR")/ams_project_llm"
    FASTAPI_PATH="$FASTAPI_DIR/main.py"
    FASTAPI_VENV="$FASTAPI_DIR/env"
    
    if [ ! -f "$FASTAPI_PATH" ]; then
        print_warning "FastAPI non trouvé (ignoré)"
        return 0
    fi
    
    # Vérifier et activer l'environnement virtuel de FastAPI
    if [ ! -d "$FASTAPI_VENV" ]; then
        print_warning "Environnement virtuel FastAPI non trouvé: $FASTAPI_VENV (ignoré)"
        return 0
    fi
    
    print_info "Activation de l'environnement virtuel FastAPI..."
    source "$FASTAPI_VENV/bin/activate"
    
    if ! python -c "import uvicorn" 2>/dev/null; then
        print_warning "Uvicorn non installé dans l'env FastAPI (ignoré)"
        # Réactiver l'env robot_hotel
        source "$VENV_DIR/bin/activate"
        return 0
    fi
    
    print_info "Démarrage FastAPI avec Uvicorn (port $FASTAPI_PORT)..."
    cd "$FASTAPI_DIR"
    nohup python -m uvicorn main:app --host 0.0.0.0 --port $FASTAPI_PORT --reload > "$LOG_DIR/fastapi.log" 2>&1 &
    FASTAPI_PID=$!
    echo $FASTAPI_PID >> "$PID_FILE"
    
    # Réactiver l'env robot_hotel pour les autres services
    source "$VENV_DIR/bin/activate"
    
    sleep 3
    if check_port $FASTAPI_PORT; then
        print_success "FastAPI démarré → http://localhost:$FASTAPI_PORT"
    else
        print_error "FastAPI n'a pas démarré. Logs: $LOG_DIR/fastapi.log"
    fi
}

# Démarrer Streamlit
start_streamlit() {
    print_info "Démarrage Streamlit Admin (port $STREAMLIT_PORT)..."
    cd "$SCRIPT_DIR/admin"
    nohup streamlit run app.py --server.port $STREAMLIT_PORT --server.headless true > "$LOG_DIR/streamlit.log" 2>&1 &
    echo $! >> "$PID_FILE"
    sleep 4
    if check_port $STREAMLIT_PORT; then
        print_success "Streamlit démarré → http://localhost:$STREAMLIT_PORT"
    else
        print_error "Streamlit n'a pas démarré. Logs: $LOG_DIR/streamlit.log"
    fi
}

# Affichage du résumé
show_summary() {
    echo
    echo "======================================================================"
    echo -e "${GREEN}🚀 Services démarrés!${NC}"
    echo "======================================================================"
    echo
    echo -e "${CYAN}URLs:${NC}"
    echo "  • Flask API:      http://localhost:$FLASK_PORT"
    echo "  • Flask Docs:     http://localhost:$FLASK_PORT/api-docs"
    FASTAPI_DIR="$(dirname "$SCRIPT_DIR")/ams_project_llm"
    if [ -f "$FASTAPI_DIR/main.py" ] && [ -d "$FASTAPI_DIR/env" ]; then
        echo "  • FastAPI:        http://localhost:$FASTAPI_PORT"
        echo "  • FastAPI Docs:   http://localhost:$FASTAPI_PORT/docs"
    fi
    echo "  • Streamlit:      http://localhost:$STREAMLIT_PORT"
    echo
    echo -e "${YELLOW}Logs: $LOG_DIR/${NC}"
    echo
    echo -e "${YELLOW}Arrêt: Ctrl+C ou ./start_all.sh stop${NC}"
    echo
    echo "======================================================================"
}

# Fonction principale
main() {
    clear
    
    # Commande stop
    if [ "$1" = "stop" ]; then
        stop_services
        exit 0
    fi
    
    echo "======================================================================"
    echo -e "${BLUE}🤖 Robot Hotel - Démarrage des Services${NC}"
    echo "======================================================================"
    echo
    
    check_ports
    activate_venv
    check_deps
    
    echo
    echo -e "${BLUE}Démarrage des services...${NC}"
    echo
    
    start_flask
    start_fastapi
    start_streamlit
    
    show_summary
    
    echo -e "${CYAN}Services en cours... Appuyez sur Ctrl+C pour arrêter${NC}"
    wait
}

# Exécution
main "$@"

