# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message
from django.core.exceptions import ObjectDoesNotExist

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chatroom_id = self.scope['url_route']['kwargs']['chatroom_id']
        self.room_group_name = f'chat_{self.chatroom_id}'
        self.user = self.scope['user']

        # Only authenticated users can connect
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verify that this user is either the farmer or customer of the chatroom
        is_allowed = await self.is_user_in_chatroom(self.chatroom_id, self.user)

        if not is_allowed:
            await self.close()  # Reject connection silently for security
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message', '').strip()
        user = self.scope['user']

        if not message_text:
            return  # Ignore empty messages

        if not user.is_authenticated:
            await self.send(text_data=json.dumps({
                'error': 'User not authenticated.'
            }))
            return

        # Save message to DB (async)
        saved_message = await self.save_message(self.chatroom_id, user, message_text)

        if not saved_message:
            await self.send(text_data=json.dumps({
                'error': 'Chat room does not exist or is invalid.'
            }))
            return

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'username': user.username,
                'timestamp': saved_message.timestamp.strftime('%Y-%m-%d %H:%M')
            }
        )

    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp']  # Include timestamp for UI
        }))

    @database_sync_to_async
    def is_user_in_chatroom(self, chatroom_id, user):
        """
        Check if the user is either the farmer or customer of the chatroom.
        Returns True if authorized, False otherwise.
        """
        try:
            chatroom = ChatRoom.objects.select_related('farmer__user', 'customer__user').get(id=chatroom_id)
            return user == chatroom.farmer.user or user == chatroom.customer.user
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, chatroom_id, user, text):
        """
        Save message to database only if chatroom exists and user is authorized.
        """
        try:
            chatroom = ChatRoom.objects.get(id=chatroom_id)
            return Message.objects.create(chatroom=chatroom, sender=user, text=text)
        except ChatRoom.DoesNotExist:
            return None