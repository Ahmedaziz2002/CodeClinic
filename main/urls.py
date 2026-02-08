from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('submit/', views.submit_problem, name='submit'),
    path('', views.home, name='home'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('problem/<int:problem_id>/add_solution/', views.add_human_solution, name='add_human_solution'),
    path('add_comment/<int:solution_id>/', views.add_comment, name='add_comment'),
    path('vote/<int:solution_id>/<str:vote_type>/', views.vote_solution, name='vote_solution'),
    path("solution/<int:solution_id>/edit/", views.edit_solution, name="edit_solution"),
    path("solution/<int:solution_id>/delete/", views.delete_solution, name="delete_solution"),
]
