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

    return response.choices[0].message.content

        
def extract_name(text):

    prompt = f"""
Extract only the candidate's full name from this resume.

Return only the name, nothing else.

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

    return response.choices[0].message.content.strip()