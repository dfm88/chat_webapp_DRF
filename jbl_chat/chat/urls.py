from django.urls import path

from chat.views.chats import (
    ChatDestroyUpdateRetrieveAPIView, 
    ChatListCreateAPIView,
    MessageRetrieveAPIView,
    MessageCreateAPIView
)

message_create = MessageCreateAPIView.as_view({
    'post':'message_user',
    'post':'message_group',
})

message_read = MessageRetrieveAPIView.as_view({
    'get':'get_msg_by_group'
})

chatroom_list_create = ChatListCreateAPIView.as_view({
    'get':'get', 
    'post':'create_chatroom'
})

leave_join_chatroom = ChatDestroyUpdateRetrieveAPIView.as_view({
    'delete':'leave_chat', 
    'put':'add_user_to_chat'
})

urlpatterns = [
    ###
    # MESSAGES
    ###
    # direct message
    path('user/<int:user_id>/', message_create, name="chat__message_user_create"),
    # message group
    path('group/<int:group_id>/', message_create, name="chat__message_group_create"),
    # get my messages by group id
    path('messages/<int:group_id>/', message_read, name='chat__get_room_messages'),

    ###
    # CHATROOMS
    ###
    # get -create chatroom
    path('chatroom/', chatroom_list_create, name='chat__get_chat'),
    # leave - join chatroom
    path('chatroom/<int:group_id>/', leave_join_chatroom, name='chat__join_leave_chat'),

]