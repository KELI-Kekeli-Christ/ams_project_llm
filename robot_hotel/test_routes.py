#!/usr/bin/env python3
"""
Script pour vérifier que toutes les routes de l'API sont bien enregistrées
"""
import sys
import os

# Ajouter le dossier au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import app
    
    print("=" * 60)
    print("Vérification des routes de l'API Flask")
    print("=" * 60)
    print()
    
    # Lister toutes les routes
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': sorted(rule.methods - {'HEAD', 'OPTIONS'}),
            'path': rule.rule
        })
    
    # Trier par path
    routes.sort(key=lambda x: x['path'])
    
    # Routes face detection à vérifier
    face_routes = [
        '/face/detect',
        '/face/register',
        '/face/persons',
        '/face/persons/<name>',
        '/face/stream/start',
        '/face/stream/stop',
        '/face/stream/detections'
    ]
    
    print(f"Total de routes trouvées: {len(routes)}")
    print()
    print("Routes de détection faciale:")
    print("-" * 60)
    
    found_routes = []
    for face_route in face_routes:
        # Normaliser pour la comparaison (enlever les <name>)
        pattern = face_route.replace('<name>', '')
        found = False
        for route in routes:
            if pattern in route['path'] or route['path'] == face_route:
                found = True
                found_routes.append(face_route)
                print(f"✅ {route['path']:30} {', '.join(route['methods'])}")
                break
        if not found:
            print(f"❌ {face_route:30} NON TROUVÉE")
    
    print()
    print("=" * 60)
    if len(found_routes) == len(face_routes):
        print("✅ Toutes les routes de détection faciale sont enregistrées!")
    else:
        print(f"⚠️  {len(found_routes)}/{len(face_routes)} routes trouvées")
    print("=" * 60)
    print()
    print("Toutes les routes disponibles:")
    print("-" * 60)
    for route in routes:
        print(f"{route['path']:40} {', '.join(route['methods'])}")

except Exception as e:
    print(f"❌ Erreur lors du chargement de l'application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

