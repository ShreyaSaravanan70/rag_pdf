import ollama
import json

def ask_llm(context: str, question: str):

    prompt = f"""
You are a STRICT extraction engine.

You are NOT allowed to explain or summarize.

RULES:
- ONLY use information from context
- DO NOT summarize
- DO NOT rephrase
- DO NOT omit items

OUTPUT RULE:
Return ONLY valid JSON in this format:

{{
  "answer": "exact text OR full list from context"
}}

If multiple values exist:
{{
  "answer": ["value1", "value2", "value3"]
}}

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
            