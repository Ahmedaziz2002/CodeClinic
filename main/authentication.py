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
            if self.user_can_authenticate(user) and user.is_active and user.is_verified:
                return user
        return None
