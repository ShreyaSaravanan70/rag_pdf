import ollama
import json

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


def extract_structured_resume(text: str):

    prompt = f"""
Extract structured data from this resume.

Return ONLY valid JSON.

Format:

{{
  "name": "",
  "skills": [],
  "projects": [],
  "experience": [],
  "hackathons": [],
  "education": []
}}

Resume:

{text}
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

    result = response["message"]["content"]

    print("\n===== RAW LLM OUTPUT =====")
    print(result)
    print("=========================\n")

    try:
        return json.loads(result)

    except Exception as e:

        print("JSON ERROR:", e)

        return {
            "name": "",
            "skills": [],
            "projects": [],
            "experience": [],
            "hackathons": [],
            "education": []
        }
            