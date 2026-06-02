import re

def split_by_headings(text):

    headings = [
        "SKILLS",
        "EXPERIENCE",
        "PROJECTS",
        "EDUCATION",
        "CERTIFICATIONS",
        "ROLES AND RESPONSIBILITIES",
        "WORK EXPERIENCE",
        "TECHNICAL SKILLS",
        "SUMMARY",
        "ACHIEVEMENTS",
        "HONOURS"
    ]

    pattern = r"(?m)^(" + "|".join(
        re.escape(h)
        for h in headings
    ) + r")\s*$"

    matches = list(
        re.finditer(
            pattern,
            text,
            re.IGNORECASE
        )
    )

    chunks = []

    if not matches:
        return [
            {
                "section": "FULL_DOCUMENT",
                "content": text
            }
        ]

    for i in range(len(matches)):

        start = matches[i].start()

        section_name = matches[i].group().strip()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        chunks.append({
            "section": section_name,
            "content": text[start:end].strip()
        })

    return chunks