from calendar import c
from functools import partial
from django.core.exceptions import ValidationError
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.authentication import BasicAuthentication
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework import status

from chat.models import ChatRoom, Membership, Message, SeenMessage
from chat.serializers import BaseMessageSerializer, ChatRoomSerializer, MessageSerializer

from ..tasks import (
    set_msg_as_seen, 
    send_direct_message, 
    send_group_message,
)
from celery.result import AsyncResult



def validate_data(data, *attributes):
    """utility to check attribute in request body

    Args:
        data (dict): data to be checked
        attribute: list of attributes to check

    Yields:
        str: error list
    """
    #TODO type check
    for attr in attributes:
        if not attr in data:
            yield attr


###########################
## CHAT ROOMS
###########################

# get all my chatroom - create a chatroom
class ChatListCreateAPIView(viewsets.ViewSet):

    ###
    # GET my chats
    ###
    def get(self, request, *args, **kwargs):
        """ No auth, takes the request user from qs ?user_id=<user_id>
        """
        ctx = {}
        try:
            user_id: str = request.GET.get('user_id', '')
            if not user_id.isdigit:
                raise ValidationError("user id most be a number")
            user_id = int(user_id)
            _: User = User.objects.get(pk=user_id)
            user_chat_rooms = ChatRoom.objects.filter(
                id__in = Membership.objects.filter(
                    user_id=user_id
                ).values('chatroom_id')
            )
            ser = ChatRoomSerializer(user_chat_rooms, many=True)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = ser.data

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    ###
    # POST chat__create_chat
    ###
    def create_chatroom(self, request, *args, **kwargs):
        """Creates a chatroom by name from body.
        This creation set the group as group chat not direct 'is_direct=False'
        {
            "room_name": str 
            "room_member: list({
                "username": str
            })
        }
        """
        ctx = {}
        try:
            data = request.data
            # In case no data is sent or list is sent --> 400
            if not data or isinstance(data, list):
                raise ValidationError("Body is empty or wrong foramt")

            validation_err = list(validate_data(data, 'room_name'))
            if validation_err:
                raise ValidationError('Attribute/s {} missing'.format(' - '.join(validation_err)))


            cr:ChatRoom = ChatRoom.objects.create(
                room_name=data['room_name'],
                internal_identifier=ChatRoom().get_group_internal_id(data['room_name']),
                is_direct=False
            )

            # if member list is provided, add them to group
            username_list = [el['username'] for el in data.get('room_member', [])]
            room_members = User.objects.filter(
                username__in=(username_list)
            )

            cr.room_member.set(room_members)
            cr.save()
                
            ser = ChatRoomSerializer(cr, many=False)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = ser.data

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# leave - join chatroom
class ChatDestroyUpdateRetrieveAPIView(viewsets.ViewSet):

    ###
    # DELETE chat__leave_chat
    ###
    def leave_chat(self, request, group_id, *args, **kwargs):
        """removes the membership association user-chat_room

           post_delete signals, if no user left in room and room not 
           'is_direct' deletes the chat_room

           No auth, takes the request user from qs ?user_id=<user_id>

        """
        ctx = {}
        try:
            user_id: str = request.GET.get('user_id', '')
            if not user_id.isdigit:
                raise ValidationError("user id most be a number")
            user_id = int(user_id)
            leaver: User = User.objects.get(pk=user_id)
            cr:ChatRoom = ChatRoom.objects.get(pk=group_id)
            
            if not leaver in cr.room_member.all():
                raise ValidationError("User %s is not part of this group" % leaver.username)
            cr.room_member.remove(leaver)

            ctx['status'] = status.HTTP_204_NO_CONTENT
            ctx['message']= 'HTTP_204_NO_CONTENT'

            return Response(ctx, status=status.HTTP_204_NO_CONTENT)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ###
    # PUT chat__join_chat
    ###
    def add_user_to_chat(self, request, group_id, *args, **kwargs):
        """It is possible to join only in a grouo chat 'is_direct=False'
           not in a 1to1 chat

           No auth, takes the request user from qs ?user_id=<user_id>
        """
        ctx = {}
        try:
            user_id: str = request.GET.get('user_id', '')
            if not user_id.isdigit:
                raise ValidationError("user id most be a number")
            user_id = int(user_id)
            new_member: User = User.objects.get(pk=user_id)
            cr:ChatRoom = ChatRoom.objects.get(pk=group_id)

            
            if new_member in cr.room_member.all():
                raise ValidationError("User %s is already part of this group" % new_member.username)
            
            else:
                if cr.is_direct:
                    raise ValidationError("Can't join a private chat")

            
            cr.room_member.add(new_member)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



###########################
## MESSAGES
###########################


