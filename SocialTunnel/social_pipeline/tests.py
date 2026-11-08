from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Text


class PostsTemporarilyDisabledTests(APITestCase):
    def test_posts_url_is_not_available_while_feature_is_disabled(self):
        response = self.client.get('/api/posts/')

        self.assertEqual(response.status_code, 404)


class DirectMessageTests(APITestCase):
    def setUp(self):
        # Create two accounts so the tests can exchange messages.
        self.alice = User.objects.create_user(username='alice', password='test-password')
        self.bob = User.objects.create_user(username='bob', password='test-password')

    def test_messages_require_authentication(self):
        # An unsigned-in visitor should not be able to read a private conversation.
        response = self.client.get(reverse('api_messages'), {'username': 'bob'})

        self.assertEqual(response.status_code, 401)

    def test_user_can_send_and_read_conversation_messages(self):
        # Sign Alice in directly, then check sending and reading in both directions.
        self.client.force_authenticate(user=self.alice)
        send_response = self.client.post(
            reverse('api_messages'),
            {'recipient': 'bob', 'message': 'Hello, Bob!'},
            format='json'
        )

        self.assertEqual(send_response.status_code, 201)
        self.assertEqual(send_response.data['sender'], 'alice')
        self.assertEqual(send_response.data['message_text'], 'Hello, Bob!')

        Text.objects.create(
            sender=self.bob,
            recipient=self.alice,
            message_text='Hello, Alice!'
        )
        conversation_response = self.client.get(
            reverse('api_messages'),
            {'username': 'bob'}
        )

        self.assertEqual(conversation_response.status_code, 200)
        self.assertEqual(
            [message['message_text'] for message in conversation_response.data['messages']],
            ['Hello, Bob!', 'Hello, Alice!']
        )

    def test_cannot_send_message_to_unknown_user(self):
        # The API should explain that a message destination must be a real account.
        self.client.force_authenticate(user=self.alice)

        response = self.client.post(
            reverse('api_messages'),
            {'recipient': 'nobody', 'message': 'Hello'},
            format='json'
        )

        self.assertEqual(response.status_code, 404)
