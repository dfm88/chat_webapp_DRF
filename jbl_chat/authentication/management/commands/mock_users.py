import sys

from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

## LOGGING
import logging
logger = logging.getLogger(__name__)

class MockManager:
    @staticmethod
    def create_user(username, password):
        user, _ = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.save()
        logger.info("creating mock user %s", username)
        return user


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            for i in range(15):
                username = f"user_{i+1}"
                password = "Passw0rd!"
                MockManager.create_user(username=username, password=password)
        except Exception as ex:
            logger.exception(ex)
            sys.exit(1)
