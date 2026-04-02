import csv
import logging
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from reportlab.pdfgen import canvas

from .models import Comment, CustomUser, Problem, Solution, Vote
from .services import (
    build_reports_context,
    continue_problem_thread,
    create_account,
    create_human_solution,
    create_problem_with_ai_response,
    get_problem_detail_context,
    list_recent_problems,
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")
        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect("signup")
        if CustomUser.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("signup")

        try:
            user, email_sent = create_account(username=username, email=email, password=password)
        except Exception:
            logger.exception("Account creation failed")
            messages.error(request, "We could not create your account right now.")
            return redirect("signup")

        if email_sent:
            messages.success(request, "Account created successfully. You can now log in using your email and password.")
        else:
            messages.warning(request, "Account created successfully. You can log in now using your email and password, but the email message could not be sent.")
        return redirect("login")

    return render(request, "signup.html")


def verify_email(request, token):
    messages.info(request, "Your account is already active. You can log in directly with your email and password.")
    return redirect("login")


def user_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is None and email and password:
            candidate = CustomUser.objects.filter(email__iexact=email).first()
            if candidate and candidate.check_password(password):
                if not candidate.is_active or not candidate.is_verified:
                    candidate.is_active = True
                    candidate.is_verified = True
                    candidate.save(update_fields=["is_active", "is_verified"])
                user = candidate
        if user:
            login(request, user, backend="main.authentication.EmailBackend")
            return redirect("home")
        messages.error(request, "Invalid credentials.")
        return redirect("login")
    return render(request, "login.html")


def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = CustomUser.objects.filter(email__iexact=email).first()
        if user:
            try:
                send_verification_email(user=user)
            except Exception:
                logger.exception("Resend verification email failed")
        messages.success(
            request,
            "If that account exists, a sign-in reminder email has been sent.",
        )
        return redirect("login")
    return render(request, "resend_verification.html")


def user_logout(request):
    logout(request)
    return redirect("login")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = CustomUser.objects.filter(email__iexact=email).first()
        if user:
            try:
                send_password_reset_email(user=user)
            except Exception:
                logger.exception("Password reset email failed")
        return render(request, "password_reset_sent.html")
    return render(request, "forgot_password.html")


def reset_password(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if not user or not default_token_generator.check_token(user, token):
        messages.error(request, "This password reset link is invalid or has expired.")
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")
        if not password or password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password", uidb64=uidb64, token=token)
        user.set_password(password)
        user.save(update_fields=["password"])
        messages.success(request, "Password reset successful. You can now log in.")
        return redirect("login")

    return render(request, "reset_password.html", {"uidb64": uidb64, "token": token})


@login_required(login_url="login")
def submit_problem(request):
    if request.method != "POST":
        return redirect("home")

    description = request.POST.get("description", "").strip()
    if not description:
        messages.error(request, "Problem description cannot be empty.")
        return redirect("home")

    problem = create_problem_with_ai_response(user=request.user, description=description)
    return redirect("problem_detail", problem_id=problem.id)


@login_required(login_url="login")
def add_ai_message(request, problem_id):
    if request.method != "POST":
        return redirect("problem_detail", problem_id=problem_id)

    problem = get_object_or_404(Problem.objects.select_related("user"), id=problem_id)
    if problem.user != request.user:
        messages.error(request, "Only the problem owner can continue the AI conversation.")
        return redirect("problem_detail", problem_id=problem.id)

    content = request.POST.get("content", "").strip()
    if not content:
        messages.error(request, "Follow-up message cannot be empty.")
        return redirect("problem_detail", problem_id=problem.id)

    continue_problem_thread(problem=problem, user=request.user, content=content)
    return redirect("problem_detail", problem_id=problem.id)


@login_required(login_url="login")
def add_human_solution(request, problem_id):
    if request.method != "POST":
        return redirect("problem_detail", problem_id=problem_id)

    problem = get_object_or_404(Problem.objects.select_related("user"), id=problem_id)
    if problem.user == request.user:
        error_message = "You cannot submit a human contribution to your own problem."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": error_message}, status=400)
        messages.error(request, error_message)
        return redirect("problem_detail", problem_id=problem_id)

    content = request.POST.get("content", "").strip()
    if not content:
        error_message = "Contribution cannot be empty."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": error_message}, status=400)
        messages.error(request, error_message)
        return redirect("problem_detail", problem_id=problem_id)

    solution = create_human_solution(problem=problem, author=request.user, content=content, request=request)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": "Contribution submitted.", "solution_id": solution.id}, status=201)

    return redirect("problem_detail", problem_id=problem_id)


def problem_detail(request, problem_id):
    try:
        context = get_problem_detail_context(problem_id)
    except Problem.DoesNotExist as exc:
        raise Http404("Problem not found") from exc
    return render(request, "problem_detail.html", context)


@login_required(login_url="login")
def accept_solution(request, solution_id):
    solution = get_object_or_404(Solution.objects.select_related("problem", "author"), id=solution_id)
    if request.method != "POST":
        return redirect("problem_detail", problem_id=solution.problem_id)
    if solution.problem.user != request.user:
        messages.error(request, "Only the problem owner can accept a human contribution.")
        return redirect("problem_detail", problem_id=solution.problem_id)

    solution.problem.accepted_solution = solution
    solution.problem.save(update_fields=["accepted_solution"])
    messages.success(request, "Contribution marked as accepted.")
    return redirect("problem_detail", problem_id=solution.problem_id)


@login_required(login_url="login")
def edit_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if solution.author != request.user:
        return redirect("problem_detail", problem_id=solution.problem.id)
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            solution.content = content
            solution.save(update_fields=["content"])
            return redirect("problem_detail", problem_id=solution.problem.id)
    return render(request, "edit_solution.html", {"solution": solution})


@login_required(login_url="login")
def delete_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if solution.author != request.user:
        return redirect("problem_detail", problem_id=solution.problem.id)
    if request.method == "POST":
        problem_id = solution.problem.id
        solution.delete()
        return redirect("problem_detail", problem_id=problem_id)
    return render(request, "delete_solution.html", {"solution": solution})


def home(request):
    return render(request, "index.html", {"problems": list_recent_problems()})


@login_required(login_url="login")
def profile(request):
    user = (
        CustomUser.objects
        .prefetch_related("problem_set__accepted_solution", "solution_set")
        .get(pk=request.user.pk)
    )
    problems = user.problem_set.all()[:5]
    contributions = user.solution_set.all()[:5]
    context = {
        "profile_user": user,
        "recent_problems": problems,
        "recent_contributions": contributions,
        "stats": {
            "problems_created": user.problem_set.count(),
            "human_contributions": user.solution_set.count(),
            "accepted_answers": user.solution_set.filter(accepted_for_problems__isnull=False).distinct().count(),
            "verified": user.is_verified,
        },
    }
    return render(request, "profile.html", context)


@login_required(login_url="login")
def add_comment(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            Comment.objects.create(solution=solution, content=content, author=request.user)
    return redirect("problem_detail", problem_id=solution.problem.id)


@login_required(login_url="login")
def vote_solution(request, solution_id, vote_type):
    solution = get_object_or_404(Solution, id=solution_id)
    vote, created = Vote.objects.get_or_create(user=request.user, solution=solution)
    if not created and vote.type == vote_type:
        vote.delete()
        message = "Vote removed"
    else:
        vote.type = vote_type
        vote.save()
        message = "Vote recorded"
    return JsonResponse(
        {
            "message": message,
            "upvotes": Vote.objects.filter(solution=solution, type="up").count(),
            "downvotes": Vote.objects.filter(solution=solution, type="down").count(),
        }
    )


@staff_member_required(login_url="login")
def reports_dashboard(request):
    if not request.user.has_perm("main.view_reports_dashboard"):
        raise PermissionDenied("You do not have permission to view reports.")
    context = build_reports_context()
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="reports.csv"'
        writer = csv.writer(response)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Problems", context["overview"]["total_problems"]])
        writer.writerow(["Human Contributions", context["engagement"]["total_human_contributions"]])
        writer.writerow(["Total Comments", context["engagement"]["total_comments"]])
        writer.writerow(["Total Votes", context["engagement"]["total_votes"]])
        writer.writerow(["AI Threads Started", context["ai"]["problems_with_ai"]])
        writer.writerow(["Assistant Messages", context["ai"]["assistant_message_count"]])
        writer.writerow(["Owner Follow-ups", context["ai"]["owner_message_count"]])
        writer.writerow(["Human Avg Votes", context["ai"]["human_avg_votes"]])
        return response
    if request.GET.get("export") == "pdf":
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        y = 800
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "CodeClinic Reports")
        y -= 40
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y, f"Total Problems: {context['overview']['total_problems']}")
        y -= 20
        pdf.drawString(50, y, f"Human Contributions: {context['engagement']['total_human_contributions']}")
        y -= 20
        pdf.drawString(50, y, f"Total Comments: {context['engagement']['total_comments']}")
        y -= 20
        pdf.drawString(50, y, f"Total Votes: {context['engagement']['total_votes']}")
        y -= 20
        pdf.drawString(50, y, f"AI Threads Started: {context['ai']['problems_with_ai']}")
        y -= 20
        pdf.drawString(50, y, f"Assistant Messages: {context['ai']['assistant_message_count']}")
        y -= 20
        pdf.drawString(50, y, f"Human Avg Votes: {context['ai']['human_avg_votes']}")
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type="application/pdf")
    return render(request, "admin/reports_dashboard.html", context)
