from __future__ import absolute_import, unicode_literals
from time import sleep
import traceback

from jbl_chat.celery import shared_task
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from celery import Celery, current_task
from celery.states import FAILURE, SUCCESS, PENDING
from celery.exceptions import Ignore

from chat.models import ChatRoom, Message, SeenMessage
from chat.serializers import ChatRoomSerializer, MessageSerializer

## LOGGING
import logging
logger = logging.getLogger(__name__)

celery_app = Celery('jbl_chat')

@celery_app.task(bind=True)
def send_direct_message(self, data: dict, user_id: int) -> dict:
    """Async task that send a message to a user

    Args:
        data (dict): data containing the body of the request
        user_id (int): user id of the receiver
        default_db (str, optional): It's a bit tricky but it force celery to use the test DB during tests. Defaults to 'default'.

    Raises:
        ex: Exception

    Returns:
        dict: serialized message data
    """

    try:
        logger.info("starting send direct msg task")


        sender: User = User.objects.get(pk=data['from'])
        receiver: User = User.objects.get(pk=user_id)

        # update task status
        meta={
            'status': 'STARTING SENDING DIRECT MESSAGE', 
            'sender': sender.username , 
            'receiver': receiver.username
        }
        self.update_state(
            state=PENDING,
            meta=meta
        )
        cr:ChatRoom = ChatRoom().get_or_create_direct_chat(
            receiver=receiver, sender=sender
        )

        msg = Message.objects.create(
            room=cr,
            msg_from=sender,
            text=data['text']
        )

        # update task status
        meta['status'] = 'DONE SENDING DIRECT MESSAGE'
        self.update_state(
            state=PENDING,
            meta=meta
        )

        logger.info("task finished")

        ser = MessageSerializer(msg)

        self.update_state(
            state=SUCCESS,
            meta=ser.data
        )
        return ser.data
    except Exception as ex:
        self.update_state(
            state=FAILURE,
            meta={
                'exc_message': traceback.format_exc().split('\n'),
                'exc_type': type(ex).__name__,
            }
        )
        raise Ignore()

@celery_app.task(bind=True)
def send_group_message(self, data: dict, group_id: int) -> dict:
    """Async task that send a message to a chat room (group)

    Args:
        data (dict): data containing the body of the request
        group_id (int): id of the of the receiver chat room
        default_db (str, optional): It's a bit tricky but it force celery to use the test DB during tests. Defaults to 'default'.

    Raises:
        ex: Exception

    Returns:
        dict: serialized message data
    """
    try:
        logger.info("starting send group msg task")

        sender: User = User.objects.get(pk=data['from'])
        receiver: ChatRoom = ChatRoom.objects.get(pk=group_id)

        # update task status
        meta={
            'status': 'STARTING SENDING GROUP MESSAGE', 
            'sender': sender.username , 
            'receiver': receiver.room_name
        }
        self.update_state(
            state=PENDING,
            meta=meta
        )

        # if sender is not part of the group
        if sender not in ChatRoomSerializer().get_room_members(
            receiver, get_queryset=True
            ):

            logger.warn("User %s doesn't belong to chatroom %s", sender.username, receiver.room_name)
            raise PermissionDenied("User doesn't belong to chatroom")

        msg = Message.objects.create(
            room=receiver,
            msg_from=sender,
            text=data['text']
        )

        # update task status
        meta['status'] = 'DONE SENDING GROUP MESSAGE'
        self.update_state(
            state=PENDING,
            meta=meta
        )

        logger.info("task finished")

        ser = MessageSerializer(msg)

        self.update_state(
            state=SUCCESS,
            meta=ser.data
        )
        return ser.data

    except Exception as ex:
        self.update_state(
            state=FAILURE,
            meta={
                'exc_message': traceback.format_exc().split('\n'),
                'exc_type': type(ex).__name__,
            }
        )
        raise Ignore()
        


@celery_app.task(bind=True)
def set_msg_as_seen(self, chat_room_id: int, reader_id: int) -> dict:
    """Async task that set all retrieved messages as seen
       it's applied only for those message the the reader_id hadn't already read and those that werent sent by himself

    Args:
        chat_room_id (int)
        reader_id (int)
        default_db (str, optional): It's a bit tricky but it force celery to use the test DB during tests. Defaults to 'default'.

    Raises:
        ex: Exception

    Returns:
        dict: serialized message data
    """
    try:
        logger.info("starting task to set msgs as seen task")
        
        reader: User = User.objects.get(pk=reader_id)

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
            self.update_state(
                state=PENDING,
                meta=meta
            )

            logger.info('set msg %s as seen' % new_msg.id)
            SeenMessage.objects.update_or_create(message=new_msg, seen_by=reader)

        logger.info("task finished")
        
        ser = MessageSerializer(msg_not_seen_by_me, many=True)
        self.update_state(
            state=SUCCESS,
            meta=ser.data
        )
        return ser.data
        
    except Exception as ex:
        self.update_state(
            state=FAILURE,
            meta={
                'exc_message': traceback.format_exc().split('\n'),
                'exc_type': type(ex).__name__,
            }
        )
        raise Ignore()