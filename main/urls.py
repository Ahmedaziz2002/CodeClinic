from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('submit/', views.submit_problem, name='submit'),
    path('', views.home, name='home'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('problem/<int:problem_id>/chat/', views.add_ai_message, name='add_ai_message'),
    path('problem/<int:problem_id>/add_solution/', views.add_human_solution, name='add_human_solution'),
    path('add_comment/<int:solution_id>/', views.add_comment, name='add_comment'),
    path('vote/<int:solution_id>/<str:vote_type>/', views.vote_solution, name='vote_solution'),
    path("solution/<int:solution_id>/edit/", views.edit_solution, name="edit_solution"),
    path("solution/<int:solution_id>/delete/", views.delete_solution, name="delete_solution"),
    path("solution/<int:solution_id>/accept/", views.accept_solution, name="accept_solution"),
    path("verify-email/<uuid:token>/", views.verify_email, name="verify_email"),
]
