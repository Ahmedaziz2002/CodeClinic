from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.template.loader import render_to_string
import logging

from main.models import Problem, Solution

logger = logging.getLogger(__name__)


@transaction.atomic
def create_human_solution(*, problem: Problem, author, content: str, request):
    solution = Solution.objects.create(
        problem=problem,
        content=content.strip(),
        author=author,
        answer_type="direct",
    )

    solution = (
        Solution.objects.select_related("author")
        .prefetch_related("comments__author")
        .get(id=solution.id)
    )
    solution.upvotes_count = 0
    solution.downvotes_count = 0

    rendered_card = render_to_string(
        "partials/solution_card.html",
        {
            "solution": solution,
            "problem": problem,
            "accepted_solution_id": problem.accepted_solution_id,
            "user": None,
        },
        request=request,
    )

    channel_layer = get_channel_layer()
    if channel_layer is not None:
        try:
            async_to_sync(channel_layer.group_send)(
                f"problem_{problem.id}",
                {
                    "type": "solution.created",
                    "html": rendered_card,
                    "solution_id": solution.id,
                },
            )
        except Exception:
            logger.exception("Live contribution broadcast failed for problem %s", problem.id)

    return solution, rendered_card
