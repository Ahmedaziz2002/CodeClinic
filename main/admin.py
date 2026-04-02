from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponse
from django.urls import path
from django.contrib.auth.admin import UserAdmin
from django.template.loader import render_to_string
from .models import Comment, CustomUser, EmailLog, Message, Problem, Solution, Thread, Vote
from .views import reports_dashboard

class MyAdminSite(AdminSite):
    site_header = "CodeClinic Admin Dashboard"
    site_title = "CodeClinic Admin"
    index_title = "Reports & Management"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("reports/", self.admin_view(reports_dashboard), name="reports_dashboard"),
            path("email-previews/verification/", self.admin_view(self.verification_email_preview), name="verification_email_preview"),
            path("email-previews/password-reset/", self.admin_view(self.password_reset_email_preview), name="password_reset_email_preview"),
        ]
        return custom_urls + urls

    def verification_email_preview(self, request):
        user = request.user
        html = render_to_string(
            "emails/verification_email.html",
            {
                "user": user,
                "login_link": "http://127.0.0.1:8000/login/",
                "app_name": "CodeClinic",
            },
        )
        return HttpResponse(html)

    def password_reset_email_preview(self, request):
        user = request.user
        html = render_to_string(
            "emails/password_reset_email.html",
            {
                "user": user,
                "reset_link": "http://127.0.0.1:8000/reset-password/example-uid/example-token/",
                "app_name": "CodeClinic",
            },
        )
        return HttpResponse(html)

admin_site = MyAdminSite(name="myadmin")

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "username", "is_verified", "is_staff", "is_active")
    list_filter = ("is_verified", "is_staff", "is_active")
    ordering = ("email",)
    search_fields = ("email", "username")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Verification", {"fields": ("is_verified",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "is_verified", "is_staff", "is_active")}
        ),
    )

admin_site.register(CustomUser, CustomUserAdmin)
admin_site.register(Problem)
admin_site.register(Thread)
admin_site.register(Message)
admin_site.register(Solution)
admin_site.register(Comment)
admin_site.register(Vote)
@admin.register(EmailLog, site=admin_site)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("email_type", "recipient", "subject", "success", "created_at")
    list_filter = ("email_type", "success", "created_at")
    search_fields = ("recipient", "subject", "error_message", "user__email", "user__username")
    readonly_fields = ("user", "email_type", "recipient", "subject", "success", "error_message", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
