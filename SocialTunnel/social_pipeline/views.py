from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView

from .models import Post, Text as TextMessage


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
class ActiveUserRegistryView(APIView):
    """
    Return active accounts other than the account making the request.

    The request first passes through JWT authentication and the authenticated
    permission check. The GET handler then filters the User table to records
    whose is_active field is true, excludes the authenticated user's primary
    key, counts the remaining records, and serializes each record's id and
    username into the users array.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Apply the active-account and current-user filters in sequence.

        First, filter(is_active=True) limits the queryset to enabled accounts.
        Next, exclude(pk=request.user.pk) removes the authenticated requester,
        so that account is not included in either the count or the array.
        Finally, count() calculates total_user_count, and iteration over the
        same queryset creates one JSON-ready object per remaining account.
        """
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
    """
    Read a two-way conversation or save a direct message.

    JWT authentication runs before either handler, and IsAuthenticated
    prevents anonymous callers from reading or writing private messages. The
    existing Text model is imported as TextMessage here so the query code
    names the message records descriptively without changing the database
    model or requiring a migration.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return messages exchanged with the username in the query string.

        First, trim the username parameter so surrounding whitespace does not
        change the account lookup. If it is missing, return a 400 response. If
        User.objects.get cannot find that username, return 404. Otherwise,
        build one Q condition for messages sent by the requester to that user
        and a second Q condition for messages sent in the opposite direction.
        The | operator combines those conditions as an OR, so the resulting
        queryset contains both sides of the mutual conversation. Related user
        rows are fetched with select_related, and order_by returns messages in
        timestamp and id order before they are serialized.
        """
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
        """
        Validate the destination and text, then insert one message record.

        First, trim recipient and message values from the JSON request body.
        Reject missing values, overlong text, or a request to message oneself.
        Next, look up the recipient by username and return 404 if no account
        matches. Finally, create the database row with request.user as sender,
        so a caller cannot choose a different sender in the request body, and
        return the saved record with an HTTP 201 response.
        """
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
