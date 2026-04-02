from django.db.models import Case, Count, F, IntegerField, Max, Q, Value, When
from django.db.models.functions import TruncDate

from main.models import Comment, CustomUser, Message, Problem, Solution, Thread, Vote


def build_reports_context():
    total_problems = Problem.objects.count()
    total_threads = Thread.objects.count()
    total_messages = Message.objects.count()
    total_human_contributions = Solution.objects.count()
    total_comments = Comment.objects.count()
    total_votes = Vote.objects.count()
    resolved_problems = Problem.objects.filter(accepted_solution__isnull=False).count()
    community_touched_problems = Problem.objects.filter(solutions__isnull=False).distinct().count()
    problems_with_ai = Problem.objects.filter(thread__messages__role="assistant").distinct().count()
    resolution_rate = ((resolved_problems / total_problems) * 100) if total_problems else 0
    community_response_rate = ((community_touched_problems / total_problems) * 100) if total_problems else 0
    avg_messages_per_thread = (total_messages / total_threads) if total_threads else 0

    assistant_message_count = Message.objects.filter(role="assistant").count()
    owner_message_count = Message.objects.filter(role="user").count()
    human_votes = Vote.objects.count()
    human_avg_votes = human_votes / total_human_contributions if total_human_contributions else 0

    problems_per_topic = Problem.objects.values("topic").annotate(count=Count("id")).order_by("-count")
    problems_daily = (
        Problem.objects.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    contribution_type_breakdown = (
        Solution.objects.values("answer_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_active_users = (
        CustomUser.objects.annotate(
            contributions_posted=Count("solution", distinct=True),
            ai_threads_started=Count("problem", distinct=True),
            comments_posted=Count("comment", distinct=True),
            accepted_answers=Count("solution__accepted_for_problems", distinct=True),
        )
        .annotate(
            activity_score=F("contributions_posted") + F("comments_posted") + F("accepted_answers") + F("ai_threads_started")
        )
        .order_by("-activity_score", "username")[:10]
    )

    top_human_contributions = (
        Solution.objects.select_related("problem", "author")
        .annotate(
            upvotes=Count("vote", filter=Q(vote__type="up")),
            downvotes=Count("vote", filter=Q(vote__type="down")),
        )
        .annotate(
            score=F("upvotes") - F("downvotes"),
            accepted_rank=Case(
                When(accepted_for_problems__isnull=False, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .order_by("-score", "-created_at")[:10]
    )

    most_consulted_ai_threads = (
        Problem.objects.annotate(
            assistant_turns=Count("thread__messages", filter=Q(thread__messages__role="assistant"), distinct=True),
            owner_turns=Count("thread__messages", filter=Q(thread__messages__role="user"), distinct=True),
        )
        .filter(assistant_turns__gt=0)
        .annotate(total_ai_activity=F("assistant_turns") + F("owner_turns"))
        .order_by("-total_ai_activity", "-created_at")[:10]
    )

    best_users = (
        CustomUser.objects.annotate(
            total_upvotes=Count("solution__vote", filter=Q(solution__vote__type="up")),
            total_contributions=Count("solution", distinct=True),
            accepted_answers=Count("solution__accepted_for_problems", distinct=True),
        )
        .order_by("-accepted_answers", "-total_upvotes", "username")[:10]
    )

    most_active_problems = (
        Problem.objects.annotate(
            contribution_count=Count("solutions", distinct=True),
            comment_count=Count("solutions__comments", distinct=True),
            ai_turn_count=Count("thread__messages", filter=Q(thread__messages__role="assistant"), distinct=True),
        )
        .annotate(activity_score=F("contribution_count") + F("comment_count") + F("ai_turn_count"))
        .order_by("-activity_score", "-created_at")[:10]
    )

    busiest_threads = (
        Thread.objects.select_related("problem")
        .annotate(
            total_messages=Count("messages"),
            last_message_at=Max("messages__created_at"),
        )
        .order_by("-total_messages", "-last_message_at")[:10]
    )

    community_share = ((community_touched_problems / total_problems) * 100) if total_problems else 0
    ai_share = ((problems_with_ai / total_problems) * 100) if total_problems else 0

    return {
        "overview": {
            "total_problems": total_problems,
            "resolved_problems": resolved_problems,
            "resolution_rate": resolution_rate,
            "community_response_rate": community_response_rate,
            "community_touched_problems": community_touched_problems,
            "problems_with_ai": problems_with_ai,
        },
        "engagement": {
            "total_human_contributions": total_human_contributions,
            "total_comments": total_comments,
            "total_votes": total_votes,
            "total_threads": total_threads,
            "total_messages": total_messages,
            "avg_messages_per_thread": avg_messages_per_thread,
            "problems_per_topic": problems_per_topic,
            "problems_daily": problems_daily,
            "top_active_users": top_active_users,
        },
        "ai": {
            "assistant_message_count": assistant_message_count,
            "owner_message_count": owner_message_count,
            "problems_with_ai": problems_with_ai,
            "community_share": community_share,
            "ai_share": ai_share,
            "human_avg_votes": human_avg_votes,
            "contribution_type_breakdown": contribution_type_breakdown,
        },
        "oversight": {
            "top_human_contributions": top_human_contributions,
            "most_consulted_ai_threads": most_consulted_ai_threads,
            "best_users": best_users,
            "most_active_problems": most_active_problems,
            "busiest_threads": busiest_threads,
        },
    }
