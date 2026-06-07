import time

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from transformers import AutoModel, AutoTokenizer
from xgboost import XGBClassifier

# =========================
# CONFIG
# =========================
MODEL_NAME = "model/bge-base-en-v1.5"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MAX_CHUNK = 512
OVERLAP = 64

TARGET_IDS = [1, 2, 6]  # cs.CV, cs.AI, cs.PL

LABEL_MAP = {1: 0, 2: 1, 6: 2}

NUM_CLASSES = 3


print(f"[INFO] Device: {DEVICE}")


# =========================
# MODEL
# =========================
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
encoder = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
encoder.eval()

HIDDEN = encoder.config.hidden_size


# =========================
# POOLING
# =========================
def mean_pool(last_hidden, mask):
    mask = mask.unsqueeze(-1).expand(last_hidden.size()).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)


# =========================
# DATASET LOADER (FIXED)
# =========================
def load_data(max_samples=150):

    ds = load_dataset("ccdv/arxiv-classification")

    per_class = max_samples // len(TARGET_IDS)

    counts = {k: 0 for k in TARGET_IDS}

    texts = []
    labels = []

    for item in ds["train"]:
        y = item["label"]

        if y not in TARGET_IDS:
            continue

        if counts[y] >= per_class:
            continue

        texts.append(item["text"])
        labels.append(LABEL_MAP[y])

        counts[y] += 1

        if len(texts) >= max_samples:
            break

    print("\n[INFO] Class distribution:")
    print("cs.CV:", counts[1])
    print("cs.AI:", counts[2])
    print("cs.PL:", counts[6])

    return texts, labels


# =========================
# CHUNKING
# =========================
def chunk_text(text):
    tokens = tokenizer.encode(text, add_special_tokens=False)

    step = MAX_CHUNK - OVERLAP
    chunks = []

    for i in range(0, len(tokens), step):
        chunks.append(tokens[i : i + MAX_CHUNK])

    return chunks


# =========================
# ENCODE CHUNK
# =========================
def encode_chunk(tokens):
    input_ids = torch.tensor([tokens], dtype=torch.long).to(DEVICE)
    mask = torch.ones_like(input_ids)

    with torch.no_grad():
        out = encoder(input_ids=input_ids, attention_mask=mask)

    emb = mean_pool(out.last_hidden_state, mask).squeeze(0)

    return emb


# =========================
# TRUNCATION EMBEDDING
# =========================
def embed_single(text):

    tokens = tokenizer(text, truncation=True, max_length=MAX_CHUNK, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        out = encoder(**tokens)

    emb = mean_pool(out.last_hidden_state, tokens["attention_mask"]).squeeze(0)

    return F.normalize(emb, dim=-1).cpu().numpy()


# =========================
# MAX POOLING CHUNK EMBEDDING
# =========================
def embed_max_pool(text):

    chunks = chunk_text(text)

    embs = [encode_chunk(c) for c in chunks]
    embs = torch.stack(embs)

    doc = torch.max(embs, dim=0).values

    return F.normalize(doc, dim=-1).cpu().numpy()


# =========================
# ATTENTION POOLING (simple norm-based)
# =========================
def embed_attention_pool(text):

    chunks = chunk_text(text)

    embs = [encode_chunk(c) for c in chunks]
    embs = torch.stack(embs)

    scores = torch.norm(embs, dim=1)
    weights = torch.softmax(scores, dim=0).unsqueeze(1)

    doc = torch.sum(weights * embs, dim=0)

    return F.normalize(doc, dim=-1).cpu().numpy()


# =========================
# FEATURE BUILDER
# =========================
def build_features(fn, texts):
    return np.array([fn(t) for t in texts])


# =========================
# EXPERIMENT RUNNER
# =========================
def run_experiment(name, fn, texts, labels):

    print("\n========================")
    print(name)
    print("========================")

    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42, stratify=labels)

    # safety check
    assert len(set(y_train)) == NUM_CLASSES, f"Missing classes in train: {set(y_train)}"

    start = time.time()

    Xtr = build_features(fn, X_train)
    Xte = build_features(fn, X_test)

    clf = XGBClassifier(
        objective="multi:softprob",
        num_class=NUM_CLASSES,
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="mlogloss",
    )

    clf.fit(Xtr, y_train)
    preds = clf.predict(Xte)

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro")

    print(f"Accuracy: {acc:.4f}")
    print(f"F1 macro: {f1:.4f}")
    print(f"Time: {time.time() - start:.2f}s")


# =========================
# MAIN
# =========================
def main():

    texts, labels = load_data(max_samples=150)

    print("\n[INFO] Dataset size:", len(texts))
    print("[INFO] Classes:", sorted(set(labels)))

    # sanity check lengths
    lengths = [len(tokenizer.encode(t, add_special_tokens=False)) for t in texts[:20]]

    print("\n[INFO] Token stats (sample):")
    print("min:", min(lengths))
    print("max:", max(lengths))
    print("avg:", sum(lengths) / len(lengths))

    run_experiment("TRUNCATION", embed_single, texts, labels)
    run_experiment("MAX POOLING", embed_max_pool, texts, labels)
    run_experiment("ATTENTION POOLING", embed_attention_pool, texts, labels)


if __name__ == "__main__":
    main()
