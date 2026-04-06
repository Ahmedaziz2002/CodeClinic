import logging
import uuid

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from main.models import CustomUser, EmailLog, EmailVerification

logger = logging.getLogger(__name__)


def build_app_url(path: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _send_auth_email(
    *,
    subject: str,
    recipient: str,
    text_template: str,
    html_template: str,
    context: dict,
    email_type: str,
    user: CustomUser | None = None,
):
    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    log = EmailLog.objects.create(
        user=user,
        email_type=email_type,
        recipient=recipient,
        subject=subject,
    )
    try:
        message.send(fail_silently=False)
        log.success = True
        log.save(update_fields=["success"])
    except Exception as exc:
        log.error_message = str(exc)
        log.save(update_fields=["error_message"])
        logger.exception("Email delivery failed for %s", recipient)
        raise


def send_verification_email(*, user: CustomUser):
    verification, created = EmailVerification.objects.get_or_create(user=user)
    if not created:
        verification.token = uuid.uuid4()
        verification.save(update_fields=["token"])
    verification_link = build_app_url(f"verify-email/{verification.token}/")
    _send_auth_email(
        subject="Verify your CodeClinic account",
        recipient=user.email,
        text_template="emails/verification_email.txt",
        html_template="emails/verification_email.html",
        email_type="verification",
        user=user,
        context={
            "user": user,
            "verification_link": verification_link,
            "app_name": "CodeClinic",
        },
    )
    return verification_link


def send_password_reset_email(*, user: CustomUser):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_link = build_app_url(f"reset-password/{uid}/{token}/")
    _send_auth_email(
        subject="Reset your CodeClinic password",
        recipient=user.email,
        text_template="emails/password_reset_email.txt",
        html_template="emails/password_reset_email.html",
        email_type="password_reset",
        user=user,
        context={
            "user": user,
            "reset_link": reset_link,
            "app_name": "CodeClinic",
        },
    )
    return reset_link


def create_account(*, username: str, email: str, password: str):
    user = CustomUser.objects.create_user(
        username=username,
        email=email.strip().lower(),
        password=password,
        is_active=False,
        is_verified=False,
    )
    email_sent = True
    try:
        send_verification_email(user=user)
    except Exception:
        email_sent = False
    return user, email_sent
