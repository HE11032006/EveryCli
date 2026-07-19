"""
benchmark_speed.py — Mesure la latence du moteur de recherche EveryCLI.

Teste si chaque requête est traitée en moins de 100ms (hors chargement initial).
Exécuter depuis la racine du projet, avec le venv activé :

    python tools/benchmark_speed.py
"""

import sys, io
# Force UTF-8 output on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import time
from pathlib import Path

# ── Setup ───────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "everycli" / "data" / "commands"

from everycli.core.search_engine import SearchEngine
from everycli.infra.yaml_loader import YamlLoader
from everycli.infra.hybrid_matcher import HybridMatcher
from everycli.infra.os_resolver import OSResolver
from everycli.infra.context_detector import ProjectContextDetector

print("⚙️  Chargement du moteur...")
t0 = time.perf_counter()
matcher = HybridMatcher(semantic_weight=0.85)
engine = SearchEngine(
    loader=YamlLoader(DATA_DIR),
    matcher=matcher,
    os_resolver=OSResolver(),
    context_detector=ProjectContextDetector(),
)
engine.boot()
boot_time = (time.perf_counter() - t0) * 1000
print(f"✅ Démarrage (cold boot) : {boot_time:.1f}ms\n")

# ── Requêtes de test ────────────────────────────────────────────────────────
QUERIES = [
    "lance tous les containers en arriere plan",
    "annule mon dernier commit sans perdre les modifs",
    "supprimer une image docker",
    "voir les logs en temps réel",
    "installer les dépendances npm",
    "créer une branche git",
    "push sur origin main",
    "lister les containers en cours",
    "creer un environnement virtuel python",
    "revenir au commit précédent",
]

TARGET_MS = 100
results_ok = 0
results_fail = 0

print(f"{'Requête':<50} {'Temps':>8} {'Résultat':>10}")
print("-" * 72)

for query in QUERIES:
    t_start = time.perf_counter()
    hits = engine.search(query, top_k=1)
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    top_id = hits[0].scenario.id if hits else "—"
    status = "✅ OK" if elapsed_ms < TARGET_MS else "❌ LENT"
    if elapsed_ms < TARGET_MS:
        results_ok += 1
    else:
        results_fail += 1

    print(f"{query:<50} {elapsed_ms:>6.1f}ms  {status}  → {top_id}")

# ── Résumé ──────────────────────────────────────────────────────────────────
print("-" * 72)
total = results_ok + results_fail
print(f"\n📊 Résultat : {results_ok}/{total} requêtes sous {TARGET_MS}ms")

# Warm path average (run all again for stable timing)
print("\n⏱️  Mesure du warm-path (moyenne sur 3 passes)...")
times = []
for _ in range(3):
    for q in QUERIES:
        t = time.perf_counter()
        engine.search(q, top_k=1)
        times.append((time.perf_counter() - t) * 1000)

avg = sum(times) / len(times)
p95 = sorted(times)[int(len(times) * 0.95)]
p99 = sorted(times)[int(len(times) * 0.99)]
print(f"  Moyenne : {avg:.1f}ms")
print(f"  P95     : {p95:.1f}ms")
print(f"  P99     : {p99:.1f}ms")

if results_fail == 0:
    print(f"\n🎉 Toutes les requêtes sont sous {TARGET_MS}ms !")
else:
    print(f"\n⚠️  {results_fail} requête(s) dépassent {TARGET_MS}ms.")
