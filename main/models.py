from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

class CustomUserManager(BaseUserManager):
    def _build_unique_username(self, email: str) -> str:
        base_username = email.split("@", 1)[0][:150] or "user"
        candidate = base_username
        counter = 1
        while self.model.objects.filter(username=candidate).exists():
            suffix = str(counter)
            candidate = f"{base_username[:150 - len(suffix) - 1]}-{suffix}"
            counter += 1
        return candidate

    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        username = (username or "").strip() or self._build_unique_username(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()


class Problem(models.Model):
    description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100, blank=True, null=True)
    accepted_solution = models.ForeignKey(
        "Solution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_for_problems",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = (
            ("view_reports_dashboard", "Can view reports dashboard"),
        )

    def __str__(self):
        return self.description[:30] + "..."


class Thread(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE, related_name="thread")
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Thread for problem {self.problem_id}"


class Message(models.Model):
    ROLE_CHOICES = (
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class Solution(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='solutions')
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    ANSWER_TYPES = (
        ('direct', 'Direct Answer'),
        ('explanation', 'Conceptual Explanation'),
        ('opinion', 'Opinion / Discussion'),
        ('example', 'Worked Example'),
    )

    answer_type = models.CharField(max_length=20, choices=ANSWER_TYPES, default='direct')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contribution #{self.pk} for problem #{self.problem_id}"


class Comment(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Vote(models.Model):
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=(('up','Upvote'), ('down','Downvote')))

    class Meta:
        unique_together = ('solution', 'user')


class EmailVerification(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProblemPresence(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="presences")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="problem_presences")
    channel_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username", "created_at"]

    def __str__(self):
        return f"{self.user.username} on problem {self.problem_id}"


class EmailLog(models.Model):
    EMAIL_TYPE_CHOICES = (
        ("verification", "Verification"),
        ("password_reset", "Password Reset"),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="email_logs")
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPE_CHOICES)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "sent" if self.success else "failed"
        return f"{self.get_email_type_display()} to {self.recipient} ({status})"
