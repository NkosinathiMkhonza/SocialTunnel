# social_pipeline/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Post, Text


# Connected to /api/register/ in config/urls.py.
@api_view(['POST'])
@permission_classes([AllowAny])  # Open endpoint for creating an account
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

    # hashes the password automatically
    user = User.objects.create_user(username=username, password=password)
    return Response(
        {"status": "success", "message": f"User {user.username} created successfully!"},
        status=status.HTTP_201_CREATED
    )

# Connected to /social_pipeline/new-feed/ in config/urls.py.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alternative_feed_view(request):
    custom_data = {
        "status": "success",
        "current_user": request.user.username,
        "view_name": "Alternative Feed",
        "announcement": f"Hello {request.user.username}, here is your feed! quack quack quack!",
        #returning data dictionary from the database
        "items": [
            {
                "id": 101,
                "source": "System",
                "update": "This data from the new endpoint"
            }
        ]
    }
    return Response(custom_data)


# Connected to /api/posts/ in config/urls.py.
# GET shows posts; POST saves a new post for the signed-in user.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def posts_view(request):
    if request.method == 'GET':
        # Show newest posts first. Also fetch each author's name along with the post.
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

    # A browser can be changed or bypassed, so check the post text here as well.
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

    # Use the signed-in account as the author; do not trust a name sent by the browser.
    post = Post.objects.create(user=request.user, content=content)
    return Response({
        "id": post.id,
        "author": post.user.username,
        "content": post.content,
        "created_at": post.created_at,
        "is_mine": True,
    }, status=status.HTTP_201_CREATED)


# Connected to /api/messages/ in config/urls.py.
# GET reads a conversation; POST saves a message to another user.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def messages_view(request):
    if request.method == 'GET':
        # Find the other account named in the page's conversation box.
        username = request.query_params.get('username', '').strip()
        if not username:
            return Response(
                {"error": "A username is required to open a conversation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            other_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"error": "That user does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Return messages in both directions between this user and the other user.
        messages = Text.objects.filter(
            Q(sender=request.user, recipient=other_user) |
            Q(sender=other_user, recipient=request.user)
        ).select_related('sender', 'recipient').order_by('timestamp', 'id')
        return Response({
            "conversation_with": other_user.username,
            "messages": [
                {
                    "id": message.id,
                    "sender": message.sender.username,
                    "recipient": message.recipient.username,
                    "message_text": message.message_text,
                    "timestamp": message.timestamp,
                    "is_mine": message.sender_id == request.user.id,
                }
                for message in messages
            ]
        })

    # For a new message, read the destination name and message text from the request.
    recipient_name = request.data.get('recipient', '').strip()
    message_text = request.data.get('message', '').strip()
    if not recipient_name or not message_text:
        return Response(
            {"error": "Both recipient and message are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if len(message_text) > 2000:
        return Response(
            {"error": "Messages must be 2000 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if recipient_name == request.user.username:
        return Response(
            {"error": "You cannot send a direct message to yourself."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        recipient = User.objects.get(username=recipient_name)
    except User.DoesNotExist:
        return Response(
            {"error": "That user does not exist."},
            status=status.HTTP_404_NOT_FOUND
        )

    # The logged-in account is always the sender of a message it submits.
    message = Text.objects.create(
        sender=request.user,
        recipient=recipient,
        message_text=message_text
    )
    return Response({
        "id": message.id,
        "sender": request.user.username,
        "recipient": recipient.username,
        "message_text": message.message_text,
        "timestamp": message.timestamp,
        "is_mine": True,
    }, status=status.HTTP_201_CREATED)
