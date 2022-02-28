from __future__ import absolute_import, unicode_literals
from time import sleep

from jbl_chat.celery import shared_task
from django.contrib.auth.models import User
from django.db.models import Q
from celery import Celery, current_task

from chat.models import ChatRoom, Message, SeenMessage

## LOGGING
import logging
logger = logging.getLogger(__name__)

celery_app = Celery('jbl_chat')

@celery_app.task(bind=True)
def send_direct_message(self, data: dict, user_id: int):
    logger.info("starting send direct msg task")


    sender: User = User.objects.get(pk=data['from'])
    receiver: User = User.objects.get(pk=user_id)

    # update task status
    meta={
        'status': 'STARTING SENDING DIRECT MESSAGE', 
        'sender': sender.username , 
        'receiver': receiver.username
    }
    self.update_state(state='PROGRESS',
        meta=meta)

    cr:ChatRoom = ChatRoom().get_or_create_direct_chat(
        receiver=receiver, sender=sender
    )

    Message.objects.create(
        room=cr,
        msg_from=sender,
        text=data['text']
    )

    # update task status
    meta['status'] = 'DONE SENDING DIRECT MESSAGE'
    self.update_state(state='ENDING',
        meta=meta)

    logger.info("task finished")


@celery_app.task(bind=True)
def send_group_message(self, data: dict, group_id: int):
    logger.info("starting send group msg task")


    sender: User = User.objects.get(pk=data['from'])
    receiver: ChatRoom = ChatRoom.objects.get(pk=group_id)

    # update task status
    meta={
        'status': 'STARTING SENDING GROUP MESSAGE', 
        'sender': sender.username , 
        'receiver': receiver.room_name
    }
    self.update_state(state='PROGRESS',
        meta=meta)

    Message.objects.create(
        room=receiver,
        msg_from=sender,
        text=data['text']
    )

    # update task status
    meta['status'] = 'DONE SENDING GROUP MESSAGE'
    self.update_state(state='ENDING',
        meta=meta)

    logger.info("task finished")


@celery_app.task(bind=True)
def set_msg_as_seen(self, chat_room_id: int, sender_id: int):
    logger.info("starting task to set msgs as seen task")
    
    reader: User = User.objects.get(pk=sender_id)

    # get the chatroom and therelated messages
    user_chat_room = ChatRoom.objects.using('default').prefetch_related(
        'message_set'
    ).get(pk=chat_room_id)

    # get the messages related to the chat_room and if 
    # they were already readed
    chat_room_msgs = user_chat_room.message_set.prefetch_related(
        'seenmessage_set'
    ).all()

    # set as 'seen' all messages that weren't already seen by me
    # excluding those I wrote (don't set as seen my own messages)
    msg_not_seen_by_me = chat_room_msgs.exclude(
        msg_from=reader
    ).filter(
        Q(seenmessage__isnull=True) | ~Q(seenmessage__seen_by=reader)
    )
    total = len(msg_not_seen_by_me)
    for i, new_msg in enumerate(msg_not_seen_by_me):
        # update task status
        meta={'parsing':new_msg.id, 'current': i+1, 'total': total}
        self.update_state(state='PROGRESS',
            meta=meta)

        logger.info('set msg %s as seen' % new_msg.id)
        SeenMessage.objects.update_or_create(message=new_msg, seen_by=reader)

    logger.info("task finished")