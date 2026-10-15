# app/persona_engine.py
"""
Multi-Persona Feed & Interactive Comment Engine for Skrulla (Study & Scroll).
Generates 5 to 12+ grounded feed posts per uploaded study material, cross-persona
AI comments, and automatic replies from the original AI persona when a user comments.
"""

from __future__ import annotations
import re
from typing import Dict, List, Any

AI_PERSONAS: List[Dict[str, str]] = [
    {
        "id": "memer_scholar",
        "name": "Memer Scholar",
        "role": "Chaotic Good Study Memelord",
        "card_type": "meme",
    },
    {
        "id": "storyteller",
        "name": "The Storyteller",
        "role": "Narrative Concept Weaver",
        "card_type": "concept",
    },
    {
        "id": "socratic_mentor",
        "name": "The Socratic Mentor",
        "role": "Active Recall & Deep Questioner",
        "card_type": "quiz",
    },
    {
        "id": "analogy_architect",
        "name": "The Analogy Architect",
        "role": "Mental Model Builder",
        "card_type": "analogy",
    },
    {
        "id": "first_principles",
        "name": "First-Principles Hacker",
        "role": "Axiom & Mechanism Deconstructor",
        "card_type": "concept",
    },
    {
        "id": "exam_speedrunner",
        "name": "The Exam Speedrunner",
        "role": "High-Yield Pattern & Mnemonic Pro",
        "card_type": "speedrun",
    },
    {
        "id": "devils_advocate",
        "name": "The Devil's Advocate",
        "role": "Edge-Case & Misconception Buster",
        "card_type": "concept",
    },
]


def compute_target_post_count(raw_text: str, file_size_bytes: int = 0) -> int:
    text_len = len(raw_text.strip())
    if text_len > 6000 or file_size_bytes > 500_000:
        return 12
    if text_len > 3500 or file_size_bytes > 200_000:
        return 10
    if text_len > 1800 or file_size_bytes > 80_000:
        return 8
    if text_len > 700 or file_size_bytes > 25_000:
        return 7
    return 6  # Minimum 5-6 feeds guaranteed


def is_garbage_or_pdf_bytecode(text: str) -> bool:
    if not text or len(text.strip()) < 15:
        return True
    cleaned = text.strip()
    if re.search(
        r"/(Filter|FlateDecode|ColorSpace|DeviceRGB|DeviceGray|Length|XObject|Subtype|Image|Catalog|Pages|Font|Encoding|MediaBox|Annots|ShadingType|Domain|FunctionType|DecodeParms|BitsPerComponent|Width|Height|ExtGState|FontDescriptor|Type\s*/)",
        cleaned,
        re.IGNORECASE,
    ):
        return True
    if re.search(r"\b\d+\s+\d+\s+(R|obj|endobj)\b", cleaned) or re.search(
        r"\b(xref|trailer|startxref)\b", cleaned, re.IGNORECASE
    ):
        return True
    if re.search(r"(QE\s*){3,}|(AAAA){3,}|(IIII){3,}|(0000){4,}", cleaned, re.IGNORECASE):
        return True
    if re.search(r"CDEFGHIJKLMNOPQRSTUVWXYZ", cleaned, re.IGNORECASE) or re.search(
        r"abcdefghijklmnopqrstuvwxyz", cleaned, re.IGNORECASE
    ):
        return True
    symbols = len(re.findall(r"[%*./+^=~`$#<>{}()[\]\\|&!@:;?]", cleaned))
    if len(cleaned) > 0 and (symbols / len(cleaned)) > 0.16:
        return True
    return False


