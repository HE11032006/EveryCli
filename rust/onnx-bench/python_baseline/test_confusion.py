"""
Teste le daemon Rust sur le jeu de confusion_set.yaml
Version socket avec reconnexion à chaque requête
"""

import json
import socket
import yaml
import os
import time

# Définir le chemin de base
base_dir = r"C:\EveryCli"

# Charger le fichier de test
file_path = os.path.join(base_dir, "eval", "confusion_set.yaml")

with open(file_path, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

cases = data["cases"]
passed = 0
failed = 0
results = []

print(f"Test de {len(cases)} requêtes sur le daemon Rust...\n")

for case in cases:
    query = case["query"]
    expected = case["expected_id"]
    
    try:
        # Ouvrir une nouvelle connexion à chaque requête
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", 51821))
        
        # Construire la requête JSON
        request = json.dumps({
            "action": "search",
            "query": query,
            "top_k": 1
        })
        
        # Envoyer la requête
        sock.send((request + "\n").encode())
        
        # Recevoir la réponse
        response = sock.recv(4096).decode()
        sock.close()
        
        result = json.loads(response)
        
        if result.get("ok") and result.get("results") and result["results"][0]["id"] == expected:
            passed += 1
            print(f"✅ {query[:50]}...")
        else:
            failed += 1
            actual = result["results"][0]["id"] if result.get("results") else "aucun"
            results.append(f"❌ {query[:50]}... -> attendu: {expected}, obtenu: {actual}")
            print(f"❌ {query[:50]}... -> {actual}")
    except Exception as e:
        failed += 1
        results.append(f"❌ {query[:50]}... -> erreur: {e}")
        print(f"❌ {query[:50]}... -> erreur")

print(f"\n=== Résultats ===")
print(f"✅ Passés: {passed}/{len(cases)}")
print(f"❌ Échecs: {failed}/{len(cases)}")
print(f"Taux de succès: {passed/len(cases)*100:.1f}%")

if results:
    print("\nDétails des échecs (premiers 10):")
    for r in results[:10]:
        print(f"  {r}")