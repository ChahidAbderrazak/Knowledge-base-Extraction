import os

from transformers import AutoTokenizer

tokenizer_name = "model/all-MiniLM-L6-v2"  # "model/Qwen2.5-1.5B-Instruct" #
examples = [
    "Hello world",
    "Montreal",
    "COVID-19",
    "strawberry",
    "The quick brown fox jumps over the lazy dog.",
]

print(f"Loading tokenizer {os.path.basename(tokenizer_name)}...")
tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

print(f"tokenizer type: {type(tokenizer)}")
print(f"tokenizer class: {tokenizer.__class__}")
print(f"backend tokenizer: {tokenizer.backend_tokenizer}")
print(f"vocab size: {tokenizer.vocab_size}")
print(f"vocab keys: {list(tokenizer.get_vocab().keys())}")

print("Tokenizing examples...")
for text in examples:
    ids = tokenizer.encode(text)
    tokens = tokenizer.convert_ids_to_tokens(ids)

    print("\nTEXT:", text)
    print("IDS:", ids)
    print("TOKENS:", tokens)
