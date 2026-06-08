# import re

# def split_by_headings(text):

#     headings = [
#         "SKILLS",
#         "MY SKILLS",
#         "EXPERIENCE",
#         "PROJECTS",
#         "EDUCATION",
#         "ACADEMIC BACKGROUND",
#         "CERTIFICATIONS",
#         "ROLES AND RESPONSIBILITIES",
#         "WORK EXPERIENCE",
#         "TECHNICAL SKILLS",
#         "SUMMARY",
#         "ACHIEVEMENTS",
#         "HONOURS"
#     ]

#     # flexible match: allows ":" "-" spaces after heading
#     pattern = r"(?im)^(" + "|".join(
#         re.escape(h) for h in headings
#     ) + r")\s*[:\-]?\s*$"

#     matches = list(re.finditer(pattern, text))

#     chunks = []

#     if not matches:
#         return [{"section": "FULL_DOCUMENT", "content": text.strip()}]

#     for i in range(len(matches)):

#         section_name = matches[i].group(1).strip()

#         # start AFTER heading line (IMPORTANT FIX)
#         start = matches[i].end()

#         if i + 1 < len(matches):
#             end = matches[i + 1].start()
#         else:
#             end = len(text)

#         content = text[start:end].strip()

#         chunks.append({
#             "section": section_name,
#             "content": content
#         })

#     return chunks

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