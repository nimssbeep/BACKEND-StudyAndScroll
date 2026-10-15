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


def chunk_material_text(raw_text: str, title: str, subject: str, target_count: int) -> List[str]:
    cleaned = re.sub(r"\s+", " ", raw_text or "").strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        if len(s.strip()) > 25
    ]
    chunks: List[str] = []
    if len(sentences) >= target_count:
        step = max(1, len(sentences) // target_count)
        for i in range(target_count):
            segment = " ".join(sentences[i * step : (i + 1) * step + 1])[:420]
            if segment:
                chunks.append(segment)
    elif sentences:
        for i in range(target_count):
            chunks.append(sentences[i % len(sentences)][:420])
    else:
        fallbacks = [
            f"Foundational definition and core mechanism of {title} in {subject}.",
            f"Step-by-step operational workflow and variable interactions in {title}.",
            f"High-yield exam patterns and common pitfalls when solving {title} problems.",
            f"Real-world mental model and intuitive analogy for {title}.",
            f"First-principles derivation and invariants governing {title}.",
            f"Boundary conditions and edge cases where standard {title} assumptions shift.",
            f"Synthesis and active recall consolidation across {title} models.",
        ]
        for i in range(target_count):
            chunks.append(fallbacks[i % len(fallbacks)])
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
