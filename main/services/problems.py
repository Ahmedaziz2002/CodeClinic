from django.db.models import Count, Prefetch, Q

from main.models import Comment, Problem, Solution
from .ai import VALID_TOPICS


def list_recent_problems(*, query: str | None = None, status: str | None = None, topic: str | None = None):
    qs = (
        Problem.objects.select_related("user")
        .annotate(
            solution_count=Count("solutions", distinct=True),
            ai_turn_count=Count("thread__messages", distinct=True),
        )
    )
    if query:
        qs = qs.filter(description__icontains=query)
    if status == "resolved":
        qs = qs.filter(accepted_solution__isnull=False)
    elif status == "open":
        qs = qs.filter(accepted_solution__isnull=True)
    if topic and topic != "all":
        qs = qs.filter(topic=topic)
    return qs.order_by("-created_at")


def list_problem_topics() -> list[str]:
    return sorted(VALID_TOPICS)


def get_problem_detail_context(problem_id: int) -> dict:
    comment_queryset = Comment.objects.select_related("author").order_by("created_at")
    problem = (
        Problem.objects.select_related("user", "accepted_solution", "accepted_solution__author")
        .prefetch_related(
            Prefetch(
                "solutions",
                queryset=Solution.objects.select_related("author")
                .annotate(
                    upvotes_count=Count("vote", filter=Q(vote__type="up")),
                    downvotes_count=Count("vote", filter=Q(vote__type="down")),
                )
                .prefetch_related(Prefetch("comments", queryset=comment_queryset))
                .order_by("-created_at"),
            ),
            "thread__messages__author",
        )
        .get(id=problem_id)
    )

    thread_messages = list(problem.thread.messages.all()) if hasattr(problem, "thread") else []

    return {
        "problem": problem,
        "human_contributions": list(problem.solutions.all()),
        "thread_messages": thread_messages,
        "accepted_solution_id": problem.accepted_solution_id,
        "active_users": list(
            problem.presences.select_related("user").values_list("user__username", flat=True).distinct()
        ),
    }
