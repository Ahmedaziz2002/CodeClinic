from django.contrib.admin import AdminSite
from django.urls import path
from .models import Problem, Solution, Comment, Vote
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

# Register your models
admin_site.register(Problem)
admin_site.register(Solution)
admin_site.register(Comment)
admin_site.register(Vote)
