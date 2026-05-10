from everycli.infra.yaml_loader import YamlLoader
from everycli.infra.tfidf_matcher import TFIDFMatcher
from pathlib import Path

DATA_DIR = Path("everycli/data/commands")
loader = YamlLoader(DATA_DIR)
scenarios = loader.load_all()

matcher = TFIDFMatcher()
matcher.fit(scenarios)

queries = [
    "je veux sauvegarder mon travail sans commiter",
    "je veux modifier un mot dans tout mes commit",
    "afficher les logs",
    "creer un nouveau projet",
    "annuler mon dernier commit"
]

for q in queries:
    res = matcher.match(q, top_k=1)
    if res:
        print(f"'{q}' -> {res[0][0].id} (Score: {res[0][1]})")
    else:
        print(f"'{q}' -> No match")
