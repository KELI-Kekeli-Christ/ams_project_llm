#!/usr/bin/env python3
"""
Script de diagnostic: Vérifier que les réservations s'enregistrent dans la BD
- Vérifier la BD temporaire (temp_reservations.db)
- Vérifier l'API AMS
- Afficher l'état des réservations
"""
import sys
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
import requests

sys.path.insert(0, str(Path(__file__).parent))

from services.make_reservation import TEMP_DB_PATH, init_temp_db, RESERVATION_API_URL

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def check_temp_database():
    """Vérifier la BD temporaire des réservations"""
    print_header("📊 VÉRIFICATION BD TEMPORAIRE (temp_reservations.db)")
    
    if not os.path.exists(TEMP_DB_PATH):
        print(f"❌ BD temporaire non trouvée: {TEMP_DB_PATH}")
        return False
    
    print(f"✅ BD trouvée: {TEMP_DB_PATH}")
    
    try:
        # Initialiser la BD
        init_temp_db()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        # Vérifier les réservations extraites
        print(f"\n📋 TABLE: extracted_reservations")
        print("-" * 70)
        cursor.execute('SELECT COUNT(*) FROM extracted_reservations')
        count = cursor.fetchone()[0]
        print(f"Nombre d'entrées: {count}")
        
        if count > 0:
            cursor.execute('''
                SELECT session_id, data, created_at, expires_at 
                FROM extracted_reservations 
                ORDER BY created_at DESC 
                LIMIT 5
            ''')
            for session_id, data_json, created_at, expires_at in cursor.fetchall():
                data = json.loads(data_json)
                print(f"\n  Session: {session_id}")
                print(f"    Nom: {data.get('nom')} {data.get('prenom')}")
                print(f"    Chambre: {data.get('type_chambre')}")
                print(f"    Arrivée: {data.get('date_arrivee')}")
                print(f"    Départ: {data.get('date_depart')}")
                print(f"    Créée: {created_at}")
                print(f"    Expire: {expires_at}")
        
        # Vérifier les réservations validées
        print(f"\n📋 TABLE: validated_reservations")
        print("-" * 70)
        cursor.execute('SELECT COUNT(*) FROM validated_reservations')
        count = cursor.fetchone()[0]
        print(f"Nombre d'entrées: {count}")
        
        if count > 0:
            cursor.execute('''
                SELECT session_id, data, created_at, expires_at 
                FROM validated_reservations 
                ORDER BY created_at DESC 
                LIMIT 5
            ''')
            for session_id, data_json, created_at, expires_at in cursor.fetchall():
                data = json.loads(data_json)
                print(f"\n  Session: {session_id}")
                print(f"    Nom: {data.get('nom')} {data.get('prenom')}")
                print(f"    Chambre: {data.get('type_chambre')}")
                print(f"    Arrivée: {data.get('date_arrivee')}")
                print(f"    Départ: {data.get('date_depart')}")
                print(f"    Créée: {created_at}")
                print(f"    Expire: {expires_at}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lecture BD: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_ams_api():
    """Vérifier l'API AMS et les réservations"""
    print_header("🌐 VÉRIFICATION API AMS")
    
    print(f"API URL: {RESERVATION_API_URL}")
    
    try:
        # Tester la connexion
        response = requests.get(f"{RESERVATION_API_URL}/docs", timeout=5)
        print(f"✅ API AMS accessible ({response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"❌ API AMS non accessible à {RESERVATION_API_URL}")
        print("   Assurez-vous que le serveur AMS est lancé:")
        print("   cd /home/christ/Downloads/Telegram\\ Desktop/M1/M1\\ Avignon\\ universite/Ams\\ projet/ams/ams_project_llm")
        print("   python3 main.py")
        return False
    except Exception as e:
        print(f"❌ Erreur accès API: {e}")
        return False
    
    # Essayer de récupérer les réservations
    print(f"\n📋 Tentative de récupération des réservations...")
    try:
        # Supposer qu'il existe une route /reservations ou /reservations/list
        endpoints = [
            "/reservations",
            "/reservations/list",
            "/reservation/list",
            "/clients"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{RESERVATION_API_URL}{endpoint}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n✅ Endpoint trouvé: {endpoint}")
                    print(f"   Réponse: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
                    return True
            except:
                pass
        
        print("⚠️ Pas d'endpoint de liste trouvé")
        print("   Endpoints testés: " + ", ".join(endpoints))
        
    except Exception as e:
        print(f"⚠️ Erreur: {e}")
    
    return False

def check_ams_database():
    """Vérifier la BD du serveur AMS directement"""
    print_header("💾 VÉRIFICATION BD AMS")
    
    # Chercher la BD AMS
    ams_paths = [
        "/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/ams_project_llm/ceribot.db",
        "/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/ams_project_llm/reservations.db",
        "/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/ams_project_llm/app.db",
        "/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/ams_project_llm/database.db",
    ]
    
    db_path = None
    for path in ams_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ BD AMS non trouvée")
        print(f"   Chemins testés:")
        for p in ams_paths:
            print(f"     - {p}")
        return False
    
    print(f"✅ BD trouvée: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lister toutes les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📊 Tables trouvées: {len(tables)}")
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} lignes")
        
        # Chercher une table de réservations
        reservation_tables = [t[0] for t in tables if 'reserv' in t[0].lower()]
        client_tables = [t[0] for t in tables if 'client' in t[0].lower()]
        
        if reservation_tables:
            print(f"\n📋 TABLE DE RÉSERVATIONS: {reservation_tables[0]}")
            print("-" * 70)
            cursor.execute(f"SELECT * FROM {reservation_tables[0]} ORDER BY rowid DESC LIMIT 5")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            print(f"Colonnes: {', '.join(columns)}")
            print(f"Nombre total de réservations: {len(rows)}")
            
            for row in rows:
                print(f"\n  Réservation:")
                for col, val in zip(columns, row):
                    print(f"    {col}: {val}")
        
        elif client_tables:
            print(f"\n👤 TABLE CLIENTS: {client_tables[0]}")
            print("-" * 70)
            cursor.execute(f"SELECT * FROM {client_tables[0]} ORDER BY rowid DESC LIMIT 3")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            print(f"Colonnes: {', '.join(columns)}")
            print(f"Nombre total de clients: {len(rows)}")
            
            for row in rows:
                print(f"\n  Client:")
                for col, val in zip(columns, row):
                    print(f"    {col}: {val}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lecture BD: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*70)
    print("  🧪 DIAGNOSTIC: VÉRIFICATION DES RÉSERVATIONS EN BD")
    print("="*70)
    
    results = {
        "BD Temporaire": check_temp_database(),
        "API AMS": check_ams_api(),
        "BD AMS": check_ams_database(),
    }
    
    print_header("📊 RÉSUMÉ DU DIAGNOSTIC")
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    all_ok = all(results.values())
    
    print(f"\n{'='*70}")
    if all_ok:
        print("✅ TOUS LES TESTS PASSENT - Système de réservation OK!")
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ - Voir détails ci-dessus")
    print(f"{'='*70}\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
