import sys
from contextvars import ContextVar
from django.test import TestCase, TransactionTestCase, override_settings
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from celery.result import EagerResult
from ..models import ChatRoom, Message
from celery import Celery
celery_app = Celery('jbl_chat')
#

@override_settings(TESTING=True, CELERY_TASK_ALWAYS_EAGER=True)
class MessagesTestCase(TransactionTestCase):
    """
        * test_0001_direct_message           : chat__message_user_create : POST : Test direct message to user and check the uniqe chatroom creation for both

        * test_0002_group_message            : chat__message_group_create: POST : Test sending a message to chatroom

        * test_0003_read_message_by_room     : chat__get_room_messages   : GET  : Test reading message and set as seen

        * test_0004_read_all_unseen_messages : chat__get_unseen_messages : GET  : Test reading all and only unreaded messages and set as seen

    """

    @classmethod
    def setUpClass(cls):
        celery_app.conf.task_always_eager = True
        
        cls.client = Client()

        cls.test1_API = 'chat__message_user_create'
        cls.test2_API = 'chat__message_group_create'
        cls.test3_API = 'chat__get_room_messages'
        cls.test4_API = 'chat__get_unseen_messages'

        cls.taskStatusAPI = 'chat__get_message_status'

        super(MessagesTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        User.objects.all().delete()
        ChatRoom.objects.all().delete()
        celery_app.conf.task_always_eager = False
        super(MessagesTestCase, cls).tearDownClass()

    def setUp(self):
        # need TransactionalTestCase to test DB result after API call
        # cons are that pre-data has to be reacreated in the setup method
        # before every test and not in the setUpClass before all tests
        
        self.user1, _ = User.objects.get_or_create(**{'username': 'user1', 'password':'test'})
        self.user2, _ = User.objects.get_or_create(**{'username': 'user2', 'password':'test'})
        self.user3, _ = User.objects.get_or_create(**{'username': 'user3', 'password':'test'})
        self.user4, _ = User.objects.get_or_create(**{'username': 'user4', 'password':'test'})

        self.roomFamily, _ = ChatRoom.objects.get_or_create(room_name='family', is_direct=False)
        self.roomFamily.room_member.add(self.user1, self.user2, self.user3)

        self.roomFriend, _ = ChatRoom.objects.get_or_create(room_name='friends', is_direct=False)
        self.roomFriend.room_member.add(self.user1, self.user4)
        super(MessagesTestCase, self).setUp()


    def test_0001_direct_message(self):
        ###
        # Send direct message from user 1 to user 2
        ###
        payload = {
            "from": self.user1.id,
            "text": "hi my man"
        }
        receiver_id = self.user2.id
        url = reverse(
            self.test1_API,
            args=(receiver_id,))
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res.get('status'), 200)

        ###
        # Test celery task status as succeded
        ###
        task_id = res.get('data')
        # test the task result
        task_status_url = reverse(
            self.taskStatusAPI,
            kwargs={
                'task_id': task_id,
            }
        )
        # Await for task to complete then read result from dedicated API
        response = self.client.get(task_status_url)
        res = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            res.get('state'),
            'SUCCESS'
        )
        task_result = res.get('result')
        room_id = task_result['room']['id']

        ###
        # Message back from user 2 to user 1 and check if chatroom is the same
        ###
        payload = {
            "from": self.user2.id,
            "text": "hey what's up"
        }
        receiver_id = self.user1.id
        url = reverse(
            self.test1_API,
            args=(receiver_id,)
        )
        response = self.client.post(url, data=payload)
        res = response.json()

        task_id = res.get('data')
        # test the task result
        task_status_url = reverse(
            self.taskStatusAPI,
            kwargs={
                'task_id': task_id,
            }
        )

        # Await for task to complete then read result from dedicated API
        response = self.client.get(task_status_url)
        res = response.json()
        task_result = res.get('result')
        room_id2 = task_result['room']['id']
        self.assertEqual(room_id, room_id2)



    def test_0002_group_message(self):
        ###
        # Chat from user1 to his group 'family'
        ###
        payload = {
            "from": self.user1.id,
            "text": "hi family"
        }
        family_group_id = self.roomFamily.id
        family_url = reverse(
            self.test2_API,
            args=(family_group_id,)
        )
        family_response = self.client.post(family_url, data=payload)
        self.assertEqual(family_response.status_code, 200)
        res = family_response.json()

        ###
        # Test celery task status as succeded
        ###
        task_id = res.get('data')
        # test the task result
        task_status_url = reverse(
            self.taskStatusAPI,
            kwargs={
                'task_id': task_id,
            }
        )
        # Await for task to complete then read result from dedicated API
        response = self.client.get(task_status_url)
        res = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            res.get('state'),
            'SUCCESS'
        )

        ###
        #  Test blocking message from user 4 (friend but no family) to family group
        ###
        payload = {
            "from": self.user4.id,
            "text": "can I be part of the family?"
        }
        family_response = self.client.post(family_url, data=payload)
        self.assertEqual(family_response.status_code, 200)
        res = family_response.json()

        ###
        # Test celery task status as failed
        ###
        task_id = res.get('data')
        # test the task result
        task_status_url = reverse(
            self.taskStatusAPI,
            kwargs={
                'task_id': task_id,
            }
        )
        # Await for task to complete then read result from dedicated API
        response = self.client.get(task_status_url)
        res = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            res.get('state'),
            'FAILURE',
            res.get('result')
        )


    def test_0003_read_message_by_room(self):
        ###
        # Chat from user1 to his group 'family'
        ###
        # create the msg from user 1
        # delete all previous messages
        Message.objects.all().delete()
        text = 'hi family'
        payload = {
            "from": self.user1.id,
            "text": text
        }
        family_group_id = self.roomFamily.id
        family_url = reverse(
            self.test2_API,
            args=(family_group_id,)
        )
        family_response = self.client.post(family_url, data=payload)
        self.assertEqual(family_response.status_code, 200)

        # user2 reads the message
        url = reverse(
            self.test3_API,
            args=(self.roomFamily.id,)
        )
        url = '{}{}{}'.format(url, '?user_id=', self.user2.id)
        response = self.client.get(url)
        self.assertEqual(family_response.status_code, 200)
        # readng text
        res = response.json()
        msg = res['data']['messages'][0]
        msg_txt = msg['text']
        self.assertEqual(text, msg_txt)


        # user4 can't read the messagw cause not in the group 'family'
        url = reverse(
            self.test3_API,
            args=(self.roomFamily.id,)
        )

        url = '{}{}{}'.format(url, '?user_id=', self.user4.id)
        response = self.client.get(url)
        self.assertEqual(family_response.status_code, 200)
        # readng text
        res = response.json()
        status = res['status']
        self.assertEqual(status, 404) # returned by the 'chartoom not found'


    def test_0004_read_all_unseen_messages(self):
        pass






