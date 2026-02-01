from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('submit/', views.submit_problem, name='submit'),
    path('', views.home, name='home'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('add_comment/<int:solution_id>/', views.add_comment, name='add_comment'),
    path('vote/<int:solution_id>/<str:vote_type>/', views.vote_solution, name='vote_solution'),
]
