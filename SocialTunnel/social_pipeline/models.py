from django.db import models
from django.contrib.auth.models import User

#defining models
#model for making posts
class Post(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} : {self.content[:20]}"

#model for sending texts
class Text(models.Model):
    sender = models.ForeignKey(User,on_delete=models.CASCADE, related_name='sender')
    recipient = models.ForeignKey(User,on_delete=models.CASCADE, related_name='recipient')
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"from {self.sender.username} to {self.recipient.username}"






