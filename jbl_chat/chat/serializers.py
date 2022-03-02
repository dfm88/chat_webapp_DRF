from django.contrib.auth.models import User
from django.db.models import F, Count

from .models import ChatRoom, Message, Membership, SeenMessage
from rest_framework import serializers
from authentication.serializers import UserBaseSerializer


class MembershipSerializer(serializers.ModelSerializer):
    user = UserBaseSerializer()
    class Meta:
        model = Membership
        fields = ('id', 'date_joined', 'user')


class BaseChatRoomSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatRoom
        fields = ('id', 'room_name')


class ChatRoomSerializer(serializers.ModelSerializer):
    room_member = serializers.SerializerMethodField(method_name='get_room_members')
    messages = serializers.ListField(required=False)

    class Meta:
        model = ChatRoom
        fields = ('id', 'room_name', 'room_member', 'messages')

    def get_room_members(self, chatroom, get_queryset=False):
        """excludes user that left the chat room 
           (if number of element per users in the chatroom
           is odd, it means that the last action was too
           join back to chatorrom, if it's even, the last action
           action was to leave the chatroom)

           get_queryset:bool defualt to False
        """
        qset = chatroom.room_member.filter(            # get all chatroom memebers who:
            id__in=  Membership.objects.filter(
                        chatroom_id = chatroom.id,     # belongs to the chatroom
                    ).values('user').annotate(
                        Count('user')
                        ).annotate(
                            odd=F('user__count') %2    # has an odd n° of instancese 
                            ).filter(                  
                                odd=True
                            ).
                            values_list(
                                'user'
                                )
        ).distinct()                                   # removes duplicates

        return qset if get_queryset else [
            UserBaseSerializer(m).data for m in qset
        ]


class MemberSerializer(serializers.ModelSerializer):
    chat_room = serializers.SerializerMethodField(method_name='get_chat_rooms')

    class Meta:
        model = User
        fields = ('id', 'username', 'chat_room')
    
    def get_chat_rooms(self, obj: User):
        """get chat_rooms by user"""
        qset = Membership.objects.filter(user=obj)
        return [MembershipSerializer(m).data for m in qset]


class MessageSerializer(serializers.ModelSerializer):
    room = ChatRoomSerializer()
    msg_from = MemberSerializer()

    class Meta:
        model = Message
        fields = '__all__'

class BaseMessageSerializer(serializers.ModelSerializer):
    msg_from = MemberSerializer()

    class Meta:
        model = Message
        fields = '__all__'

class SeenMessageSerializer(serializers.ModelSerializer):
    message = MessageSerializer()
    room = ChatRoomSerializer()

    class Meta:
        model = SeenMessage
        fields = '__all__'
        