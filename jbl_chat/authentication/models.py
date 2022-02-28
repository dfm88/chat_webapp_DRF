from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Profile(models.Model):
    class Status(models.TextChoices):
        online="Online",
        busy="Busy",
        offline="Offline"
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=Status.choices, blank=True, null=True, default=Status.offline)
    status_msg = models.CharField(max_length=255, blank=True, null=True, verbose_name="Status message")



    def __str__(self):
        return ("%s profile" % self.user.username)