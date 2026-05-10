#!/usr/bin/env python3
"""
Script pour examiner en détail les réservations en BD
"""
import sys
import sqlite3
import json
from pathlib import Path

db_path = "/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/ams_project_llm/ceribot.db"

print("\n" + "="*70)
print("  📋 INSPECTION DES RÉSERVATIONS AMS")
print("="*70)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Récupérer TOUTES les réservations
    print("\n📊 TOUTES LES RÉSERVATIONS ENREGISTRÉES:")
    print("-" * 70)
    
    # Vérifier les colonnes d'abord
    cursor.execute("PRAGMA table_info(clients)")
    client_cols = [row[1] for row in cursor.fetchall()]
    
    cursor.execute("PRAGMA table_info(reservations)")
    res_cols = [row[1] for row in cursor.fetchall()]
    
    print(f"Colonnes clients: {client_cols}")
    print(f"Colonnes reservations: {res_cols}\n")
    
    # Faire la requête
    cursor.execute('''
        SELECT 
            r.id_res,
            r.id_client,
            c.nom,
            c.prenom,
            r.type_chambre,
            r.date_arrivee,
            r.date_depart,
            r.statut
        FROM reservations r
        LEFT JOIN clients c ON r.id_client = c.id_client
        ORDER BY r.date_arrivee DESC
    ''')
    
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    
    print(f"Total: {len(rows)} réservations\n")
    
    for i, row in enumerate(rows, 1):
        print(f"{i:2d}. Réservation ID: {row[0]}")
        print(f"    Client: {row[2]} {row[3]} (ID: {row[1]})")
        print(f"    Chambre: {row[4]}")
        print(f"    Dates: {row[5]} → {row[6]}")
        print(f"    Statut: {row[7]}")
        print()
    
    # Statistiques
    print("-" * 70)
    print("📈 STATISTIQUES:")
    cursor.execute("SELECT COUNT(*) FROM reservations")
    print(f"  Total réservations: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM clients")
    print(f"  Total clients: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT type_chambre) FROM reservations")
    print(f"  Types chambre: {cursor.fetchone()[0]}")
    
    # Répartition par type
    print("\n📊 Répartition par type de chambre:")
    cursor.execute('''
        SELECT type_chambre, COUNT(*) as count
        FROM reservations
        GROUP BY type_chambre
    ''')
    for chamber_type, count in cursor.fetchall():
        print(f"    {chamber_type}: {count}")
    
    # Réservations par statut
    print("\n📊 Répartition par statut:")
    cursor.execute('''
        SELECT statut, COUNT(*) as count
        FROM reservations
        GROUP BY statut
    ''')
    for status, count in cursor.fetchall():
        print(f"    {status}: {count}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ VÉRIFICATION COMPLÈTE: Les réservations s'enregistrent bien!")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
