import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Accept connection and authenticate user"""
        # Get user from scope, with proper type checking
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
        
        # Add user to their personal notification group
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Send unread count on connection
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
        
        await self.accept()
    
    async def disconnect(self, code):
        """Remove user from their notification group"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages"""
        if text_data:
            data = json.loads(text_data)
            
            # Handle different message types
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            elif data.get('type') == 'mark_read':
                # Mark specific notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
    
    async def notification_created(self, event):
        """Send new notification to user"""
        if self.user.id == event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'new_notification',
                'notification': event['notification_data']
            }))
            
            # Update unread count
            unread_count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count
            }))
    
    async def notification_read(self, event):
        """Send notification read status update"""
        if self.user.id == event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'notification_read',
                'notification_id': event['notification_id']
            }))
            
            # Update unread count
            unread_count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count
            }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user"""
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
    
    @sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a specific notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save(update_fields=['is_read', 'read_at'])
        except Notification.DoesNotExist:
            pass