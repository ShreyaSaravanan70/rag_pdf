from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(context: str, question: str):

    prompt = f"""You are a resume data extraction assistant.

Read the resume context below and answer the question asked.
Extract all relevant information from the context and return it.

Context:
{context}

Question:
{question}

Return your answer in this JSON format only:
{{"answer": "your answer here"}}

If the answer is a list of items, return:
{{"answer": ["item1", "item2", "item3"]}}

Do not say the context does not contain information. Extract whatever is relevant.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content

    return json.loads(content)

        

def extract_structured_resume(text):

    prompt = f"""
Extract the following information from the resume.

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

Rules:
- Return only JSON.
- No explanations.
- No markdown.
- If a field is missing, use an empty string or empty list.
- Extract all available items.

Resume:
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "name": "",
            "skills": [],
            "projects": [],
            "experience": [],
            "hackathons": [],
            "education": []
        }