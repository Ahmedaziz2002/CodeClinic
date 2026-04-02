from celery import shared_task
from django.contrib.auth import get_user_model

from main.models import Problem
from main.services.ai import continue_problem_thread


@shared_task
def generate_follow_up_reply(problem_id: int, user_id: int, content: str):
    problem = Problem.objects.select_related("user").get(id=problem_id)
    continue_problem_thread(problem=problem, user=get_user_model().objects.get(id=user_id), content=content)