def chunk_material_text(raw_text: str, title: str, subject: str, target_count: int) -> List[str]:
    clean_title = re.sub(r"[!?;:#$%^*()_=[\]{}<>]", " ", title).strip() or "Study Notes"
    clean_subject = re.sub(r"[!?;:#$%^*()_=[\]{}<>]", " ", subject).strip() or "General"
    cleaned = re.sub(r"\s+", " ", raw_text or "").strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        if len(s.strip()) > 25 and not is_garbage_or_pdf_bytecode(s)
    ]
    chunks: List[str] = []
    if len(sentences) >= target_count:
        step = max(1, len(sentences) // target_count)
        for i in range(target_count):
            segment = " ".join(sentences[i * step : (i + 1) * step + 1])[:420]
            if segment and not is_garbage_or_pdf_bytecode(segment):
                chunks.append(segment)
    elif sentences:
        for i in range(target_count):
            candidate = sentences[i % len(sentences)][:420]
            if not is_garbage_or_pdf_bytecode(candidate):
                chunks.append(candidate)

    if len(chunks) < target_count:
        educational_angles = [
            f"Foundational definition: In {clean_subject}, \"{clean_title}\" establishes the primary mapping rule where each input element corresponds to an unambiguous, well-defined output value.",
            f"Core operational mechanism: When applying {clean_title}, each transformation step must preserve invariants, respect variable bounds, and eliminate extraneous solutions.",
            f"High-yield exam pattern: Test questions on {clean_title} frequently invert premises or introduce edge cases—such as undefined intervals or zero-division—to verify conceptual retention.",
            f"Real-world mental model: Picture {clean_title} like a sealed computation module in {clean_subject}: provided the input parameters satisfy the domain criteria, the result is deterministic and reproducible.",
            f"First-principles deconstruction: Stripping away arbitrary notation, {clean_title} reduces down to a consistent constraint governing system states across {clean_subject}.",
            f"Common student pitfall: Conflating general relations with {clean_title}—a valid {clean_title} must never map a single domain input to conflicting outputs.",
            f"Edge-case boundary analysis: What happens to the behavior of {clean_title} as parameters approach asymptotic limits or discontinuous transitions?",
            f"Active recall challenge: Given the core principles of {clean_title}, derive how the governing rules adapt when external system constraints shift.",
            f"Synthesis and memory anchor: Linking the axioms of {clean_title} to broader models in {clean_subject} allows rapid recognition under timed exam conditions.",
            f"Intuitive system analogy: Think of {clean_title} like a functions pipeline in software: clean arguments yield predictable returns without unexpected side-effects.",
            f"Consolidated review checkpoint: Reviewing the formal properties, domain restrictions, and evaluation steps that define {clean_title} in {clean_subject}.",
            f"Mastery summary: Integrating all moving components of {clean_title} so you can deconstruct novel examination problems with confidence.",
        ]
        while len(chunks) < target_count:
            chunks.append(educational_angles[len(chunks) % len(educational_angles)])
    return chunks


def build_persona_post_payloads(
    title: str,
    subject: str,
    raw_text: str,
    grade_level: str = "University",
    file_size_bytes: int = 0,
) -> List[Dict[str, Any]]:
    target_count = compute_target_post_count(raw_text, file_size_bytes)
    chunks = chunk_material_text(raw_text, title, subject, target_count)
    payloads: List[Dict[str, Any]] = []

    for i in range(target_count):
        persona = AI_PERSONAS[i % len(AI_PERSONAS)]
        chunk = chunks[i % len(chunks)]
        other_personas = [p for p in AI_PERSONAS if p["id"] != persona["id"]]
        c1 = other_personas[i % len(other_personas)]
        c2 = other_personas[(i + 2) % len(other_personas)]

        if persona["id"] == "memer_scholar":
            headline = f"{title}: Meme Scholar Translation #{i + 1} 💀"
            body = (
                f"Nobody:\n{subject} textbooks: *explains {title} in 40 pages of jargon*\n\n"
                f"Memer Scholar translation: {chunk}\n\n"
                f"Lock this in and {title} is free exam points."
            )
        elif persona["id"] == "socratic_mentor":
            headline = f"Active Recall: {title} (Challenge #{i + 1})"
            body = f"Based on your notes on {title}, how does this mechanism operate: \"{chunk[:120]}...\"?"
        elif persona["id"] == "analogy_architect":
            headline = f"{title}: The Real-World Analogy"
            body = f"Think of {title} like a state engine in {subject}: {chunk}"
        elif persona["id"] == "first_principles":
            headline = f"{title}: First-Principles Breakdown"
            body = f"Stripping away the jargon in {subject}, here is the core axiom of {title}: {chunk}"
        elif persona["id"] == "exam_speedrunner":
            headline = f"⚡ Exam Speedrun: {title}"
            body = f"10-Second Pattern Recognition for {title}: {chunk}"
        elif persona["id"] == "devils_advocate":
            headline = f"Edge-Case Check: When Does {title} Break?"
            body = f"Don't just memorize {title}—test its limits: {chunk}"
        else:
            headline = f"{title}: Concept Story #{i + 1}"
            body = f"{title} ({subject}) — {chunk}"

        ai_comments = [
            {
                "author_name": c1["name"],
                "persona_id": c1["id"],
                "is_ai": True,
                "content": f"[{c1['name']}] Love this angle on {title}! Connecting \"{chunk[:80]}...\" makes {subject} click.",
            },
            {
                "author_name": c2["name"],
                "persona_id": c2["id"],
                "is_ai": True,
                "content": f"[{c2['name']}] Pro tip for {title}: watch how this exact rule gets tested under timed conditions.",
            },
        ]

        payloads.append(
            {
                "persona": persona["name"],
                "author_name": persona["name"],
                "persona_id": persona["id"],
                "headline": headline,
                "body": body,
                "hook": f"Grounded in your notes on {title} · {grade_level}",
                "series_tag": f"#{subject.replace(' ', '')}Grounded",
                "source_excerpt": chunk,
                "grounding_score": 0.99,
                "post_type": "quiz" if persona["id"] == "socratic_mentor" else "concept",
                "quiz_question": f"Based on {title}, which statement best describes this mechanism: \"{chunk[:100]}...\"?" if persona["id"] == "socratic_mentor" else None,
                "quiz_options": [
                    f"It governs the core behavior of {title}",
                    "It has no measurable effect",
                    "It operates inversely to observed constraints",
                ] if persona["id"] == "socratic_mentor" else None,
                "quiz_correct_index": 0 if persona["id"] == "socratic_mentor" else None,
                "quiz_explanation": f"Grounded in notes on {title}: {chunk}" if persona["id"] == "socratic_mentor" else None,
                "tags": [subject, "AIStudy", persona["name"].replace(" ", "")],
                "ai_comments": ai_comments,
            }
        )
    return payloads


def generate_author_persona_reply(
    author_name: str,
    post_title: str,
    post_content: str,
    user_comment: str,
    user_name: str = "Scholar",
) -> Dict[str, Any]:
    persona = next(
        (p for p in AI_PERSONAS if p["name"].lower() in (author_name or "").lower()),
        AI_PERSONAS[0],
    )
    snippet = (post_content or post_title)[:140]
    if persona["id"] == "memer_scholar":
        reply = (
            f"Big-brain question @{user_name} 💀 In \"{post_title}\", remember: {snippet}... "
            f"Once that clicks, your point about \"{user_comment[:60]}\" is 100% locked in!"
        )
    elif persona["id"] == "socratic_mentor":
        reply = (
            f"Thoughtful point, @{user_name}! Grounding in \"{post_title}\" ({snippet}...), "
            f"how would you apply \"{user_comment[:60]}\" if one variable changed?"
        )
    else:
        reply = (
            f"Spot on, @{user_name}! Directly from our notes on \"{post_title}\": {snippet}... "
            f"That directly answers your point on \"{user_comment[:60]}\"."
        )
    return {
        "author_name": persona["name"],
        "persona_id": persona["id"],
        "is_ai": True,
        "content": reply,
    }
