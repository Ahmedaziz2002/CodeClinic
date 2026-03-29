from django.contrib.admin import AdminSite
from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.auth.admin import UserAdmin
from .models import Problem, Solution, Comment, Vote, CustomUser
from .views import reports_dashboard

class MyAdminSite(AdminSite):
    site_header = "CodeClinic Admin Dashboard"
    site_title = "CodeClinic Admin"
    index_title = "Reports & Management"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("reports/", self.admin_view(reports_dashboard), name="reports_dashboard"),
        ]
        return custom_urls + urls

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
admin_site.register(Solution)
admin_site.register(Comment)
admin_site.register(Vote)