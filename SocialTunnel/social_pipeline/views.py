from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView

from .models import Post, Text as TextMessage


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {"error": "Both username and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "A user with that username already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(username=username, password=password)
    return Response(
        {"status": "success", "message": f"User {user.username} created successfully!"},
        status=status.HTTP_201_CREATED
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alternative_feed_view(request):
    custom_data = {
        "status": "success",
        "current_user": request.user.username,
        "view_name": "Alternative Feed",
        "announcement": f"Hello {request.user.username}, here is your feed! quack quack quack!",
        "items": [
            {
                "id": 101,
                "source": "System",
                "update": "This data from the new endpoint"
            }
        ]
    }
    return Response(custom_data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def posts_view(request):
    if request.method == 'GET':
        posts = Post.objects.select_related('user').order_by('-created_at', '-id')
        return Response({
            "current_user": request.user.username,
            "posts": [
                {
                    "id": post.id,
                    "author": post.user.username,
                    "content": post.content,
                    "created_at": post.created_at,
                    "is_mine": post.user_id == request.user.id,
                }
                for post in posts
            ]
        })

    content = request.data.get('content', '').strip()
    if not content:
        return Response(
            {"error": "Post content is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if len(content) > 500:
        return Response(
            {"error": "Posts must be 500 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST
        )

    post = Post.objects.create(user=request.user, content=content)
    return Response({
        "id": post.id,
        "author": post.user.username,
        "content": post.content,
        "created_at": post.created_at,
        "is_mine": True,
    }, status=status.HTTP_201_CREATED)
class ActiveUserRegistryView(APIView):
    """List active users other than the authenticated requester."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(is_active=True).exclude(
            pk=request.user.pk
        ).order_by('username')

        return Response({
            'total_user_count': users.count(),
            'users': [
                {
                    'id': user.id,
                    'username': user.username,
                }
                for user in users
            ],
        })


class DirectMessagePipelineView(APIView):
    """Read or send direct messages for the authenticated user."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        username = request.query_params.get('username', '').strip()
        if not username:
            return Response(
                {'error': 'A username is required to open a conversation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            other_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': 'That user does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        messages = TextMessage.objects.filter(
            Q(sender=request.user, recipient=other_user)
            | Q(sender=other_user, recipient=request.user)
        ).select_related(
            'sender',
            'recipient'
        ).order_by('timestamp', 'id')

        return Response({
            'conversation_with': other_user.username,
            'messages': [
                {
                    'id': message.id,
                    'sender': message.sender.username,
                    'recipient': message.recipient.username,
                    'message_text': message.message_text,
                    'timestamp': message.timestamp,
                    'is_mine': message.sender_id == request.user.id,
                }
                for message in messages
            ],
        })

    def post(self, request):
        recipient_name = request.data.get('recipient', '').strip()
        message_text = request.data.get('message', '').strip()
        if not recipient_name or not message_text:
            return Response(
                {'error': 'Both recipient and message are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(message_text) > 2000:
            return Response(
                {'error': 'Messages must be 2000 characters or fewer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if recipient_name == request.user.username:
            return Response(
                {'error': 'You cannot send a direct message to yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            recipient = User.objects.get(username=recipient_name)
        except User.DoesNotExist:
            return Response(
                {'error': 'That user does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        message = TextMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            message_text=message_text
        )
        return Response({
            'id': message.id,
            'sender': request.user.username,
            'recipient': recipient.username,
            'message_text': message.message_text,
            'timestamp': message.timestamp,
            'is_mine': True,
        }, status=status.HTTP_201_CREATED)
