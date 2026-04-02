from django.contrib.auth.backends import ModelBackend
from .models import CustomUser

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get('email', username) or "").strip().lower()
        if not email or not password:
            return None
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password):
            # The app no longer gates access on email verification.
            if not user.is_active or not user.is_verified:
                user.is_active = True
                user.is_verified = True
                user.save(update_fields=["is_active", "is_verified"])
            if self.user_can_authenticate(user):
                return user
        return None
