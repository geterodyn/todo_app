from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField(blank=True, null=True)
    trello_key = models.CharField(blank=True, max_length=32)
    trello_secret = models.CharField(blank=True, max_length=64)
    trello_board = models.CharField(blank=True, max_length=24)
	
    def __str__(self):
        return "Профиль пользователя %s" % self.user.username

# Create your models here.
