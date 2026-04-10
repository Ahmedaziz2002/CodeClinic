import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import ProblemPresence

logger = logging.getLogger(__name__)


class ProblemConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.problem_id = self.scope["url_route"]["kwargs"]["problem_id"]
        self.group_name = f"problem_{self.problem_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        if self.scope["user"].is_authenticated:
            await self._upsert_presence()
        await self.accept()
        logger.info("WebSocket connected: problem=%s user=%s channel=%s", self.problem_id, self.scope.get("user"), self.channel_name)
        await self._broadcast_active_users()

    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self._remove_presence()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WebSocket disconnected: problem=%s channel=%s code=%s", self.problem_id, self.channel_name, close_code)
        await self._broadcast_active_users()

    async def solution_created(self, event):
        await self.send_json(
            {
                "type": "solution.created",
                "html": event["html"],
                "solution_id": event["solution_id"],
            }
        )

    async def presence_updated(self, event):
        await self.send_json(
            {
                "type": "presence.updated",
                "active_users": event["active_users"],
            }
        )

    @database_sync_to_async
    def _upsert_presence(self):
        ProblemPresence.objects.update_or_create(
            channel_name=self.channel_name,
            defaults={
                "problem_id": self.problem_id,
                "user": self.scope["user"],
            },
        )

    @database_sync_to_async
    def _remove_presence(self):
        ProblemPresence.objects.filter(channel_name=self.channel_name).delete()

    @database_sync_to_async
    def _get_active_users(self):
        return list(
            ProblemPresence.objects.filter(problem_id=self.problem_id)
            .select_related("user")
            .values_list("user__username", flat=True)
            .distinct()
        )

    async def _broadcast_active_users(self):
        active_users = await self._get_active_users()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence.updated",
                "active_users": active_users,
            },
        )
