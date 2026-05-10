import time
print("Starting...")
t0 = time.time()
from sentence_transformers import SentenceTransformer
t1 = time.time()
print(f"Import time: {t1-t0:.2f}s")
model = SentenceTransformer("all-MiniLM-L6-v2")
t2 = time.time()
print(f"Load model time: {t2-t1:.2f}s")
model.encode(["test"])
t3 = time.time()
print(f"Encode 1 string time: {t3-t2:.2f}s")
