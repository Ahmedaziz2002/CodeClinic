from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.db.models.functions import TruncDate

from .models import Problem, Solution, Comment, Vote

from decouple import config
import google.generativeai as genai
import logging

GENAI_API_KEY = config("GENAI_API_KEY", default=None)

AI_ENABLED = False
MODEL = None
GENAI_MODEL = config(
    "GENAI_MODEL",
    default="models/gemini-1.5-flash"
)

if GENAI_API_KEY:
    try:
        genai.configure(api_key=GENAI_API_KEY)
        MODEL = genai.GenerativeModel(GENAI_MODEL)
        AI_ENABLED = True
    except Exception as e:
        logging.error(f"Gemini init failed: {e}")


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("signup")

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created. Please log in.")
        return redirect("login")

    return render(request, "signup.html")


def user_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )

        if user:
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid credentials")
        return redirect("login")

    return render(request, "login.html")


def user_logout(request):
    logout(request)
    return redirect("login")

@login_required(login_url="login")
def submit_problem(request):
    if request.method != "POST":
        return redirect("home")

    description = request.POST.get("description")

    ai_solution_text = "AI service unavailable."
    ai_topic = "Uncategorized"

    if AI_ENABLED:
        try:
            topic_prompt = (
                "Classify this coding problem into ONE topic from:\n"
                "[Arrays, Strings, Math, Binary Search, Graphs, "
                "Dynamic Programming, Sorting, Hashmaps, Recursion, Trees]\n\n"
                "Return ONLY the topic name.\n\n"
                f"{description}"
            )

            topic_response = MODEL.generate_content(topic_prompt)
            ai_topic = topic_response.text.strip()

            if ai_topic not in [
                "Arrays", "Strings", "Math", "Binary Search", "Graphs",
                "Dynamic Programming", "Sorting", "Hashmaps", "Recursion", "Trees"
            ]:
                ai_topic = "Uncategorized"

            solution_prompt = (
                "Solve the following coding problem clearly.\n"
                "Explain the approach and provide code.\n\n"
                f"{description}"
            )

            solution_response = MODEL.generate_content(solution_prompt)
            ai_solution_text = solution_response.text.strip()

        except Exception as e:
            ai_solution_text = f"AI error: {str(e)}"
            ai_topic = "Unknown"

    problem = Problem.objects.create(
        user=request.user,
        description=description,
        topic=ai_topic
    )

    Solution.objects.create(
        problem=problem,
        content=ai_solution_text,
        ai_generated=True
    )

    return redirect("problem_detail", problem_id=problem.id)
from django.db.models import Count, Q

def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)

    solutions = (
        problem.solutions
        .annotate(
            upvotes_count=Count("vote", filter=Q(vote__type="up")),
            downvotes_count=Count("vote", filter=Q(vote__type="down")),
        )
        .prefetch_related("comments", "vote_set")
    )

    return render(request, "problem_detail.html", {
        "problem": problem,
        "solutions": solutions
    })

def home(request):
    problems = Problem.objects.all().order_by("-created_at")
    return render(request, "index.html", {"problems": problems})

@login_required(login_url="login")
def add_comment(request, solution_id):
    if request.method == "POST":
        solution = get_object_or_404(Solution, id=solution_id)
        Comment.objects.create(
            solution=solution,
            content=request.POST.get("content"),
            author=request.user
        )

    return redirect("problem_detail", problem_id=solution.problem.id)

@login_required(login_url="login")
def vote_solution(request, solution_id, vote_type):
    solution = get_object_or_404(Solution, id=solution_id)
    vote, created = Vote.objects.get_or_create(
        user=request.user,
        solution=solution
    )

    if not created and vote.type == vote_type:
        vote.delete()
        message = "Vote removed"
    else:
        vote.type = vote_type
        vote.save()
        message = "Vote recorded"

    return JsonResponse({
        "message": message,
        "upvotes": Vote.objects.filter(solution=solution, type="up").count(),
        "downvotes": Vote.objects.filter(solution=solution, type="down").count()
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate

from .models import Problem, Solution, Comment, Vote

@login_required(login_url="login")
def reports_dashboard(request):
    total_problems = Problem.objects.count()
    total_solutions = Solution.objects.count()
    total_comments = Comment.objects.count()
    total_votes = Vote.objects.count()

    problems_per_topic = (
        Problem.objects.values("topic")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    problems_daily = (
        Problem.objects
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    top_active_users = (
        User.objects
        .annotate(
            solutions_posted=Count("solution", distinct=True),
            comments_posted=Count("comment", distinct=True),
        )
        .annotate(
            activity_score=Count("solution", distinct=True) +
                           Count("comment", distinct=True)
        )
        .order_by("-activity_score")[:10]
    )

    ai_solutions = Solution.objects.filter(ai_generated=True).count()
    human_solutions = Solution.objects.filter(ai_generated=False).count()

    ai_votes = Vote.objects.filter(solution__ai_generated=True).count()
    human_votes = Vote.objects.filter(solution__ai_generated=False).count()

    ai_avg_votes = ai_votes / ai_solutions if ai_solutions else 0
    human_avg_votes = human_votes / human_solutions if human_solutions else 0

    ai_topic_breakdown = (
        Solution.objects
        .filter(ai_generated=True)
        .values("problem__topic")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_solutions = (
        Solution.objects
        .annotate(
            upvotes=Count("vote", filter=Q(vote__type="up")),
            downvotes=Count("vote", filter=Q(vote__type="down")),
        )
        .annotate(score=Count("vote"))
        .order_by("-score")[:10]
    )


    best_users = (
        User.objects
        .annotate(
            total_upvotes=Count("solution__vote", filter=Q(solution__vote__type="up")),
            total_solutions=Count("solution", distinct=True),
        )
        .annotate(
            avg_upvotes=Avg("total_upvotes")
        )
        .order_by("-total_upvotes")[:10]
    )

    most_active_problems = (
        Problem.objects
        .annotate(
            solution_count=Count("solutions", distinct=True),
            comment_count=Count("solutions__comments", distinct=True),
        )
        .annotate(
            activity_score=Count("solutions", distinct=True) +
                           Count("solutions__comments", distinct=True)
        )
        .order_by("-activity_score")[:10]
    )

    context = {
        "engagement": {
            "total_problems": total_problems,
            "total_solutions": total_solutions,
            "total_comments": total_comments,
            "total_votes": total_votes,
            "problems_per_topic": problems_per_topic,
            "problems_daily": problems_daily,
            "top_active_users": top_active_users,
        },
        "ai": {
            "ai_solutions": ai_solutions,
            "human_solutions": human_solutions,
            "ai_avg_votes": ai_avg_votes,
            "human_avg_votes": human_avg_votes,
            "ai_topic_breakdown": ai_topic_breakdown,
        },
        "oversight": {
            "top_solutions": top_solutions,
            "best_users": best_users,
            "most_active_problems": most_active_problems,
        }
    }

    return render(request, "admin/reports_dashboard.html", context)
