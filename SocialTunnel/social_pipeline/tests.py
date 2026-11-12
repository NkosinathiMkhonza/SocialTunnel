from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Message


class ActiveUserRegistryTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice',
            password='test-password',
        )
        self.bob = User.objects.create_user(
            username='bob',
            password='test-password',
        )
        User.objects.create_user(
            username='inactive',
            password='test-password',
            is_active=False
        )

    def test_active_users_require_authentication(self):
        response = self.client.get(reverse('api_active_users'))

        self.assertEqual(response.status_code, 401)

    def test_registry_returns_active_users_except_requester(self):
        self.client.force_authenticate(user=self.alice)

        response = self.client.get(reverse('api_active_users'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_user_count'], 1)
        self.assertEqual(
            response.data['users'],
            [{'id': self.bob.id, 'username': 'bob'}]
        )


class PostsTemporarilyDisabledTests(APITestCase):
    def test_posts_url_is_not_available_while_feature_is_disabled(self):
        response = self.client.get('/api/posts/')

        self.assertEqual(response.status_code, 404)


class DirectMessageTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice',
            password='test-password',
        )
        self.bob = User.objects.create_user(
            username='bob',
            password='test-password',
        )

    def test_messages_require_authentication(self):
        response = self.client.get(reverse('api_messages'), {'username': 'bob'})

        self.assertEqual(response.status_code, 401)

    def test_user_can_send_and_read_conversation_messages(self):
        self.client.force_authenticate(user=self.alice)
        send_response = self.client.post(
            reverse('api_messages'),
            {'recipient': 'bob', 'message': 'Hello, Bob!'},
            format='json',
        )

        self.assertEqual(send_response.status_code, 201)
        self.assertEqual(send_response.data['sender'], 'alice')
        self.assertEqual(send_response.data['message_text'], 'Hello, Bob!')

        Message.objects.create(
            sender=self.bob,
            recipient=self.alice,
            message_text='Hello, Alice!'
        )
        conversation_response = self.client.get(
            reverse('api_messages'),
            {'username': 'bob'},
        )

        self.assertEqual(conversation_response.status_code, 200)
        self.assertEqual(
            [
                message['message_text']
                for message in conversation_response.data['messages']
            ],
            ['Hello, Bob!', 'Hello, Alice!']
        )

    def test_cannot_send_message_to_unknown_user(self):
        self.client.force_authenticate(user=self.alice)

        response = self.client.post(
            reverse('api_messages'),
            {'recipient': 'nobody', 'message': 'Hello'},
            format='json',
        )

        self.assertEqual(response.status_code, 404)