# get my message by group id
class MessageRetrieveAPIView(viewsets.ViewSet):

    ###
    # GET my messages with a specific room chat__get_room_messages
    ###
    def get_msg_by_group(self, request, group_id, *args, **kwargs):
        """ No auth, takes the request user from qs ?user_id=<user_id>
        """
        ctx = {}
        try:
            user_id: str = request.GET.get('user_id', '')
            if not user_id.isdigit:
                raise ValidationError("user id most be a number")
            user_id = int(user_id)
            _: User = User.objects.get(pk=user_id)

            # get the chatroom
            user_chat_room = ChatRoom.objects.prefetch_related('message_set').get(
                id = Membership.objects.get(
                    user_id=user_id,
                    chatroom_id=group_id
                ).chatroom_id
            )

            user_chat_room.messages = BaseMessageSerializer(
                user_chat_room.message_set.all(), 
                many=True
            ).data
            
            # set asynchronously the messages as 'seen'
            set_msg_as_seen.delay(chat_room_id=user_chat_room.pk, sender_id=user_id)

            ser = ChatRoomSerializer(user_chat_room)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = ser.data

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ###
    # GET my all mine unseen msgs chat__get_unseen_messages 
    # for long polling purpose to get all unseen messages
    ###
    def get_only_unseen_msgs(self, request, *args, **kwargs):
        """ No auth, takes the request user from qs ?user_id=<user_id>
        """
        ctx = {}
        try:
            user_id: str = request.GET.get('user_id', '')
            if not user_id.isdigit:
                raise ValidationError("user id most be a number")
            user_id = int(user_id)
            reader: User = User.objects.get(pk=user_id)
            # get all mine chatroom
            user_chat_rooms = ChatRoom.objects.prefetch_related('message_set').filter(
                id__in = Membership.objects.filter(
                    user_id=user_id,
                ).values('chatroom_id')
            )

            chat_rooms = []
            # for all chatroom set all unseen msgs for user
            for cr in user_chat_rooms:
                cr_msgs = cr.message_set.prefetch_related(
                    'seenmessage_set'
                )
                unseen_msgs = cr_msgs.exclude(
                    msg_from=reader
                ).filter(
                    Q(seenmessage__isnull=True) | ~Q(seenmessage__seen_by=reader)
                )
                cr.messages = BaseMessageSerializer(unseen_msgs, many=True).data
                chat_rooms.append(cr)

                # set asynchronously the messages as 'seen'
                set_msg_as_seen.delay(chat_room_id=cr.pk, sender_id=user_id)
            

            ser = ChatRoomSerializer(chat_rooms, many=True)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = ser.data

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


###########################
## MESSAGES STATUS
###########################

# get my message status by job id
class MessageStatusAPIView(viewsets.ViewSet):

    ###
    # GET chat__get_message_status
    ###
    def message_task_status(self, request, task_id, *args, **kwargs):
        """ A view to report the progress to the user """
        ctx = {}
        try:
            job = AsyncResult(task_id)
            data = job.result or job.state
            ctx['status'] = data
            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# message to user / group
class MessageCreateAPIView(viewsets.ModelViewSet):
    # permission_classes = (IsAuthenticated, BasicAuthentication, SessionAuthentication)
    queryset = Message.objects.all()
    serializer_class = MessageSerializer  

    ###
    # POST chat__message_user_create
    ###
    def message_user(self, request, user_id, *args, **kwargs):
        """Takes both users and creates a dedicated chat room
        the chatroom identifier is created (and retrieved) by ordering the
        two users objects by id and creating an hash string.

        No Auth so sender user is retrived by "from" attribute in body
        Receiver is retrieved from 'user_id'
        """
        ctx = {}
        try:
            data = request.data
            # In case no data is sent or list is sent --> 400
            if not data or isinstance(data, list):
                raise ValidationError("Body is empty or wrong foramt")

            validation_err = list(validate_data(data, 'from', 'text'))
            if validation_err:
                raise ValidationError('Attribute/s {} missing'.format(' - '.join(validation_err)))

            # send asynchronously the message
            job = send_direct_message.delay(data=data, user_id=user_id)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = job.id

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ###
    # POST chat__message_group_create
    ###
    def message_group(self, request, group_id, *args, **kwargs):
        """for group message, group need to exists
            No Auth so sender user is retrived by "from" attribute in body
            Receiver is retrieved from 'group_id'
        """
        ctx = {}
        try:
            data = request.data
            # In case no data is sent or list is sent --> 400
            if not data or isinstance(data, list):
                raise ValidationError("Body is empty or wrong foramt")

            validation_err = list(validate_data(data, 'from', 'text'))
            if validation_err:
                raise ValidationError('Attribute/s {} missing'.format(' - '.join(validation_err)))

            # send asynchronously the message
            job = send_group_message.delay(data=data, group_id=group_id)

            ctx['status'] = status.HTTP_200_OK
            ctx['message']= 'HTTP_200_OK'
            ctx['data'] = job.id

            return Response(ctx, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as ex:
            ctx['status'] = status.HTTP_400_BAD_REQUEST
            ctx['msg'] = str(ex)         
            return Response(ctx, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            ctx['status'] = status.HTTP_404_NOT_FOUND
            ctx['msg'] = str(ex)
            return Response(ctx, status=status.HTTP_500_INTERNAL_SERVER_ERROR)