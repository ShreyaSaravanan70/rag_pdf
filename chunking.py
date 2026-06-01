import re

def split_by_sentences(text, chunk_size=5):
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks = []
    chunk = []

    for sentence in sentences:
        chunk.append(sentence)

        if len(chunk) >= chunk_size:
            chunks.append(" ".join(chunk))
            chunk = []

    if chunk:
        chunks.append(" ".join(chunk))

    return chunks