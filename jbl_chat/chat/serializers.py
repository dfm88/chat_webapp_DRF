from django.contrib.auth.models import User
from .models import ChatRoom, Message, Membership, SeenMessage
from rest_framework import serializers
from authentication.serializers import UserBaseSerializer


class MembershipSerializer(serializers.ModelSerializer):
    user = UserBaseSerializer()
    class Meta:
        model = Membership
        fields = ('id', 'date_joined', 'user')


class ChatRoomSerializer(serializers.ModelSerializer):
    room_member = serializers.SerializerMethodField(method_name='get_room_members')

    class Meta:
        model = ChatRoom
        fields = ('id', 'room_name', 'room_member')

    def get_room_members(self, chatroom):
        """excludes user that left the chat room """
        qset = chatroom.room_member.exclude(
            id__in=Membership.objects.filter(
                chatroom_id= chatroom.id, 
                date_lefted__isnull=False
            ).values('user_id')
        )
        return [UserBaseSerializer(m).data for m in qset]


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

class SeenMessageSerializer(serializers.ModelSerializer):
    message = MessageSerializer()
    room = ChatRoomSerializer()

    class Meta:
        model = SeenMessage
        fields = '__all__'
        