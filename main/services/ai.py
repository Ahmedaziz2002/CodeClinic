import logging

from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import types

from main.models import Message, Problem, Thread

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Code Clinic's AI programming assistant. "
    "Give accurate, complete, and practical help for coding questions. "
    "Write like ChatGPT/Codex: a short natural explanation first, then a short step list, "
    "then a single fenced code block if code is needed, then a one-line summary. "
    "Do not use labels like 'Explanation:' or 'Steps:' or 'Summary:'. "
    "Keep answers concise but complete, and finish every response."
)

VALID_TOPICS = {
    "Arrays",
    "Strings",
    "Math",
    "Binary Search",
    "Graphs",
    "Dynamic Programming",
    "Greedy",
    "Optimization",
    "Complexity",
    "Sorting",
    "Hashmaps",
    "Recursion",
    "Trees",
    "Uncategorized",
}


class AIServiceError(Exception):
    pass


def _get_client() -> genai.Client:
    if not settings.GENAI_API_KEY:
        raise AIServiceError("Google GenAI API key is missing.")
    return genai.Client(api_key=settings.GENAI_API_KEY)


def _build_history(thread: Thread) -> list[dict[str, str]]:
    history = [{"role": "user", "content": SYSTEM_PROMPT}]
    for message in thread.messages.all():
        history.append({"role": message.role, "content": message.content})
    return history


def _generate_topic(description: str) -> str:
    client = _get_client()
    completion = client.models.generate_content(
        model=settings.GENAI_MODEL,
        contents=(
            "Classify coding problems into exactly one topic from this list: "
            "Arrays, Strings, Math, Binary Search, Graphs, Dynamic Programming, "
            "Greedy, Optimization, Complexity, Sorting, Hashmaps, Recursion, Trees, Uncategorized. "
            "If the question is about performance, time/space complexity, or optimization, "
            "return Optimization or Complexity. "
            "Return only the topic name.\n\n"
            f"{description}"
        ),
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=32,
        ),
    )
    topic = (completion.text or "Uncategorized").strip()
    if topic in VALID_TOPICS:
        return topic

    topic_lower = topic.lower()
    keyword_map = {
        "optimiz": "Optimization",
        "performance": "Optimization",
        "complexity": "Complexity",
        "big o": "Complexity",
        "big-o": "Complexity",
        "greedy": "Greedy",
        "dp": "Dynamic Programming",
        "dynamic programming": "Dynamic Programming",
        "graph": "Graphs",
        "tree": "Trees",
        "hash": "Hashmaps",
        "sort": "Sorting",
        "array": "Arrays",
        "string": "Strings",
        "binary search": "Binary Search",
        "recursion": "Recursion",
        "math": "Math",
    }
    for key, mapped in keyword_map.items():
        if key in topic_lower:
            return mapped

    description_lower = description.lower()
    for key, mapped in keyword_map.items():
        if key in description_lower:
            return mapped

    return "Uncategorized"


def _generate_assistant_reply(thread: Thread) -> str:
    client = _get_client()
    contents = []
    for item in _build_history(thread):
        role = item["role"]
        if role == "assistant":
            role = "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=item["content"])],
            )
        )

    completion = client.models.generate_content(
        model=settings.GENAI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=1400,
        ),
    )
    return (completion.text or "").strip()


@transaction.atomic
def create_problem_with_ai_response(*, user, description: str) -> Problem:
    cleaned_description = description.strip()
    problem = Problem.objects.create(
        user=user,
        description=cleaned_description,
        topic="Uncategorized",
    )
    thread = Thread.objects.create(
        problem=problem,
        title=cleaned_description[:255],
    )
    Message.objects.create(
        thread=thread,
        role="user",
        content=cleaned_description,
        author=user,
    )

    try:
        problem.topic = _generate_topic(cleaned_description)
        assistant_reply = _generate_assistant_reply(thread)
    except Exception as exc:
        logger.exception("Google GenAI generation failed")
        assistant_reply = "AI failed to generate a response right now. Please try again."
        if isinstance(exc, AIServiceError):
            problem.topic = "Uncategorized"
        else:
            problem.topic = "Unknown"

    problem.save(update_fields=["topic"])
    Message.objects.create(
        thread=thread,
        role="assistant",
        content=assistant_reply,
    )
    thread.save(update_fields=["updated_at"])
    return problem


@transaction.atomic
def continue_problem_thread(*, problem: Problem, user, content: str) -> Message:
    if not hasattr(problem, "thread"):
        thread = Thread.objects.create(problem=problem, title=problem.description[:255])
    else:
        thread = problem.thread

    cleaned_content = content.strip()
    Message.objects.create(
        thread=thread,
        role="user",
        content=cleaned_content,
        author=user,
    )

    try:
        assistant_reply = _generate_assistant_reply(thread)
    except Exception:
        logger.exception("Google GenAI follow-up generation failed")
        assistant_reply = "AI failed to generate a follow-up response right now. Please try again."

    assistant_message = Message.objects.create(
        thread=thread,
        role="assistant",
        content=assistant_reply,
    )
    thread.save(update_fields=["updated_at"])
    return assistant_message
