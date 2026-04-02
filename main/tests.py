from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from main.models import Message, Problem, Solution, Thread
from main.services.ai import continue_problem_thread, create_problem_with_ai_response
from main.services.users import create_account, send_password_reset_email


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class AIConversationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="owner@example.com",
            username="owner",
            password="password123",
            is_verified=True,
        )

    @patch("main.services.ai._generate_assistant_reply", return_value="Use a dictionary to track seen values.")
    @patch("main.services.ai._generate_topic", return_value="Hashmaps")
    def test_problem_submission_creates_thread_messages_without_ai_solution_projection(self, mocked_topic, mocked_reply):
        problem = create_problem_with_ai_response(
            user=self.user,
            description="How do I solve two sum efficiently?",
        )

        self.assertEqual(problem.topic, "Hashmaps")
        self.assertTrue(Thread.objects.filter(problem=problem).exists())
        self.assertEqual(Message.objects.filter(thread=problem.thread).count(), 2)
        self.assertFalse(Solution.objects.filter(problem=problem).exists())

    @patch("main.services.ai._generate_assistant_reply", return_value="Yes, a set works well for membership checks.")
    def test_follow_up_adds_new_messages_only(self, mocked_reply):
        problem = Problem.objects.create(user=self.user, description="Initial question", topic="Uncategorized")
        Thread.objects.create(problem=problem, title="Initial question")

        assistant_message = continue_problem_thread(
            problem=problem,
            user=self.user,
            content="Would a set help here too?",
        )

        self.assertEqual(problem.thread.messages.count(), 2)
        self.assertEqual(assistant_message.role, "assistant")
        self.assertEqual(Solution.objects.filter(problem=problem).count(), 0)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class HumanContributionViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            email="owner2@example.com",
            username="owner2",
            password="password123",
            is_verified=True,
        )
        self.helper = user_model.objects.create_user(
            email="helper@example.com",
            username="helper",
            password="password123",
            is_verified=True,
        )
        self.problem = Problem.objects.create(user=self.owner, description="Need help with loops", topic="Uncategorized")
        self.client = Client()
        self.client.login(email="helper@example.com", password="password123")

    @patch("main.services.solutions.get_channel_layer")
    def test_ajax_human_contribution_returns_json_and_persists(self, mocked_channel_layer):
        mocked_layer = MagicMock()
        mocked_layer.group_send = AsyncMock()
        mocked_channel_layer.return_value = mocked_layer

        response = self.client.post(
            reverse("add_human_solution", args=[self.problem.id]),
            {"content": "Try using enumerate to keep the index."},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Solution.objects.filter(problem=self.problem, author=self.helper).exists())


class UserOnboardingTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_create_account_creates_immediately_active_user_and_sends_email(self):
        user, email_sent = create_account(username="newuser", email="new@example.com", password="password123")

        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)
        self.assertTrue(email_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("login", mail.outbox[0].body.lower())
        self.assertIn("no extra verification step is required", mail.outbox[0].body.lower())

    @patch("main.services.users.send_verification_email", side_effect=Exception("smtp down"))
    def test_create_account_still_succeeds_when_confirmation_email_fails(self, mocked_send):
        user, email_sent = create_account(username="mailfail", email="mailfail@example.com", password="password123")

        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)
        self.assertFalse(email_sent)
        mocked_send.assert_called_once()

    def test_signup_created_user_can_log_in_immediately(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "freshuser",
                "email": "fresh@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        response = self.client.post(
            reverse("login"),
            {
                "email": "fresh@example.com",
                "password": "password123",
            },
        )

        self.assertRedirects(response, reverse("home"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_forgot_password_sends_reset_email(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            email="recover@example.com",
            username="recover",
            password="password123",
            is_active=True,
            is_verified=True,
        )

        response = self.client.post(reverse("forgot_password"), {"email": "recover@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password", mail.outbox[0].body)
        self.assertIn("http://127.0.0.1:8000", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_email_helper_uses_shared_base_url(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="helperreset@example.com",
            username="helperreset",
            password="password123",
            is_active=True,
            is_verified=True,
        )

        reset_link = send_password_reset_email(user=user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reset_link, mail.outbox[0].body)
        self.assertTrue(reset_link.startswith("http://127.0.0.1:8000/reset-password/"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_resend_sign_in_email_sends_message_without_verification_gate(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            email="verifyme@example.com",
            username="verifyme",
            password="password123",
            is_active=True,
            is_verified=True,
        )
        mail.outbox.clear()

        response = self.client.post(reverse("resend_verification"), {"email": "verifyme@example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("login", mail.outbox[0].body.lower())
