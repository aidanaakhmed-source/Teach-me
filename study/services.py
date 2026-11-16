import copy
import json
import os
import urllib.request

from django.conf import settings

from .demo import DEMO_TEXT, DEMO_CARDS


class GenerationError(Exception):
    pass


def validate_cards(payload, text):
    if not isinstance(payload, dict):
        raise GenerationError("Жауап пішімі дұрыс емес: объект күтілді.")

    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise GenerationError("Жауапта 'cards' тізімі жоқ.")

    if not (3 <= len(cards) <= 8):
        raise GenerationError("Карточкалар саны 3 пен 8 аралығында болуы керек.")

    valid_cards = []
    seen_questions = set()

    for card in cards:
        if not isinstance(card, dict):
            continue

        if set(card.keys()) != {"question", "answer", "source_quote"}:
            continue

        question = card.get("question")
        answer = card.get("answer")
        source_quote = card.get("source_quote")

        if not all(isinstance(value, str) and value.strip() for value in (question, answer, source_quote)):
            continue

        question = question.strip()
        answer = answer.strip()
        source_quote = source_quote.strip()

        if len(question) > 300 or len(answer) > 1600 or len(source_quote) > 1600:
            continue

        if question.casefold() in seen_questions:
            continue

        if source_quote not in text:
            continue

        seen_questions.add(question.casefold())
        valid_cards.append({
            "question": question,
            "answer": answer,
            "source_quote": source_quote,
        })

    if not valid_cards:
        raise GenerationError("Жарамды карточкалар табылмады.")

    return valid_cards


def generate_cards(text):
    mode = getattr(settings, "TEACHME_MODE", "demo")

    if mode == "demo":
        if text == DEMO_TEXT:
            payload = copy.deepcopy({"cards": DEMO_CARDS})
            return validate_cards(payload, DEMO_TEXT)

        raise GenerationError("Демо-режимде тек демо-мәтінді пайдалануға болады.")

    if mode == "live":
        return _generate_live(text)

    raise GenerationError("Белгісіз режим.")


def _generate_live(text):
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")

    if not api_key or not model:
        raise GenerationError("LIVE режимі үшін GEMINI_API_KEY және GEMINI_MODEL қажет.")

    timeout_raw = os.environ.get("GEMINI_TIMEOUT_SECONDS", "25")
    try:
        timeout = float(timeout_raw)
    except ValueError:
        raise GenerationError("GEMINI_TIMEOUT_SECONDS сандық мән болуы керек.")

    if not (1 <= timeout <= 60):
        raise GenerationError("GEMINI_TIMEOUT_SECONDS 1 бен 60 аралығында болуы керек.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "cards": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING"},
                        "answer": {"type": "STRING"},
                        "source_quote": {"type": "STRING"},
                    },
                    "required": ["question", "answer", "source_quote"],
                },
                "minItems": 3,
                "maxItems": 8,
            }
        },
        "required": ["cards"],
    }

    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except Exception:
        raise GenerationError("Сыртқы API қатесі.")

    try:
        raw_json = (
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )
        payload = json.loads(raw_json)
    except (KeyError, IndexError, json.JSONDecodeError):
        raise GenerationError("API жауабынан JSON алу мүмкін болмады.")

    return validate_cards(payload, text)