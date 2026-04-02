from django.urls import path

from .consumers import ProblemConsumer

websocket_urlpatterns = [
    path("ws/problems/<int:problem_id>/", ProblemConsumer.as_asgi(), name="problem_ws"),
]
