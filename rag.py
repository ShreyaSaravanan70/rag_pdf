import ollama

def ask_llm(context: str, question: str):

    prompt = f"""
You are a PDF assistant.

Use ONLY the information present in the context.

If the answer exists in the context, answer clearly.

If the answer is not present, say:
"Information not found in the uploaded documents."

Context:
{context}

Question:
{question}

Answer:
"""

    response = ollama.chat(
        model="gemma:2b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]