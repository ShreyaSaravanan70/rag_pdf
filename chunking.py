def split_by_words(text, chunk_size=150, overlap=30):

    words = text.split()

    chunks = []

    step = chunk_size - overlap

    for i in range(0, len(words), step):

        chunk_words = words[i:i + chunk_size]

        if not chunk_words:
            continue

        chunks.append({
            "content": " ".join(chunk_words)
        })

    return chunks