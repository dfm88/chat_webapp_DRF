from django.db.models.signals import post_delete
from django.dispatch import receiver

from chat.models import ChatRoom
from .models import Membership
from django.utils import timezone
from django.dispatch import Signal


# Chat Room
@receiver(post_delete, sender=Membership)
def delete_membership(sender, instance: Membership, **kwargs):
    # set the value of 'date_lefted' in the Membership relation
    leave_date = timezone.now()
    instance.date_lefted = leave_date
    instance.save()


@receiver(post_delete, sender=Membership)
def delete_chatroom(sender, instance: Membership, **kwargs):
    # if no member is left in the chat room, delete it
    import ipdb; ipdb.set_trace()
    if not Membership.objects.filter(
        chatroom_id=instance.chatroom_id,
        date_lefted__isnull=True
    ):
        # disable signals to avoid recursion
        Signal.disconnect(post_delete, receiver=delete_chatroom, sender=Membership)
        Signal.disconnect(post_delete, receiver=delete_membership, sender=Membership)
        ChatRoom.objects.filter(pk=instance.chatroom_id).delete


