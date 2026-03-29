from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()


class Problem(models.Model):
    description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.description[:30] + "..."


class Solution(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='solutions')
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    ai_generated = models.BooleanField(default=False)

    ANSWER_TYPES = (
        ('direct', 'Direct Answer'),
        ('explanation', 'Conceptual Explanation'),
        ('opinion', 'Opinion / Discussion'),
        ('example', 'Worked Example'),
    )

    answer_type = models.CharField(max_length=20, choices=ANSWER_TYPES, default='direct')
    created_at = models.DateTimeField(auto_now_add=True)


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