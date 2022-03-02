from asyncio.log import logger
from os import environ
from typing import List
from django.db import models
from django.contrib.auth.models import User
import base64

# Create your models here.
class ChatRoom(models.Model):
    internal_identifier = models.CharField(max_length=255, unique=True, blank=False)
    room_name = models.CharField(max_length=255, unique=True, blank=False)
    room_member = models.ManyToManyField(User, through='Membership')
    is_direct = models.BooleanField(default=False)
    
    def get_or_create_direct_chat(self, sender:User, receiver:User):
        """Direct chat room (user to user) is created automatically at
           first interaction 

        Returns:
            ChatRoom
        """

        msg = self.get_direct_base_internal_id(sender, receiver)
        unique_direct_room_name = self.get_direct_chat_name(sender, receiver)
        cr, created = ChatRoom.objects.get_or_create(
            internal_identifier=self.encode_msg(msg), 
            room_name=unique_direct_room_name,
            is_direct=True
        )
        if created:
            cr.room_member.set([sender, receiver])
        
        log = 'Private chat already existed' if created else 'Creating new private chat'
        logger.debug('%s for users %s - %s', log, sender.username, receiver.username)
        return cr


    def get_direct_base_internal_id(self, sender: User, receiver: User) -> str:
        """Order the sender and the receiver by id and creates an hash
        """
        sorted_partecipants = self._sort_partecipants_by_id(sender, receiver)
        partecipants_ids = [x.id for x in sorted_partecipants]
        base_hash: str = ('-').join(str(partecipants_ids))
        return base_hash

    def get_group_internal_id(self, group_name: str) -> str:
        """Creates unique id for group chats
        """
        return self.encode_msg(group_name)


    def decode_msg(self, msg: str):
        return base64.b64decode(msg).decode()
    
    def encode_msg(self, msg:str):
        return base64.b64encode(msg.encode()).decode()

    def _sort_partecipants_by_id(self,  *partecipants: List[User]) -> List[User]:
        partecipants = list(partecipants)
        partecipants.sort(key=lambda x: x.id)
        return partecipants


    def get_direct_chat_name(self, sender:User, receiver:User) -> str:
        # for direct message room name is default sender.username - receiver.username
        sorted_partecipants = self._sort_partecipants_by_id(sender, receiver)
        partecipants_usrn = [x.username for x in sorted_partecipants]
        return '{0} - {1}'.format(*partecipants_usrn) 

    def save(self, *args, **kwargs):
        # avoid null field in unique identifier

        if not getattr(self, 'internal_identifier', None):
            if getattr(self, 'room_name', None):
                #TODO listen for change on the group name to update the identifier
                setattr(self, 'internal_identifier', self.encode_msg(self.room_name))
        if self._state.adding:
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.room_name

class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_lefted = models.DateTimeField(null=True, default=None)

    def save(self, *args, **kwargs) -> None:
        # chek if last element of user-chatroom has the
        # 'date_lefed empt it means that the user still
        # belongs to chatroom, so do nothing
        last_join = Membership.objects.filter(
            user=self.user, chatroom=self.chatroom
        ).last()

        if last_join and last_join.date_lefted is None:
            return
            
        return super().save(*args, **kwargs)
    class Meta:
        unique_together = (
            ('user', 'chatroom', 'date_joined'), 
            ('user', 'chatroom', 'date_lefted')
        )

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    msg_from = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="msg_as_sender")
    text = models.TextField(max_length=1024, default="")
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} - Message message from {}".format(self.pk, self.msg_from.username)

class SeenMessage(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    seen_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    seen_at = models.DateTimeField(auto_now_add=True)
