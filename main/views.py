import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from decouple import config

from google import genai
from google.genai import types

from .models import Problem, Solution, Comment, Vote


GENAI_API_KEY = config("GENAI_API_KEY", default=None)
GENAI_MODEL = config("GENAI_MODEL", default="gemini-2.5-flash")

AI_ENABLED = False
genai_client = None

if GENAI_API_KEY:
    try:
        genai_client = genai.Client(api_key=GENAI_API_KEY)
        AI_ENABLED = True
    except Exception as e:
        logging.error(f"GenAI initialization failed: {e}")

GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.4,
    max_output_tokens=800,
)

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

        User.objects.create_user(username=username, email=email, password=password)
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

            topic_response = genai_client.models.generate_content(
                model=GENAI_MODEL,
                contents=topic_prompt,
                config=GENERATION_CONFIG,
            )
            ai_topic = topic_response.text.strip()

            VALID_TOPICS = {
                "Arrays", "Strings", "Math", "Binary Search", "Graphs",
                "Dynamic Programming", "Sorting", "Hashmaps", "Recursion", "Trees"
            }
            if ai_topic not in VALID_TOPICS:
                ai_topic = "Uncategorized"

            solution_prompt = f"""
                You are a helpful programming assistant.

                Answer the user's question clearly and directly.
                If the user asks for syntax, explain it simply with examples.
                If the user asks for a concept, explain it intuitively.
                If the user asks for code, provide correct and clean code.

                User question:
                {description}
                """
            solution_response = genai_client.models.generate_content(
                model=GENAI_MODEL,
                contents=solution_prompt,
                config=GENERATION_CONFIG,
            )
            ai_solution_text = solution_response.text.strip()

        except Exception as e:
            logging.error(f"AI generation error: {e}")
            ai_solution_text = "AI failed to generate a solution."
            ai_topic = "Unknown"

    problem = Problem.objects.create(
        user=request.user,
        description=description,
        topic=ai_topic
    )

    def infer_answer_type(question: str) -> str:
        q = question.lower()
        if "example" in q or "sample" in q:
            return "example"
        if "explain" in q or "why" in q or "how does" in q:
            return "explanation"
        if "opinion" in q or "best" in q:
            return "opinion"
        return "direct"

    answer_type = infer_answer_type(description)

    Solution.objects.create(
        problem=problem,
        content=ai_solution_text,
        ai_generated=True,
        answer_type=answer_type
    )

    return redirect("problem_detail", problem_id=problem.id)


@login_required(login_url="login")
def add_human_solution(request, problem_id):
    if request.method == "POST":
        problem = get_object_or_404(Problem, id=problem_id)
        content = request.POST.get("content")

        if content:
            Solution.objects.create(
                problem=problem,
                content=content,
                author=request.user,
                ai_generated=False,
                answer_type="direct"
            )
        else:
            messages.error(request, "Solution cannot be empty.")

    return redirect("problem_detail", problem_id=problem_id)


def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)

    solutions = (
        problem.solutions
        .annotate(
            upvotes_count=Count("vote", filter=Q(vote__type="up")),
            downvotes_count=Count("vote", filter=Q(vote__type="down")),
        )
        .order_by(
            "-ai_generated",          
            "answer_type",           
            "-upvotes_count",
            "downvotes_count",
            "-created_at"
        )
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
            human_solutions_posted=Count("solution", filter=Q(solution__ai_generated=False), distinct=True),
            comments_posted=Count("comment", distinct=True),
        )
        .annotate(
            activity_score=F("human_solutions_posted") + F("comments_posted")
        )
        .order_by("-activity_score")[:10]
    )

    ai_solutions = Solution.objects.filter(ai_generated=True).count()
    human_full_solutions = Solution.objects.filter(ai_generated=False).count()

    ai_votes = Vote.objects.filter(solution__ai_generated=True).count()
    human_votes_on_solutions = Vote.objects.filter(solution__ai_generated=False).count()

    ai_avg_votes = ai_votes / ai_solutions if ai_solutions else 0
    human_avg_votes = human_votes_on_solutions / human_full_solutions if human_full_solutions else 0

    ai_type_breakdown = (
        Solution.objects.filter(ai_generated=True)
        .values("answer_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    human_type_breakdown = (
        Solution.objects.filter(ai_generated=False)
        .values("answer_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_ai_solutions = (
        Solution.objects.filter(ai_generated=True)
        .annotate(
            upvotes=Count("vote", filter=Q(vote__type="up")),
            downvotes=Count("vote", filter=Q(vote__type="down")),
        )
        .annotate(score=Count("vote"))
        .order_by("-score")[:10]
    )

    top_human_solutions = (
        Solution.objects.filter(ai_generated=False)
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
            total_upvotes=Count(
                "solution__vote",
                filter=Q(solution__vote__type="up", solution__ai_generated=False)
            ),
            total_solutions=Count("solution", filter=Q(solution__ai_generated=False), distinct=True),
        )
        .order_by("-total_upvotes")[:10]
    )

    # Most active problems (human activity only)
    most_active_problems = (
        Problem.objects
        .annotate(
            solution_count=Count("solutions", filter=Q(solutions__ai_generated=False), distinct=True),
            comment_count=Count("solutions__comments", distinct=True),
        )
        .annotate(
            activity_score=F("solution_count") + F("comment_count")
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
            "human_solutions": human_full_solutions,
            "ai_avg_votes": ai_avg_votes,
            "human_avg_votes": human_avg_votes,
            "ai_type_breakdown": ai_type_breakdown,
            "human_type_breakdown": human_type_breakdown,
        },
        "oversight": {
            "top_ai_solutions": top_ai_solutions,
            "top_human_solutions": top_human_solutions,
            "best_users": best_users,
            "most_active_problems": most_active_problems,
        }
    }

    return render(request, "admin/reports_dashboard.html", context)
