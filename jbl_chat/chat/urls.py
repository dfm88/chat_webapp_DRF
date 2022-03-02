from django.urls import path

from chat.views.chats import (
    ChatDestroyUpdateRetrieveAPIView, 
    ChatListCreateAPIView,
    MessageRetrieveAPIView,
    MessageCreateAPIView,
    MessageStatusAPIView
)

message_create_direct = MessageCreateAPIView.as_view({
    'post':'message_user',
})

message_create_group = MessageCreateAPIView.as_view({
    'post':'message_group',
})

message_read = MessageRetrieveAPIView.as_view({
    'get':'get_msg_by_group',
})

# for polling only new messages
messages_unseen_read = MessageRetrieveAPIView.as_view({
    'get':'get_only_unseen_msgs',
})

message_status = MessageStatusAPIView.as_view({
    'get':'message_task_status',
})

chatroom_list_create = ChatListCreateAPIView.as_view({
    'get':'get', 
    'post':'create_chatroom'
})

leave_join_read_chatroom = ChatDestroyUpdateRetrieveAPIView.as_view({
    'get': 'read_chat',
    'delete':'leave_chat', 
    'put':'add_user_to_chat'
})

urlpatterns = [
    ###
    # MESSAGES
    ###
    # direct message
    path('user/<int:user_id>/', message_create_direct, name="chat__message_user_create"),
    # message group
    path('group/<int:group_id>/', message_create_group, name="chat__message_group_create"),
    # get my messages by group id
    path('messages/<int:group_id>/', message_read, name='chat__get_room_messages'),
    # get all and only mine unseen messages
    path('messages/unseen/', messages_unseen_read, name='chat__get_unseen_messages'),

    path('task_state/<str:task_id>', message_status, name='chat__get_message_status'),

    ###
    # CHATROOMS
    ###
    # get -create chatroom
    path('chatroom/', chatroom_list_create, name='chat__get_create_chat'),
    # leave - join chatroom
    path('chatroom/<int:group_id>/', leave_join_read_chatroom, name='chat__join_leave_read_chat'),

]