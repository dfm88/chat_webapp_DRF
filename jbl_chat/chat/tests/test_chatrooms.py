from django.test import TestCase, override_settings, TransactionTestCase
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import transaction
from celery.result import AsyncResult
from ..models import ChatRoom
from celery import Celery
celery_app = Celery('jbl_chat')
#
@override_settings(TESTING=True, CELERY_TASK_ALWAYS_EAGER=True)
class ChatRoomTestCase(TransactionTestCase):
    """
        * test_0001_get_create_a_chatroom   : chat__get_create_chat   : POST      : Test chatroom creation and reading

        * test_0002_join_leave_a_chatroom   : chat__join_leave_read_chat   : PUT-DELETE : Test chatroom joining and leaving

    """


    @classmethod
    def setUpClass(cls):
        celery_app.conf.task_always_eager = True

        cls.client = Client()
        cls.test1_API = 'chat__get_create_chat'
        cls.test2_API = 'chat__join_leave_read_chat'

        super(TransactionTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        User.objects.all().delete()
        ChatRoom.objects.all().delete()
        celery_app.conf.task_always_eager = False
        super(TransactionTestCase, cls).tearDownClass()


    def setUp(self):
        # need TransactionalTestCase to test DB result after API call
        # cons are that pre-data has to be reacreated in the setup method
        # before every test and not in the setUpClass before all tests

        self.user1, _ = User.objects.get_or_create(**{'username': 'user1', 'password':'test'})
        self.user2, _ = User.objects.get_or_create(**{'username': 'user2', 'password':'test'})
        self.user3, _ = User.objects.get_or_create(**{'username': 'user3', 'password':'test'})
        self.user4, _ = User.objects.get_or_create(**{'username': 'user4', 'password':'test'})

        self.roomFamily, _ = ChatRoom.objects.get_or_create(internal_identifier='family', room_name='family', is_direct=False)
        self.roomFamily.room_member.add(self.user1, self.user2, self.user3)

        self.roomFriend, _ = ChatRoom.objects.get_or_create(internal_identifier='friends', room_name='friends', is_direct=False)
        self.roomFriend.room_member.add(self.user1, self.user4)


        super(TransactionTestCase, self).setUp()




    def test_0001_get_create_a_chatroom(self):
        ###
        # Create group named 'crew'
        ###
        room_name = 'crew'
        payload = {
            "room_name": room_name,
        }
        
        url = reverse(
            self.test1_API,
        )
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        room_name_rec = res['data']['room_name']
        self.assertEqual(room_name, room_name_rec)
        

        ###
        # Read the list of rooms without provide the qs <user_id>
        # (expect to read all (not private) chatrooms and only the room_names)
        ###
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        room_list = res['data']

        for room in room_list:
            self.assertTrue(room.get('room_member') is None)

        ###
        # Read the list of rooms providing the <user_id>
        # (expect to read all chatrooms and also the room_members)
        ###
        url = '{}{}{}'.format(url, '?user_id=', self.user1.id)
        response = self.client.get(url)

        res = response.json()
        room_list = res['data']
        for room in room_list:
            self.assertTrue(room.get('room_member') is not None)

    def test_0002_join_leave_a_chatroom(self):
        ###
        # Create group named 'crew'
        ###
        room_name = 'besties'
        payload = {
            "room_name": room_name,
        }
        
        url = reverse(
            self.test1_API,
        )
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        room_name_rec = res['data']['room_name']
        room_id = res['data']['id']
        self.assertEqual(room_name, room_name_rec)
        
        
        ###
        # Join with user 2 to previously created chatroom 'besties'
        ###
        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user2.id)
        response = self.client.put(url)
        self.assertEqual(response.status_code, 200)

        ###
        # Also user 3 will join the crew chatroom
        ###
        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user3.id)
        response = self.client.put(url)
        self.assertEqual(response.status_code, 200)

        ###
        # User 2 will leave the chatroom (the chatroom still have to exists)
        # because User 3 is still in
        ###
        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user2.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)


        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        # Check if chatrrom still exists 
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        ###
        # User 3 will leave the chatroom the chatroom will
        # be delleted because it's now empty
        ###
        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user3.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)


        url = reverse(
            self.test2_API,
            args=(room_id,)
        )
        # Check if chatrrom was deleted 
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


        ###
        # Join with user 2 to a private chatroom, expected error
        ###
        private_chat_room, _ = ChatRoom.objects.get_or_create(room_name='private', is_direct=True)
        
        url = reverse(
            self.test2_API,
            args=(private_chat_room.id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user2.id)
        response = self.client.put(url)
        self.assertEqual(response.status_code, 400)