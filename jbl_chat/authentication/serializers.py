from random import random
from django.core.exceptions import ValidationErr
from django.contrib.auth.models import User
from .models import Profile
from rest_framework import serializers


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'
        extra_kwargs = {
            'user': {"required": False, "allow_null": True}
        }

class UserBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    last_login = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = User
        exclude = ("groups", "user_permissions")
        extra_kwargs = {'password': {'write_only':True}}
        
    def create(self, validated_data):
        # create user 
        profile_data = validated_data.pop('profile')
        user: User= User.objects.create(
            **validated_data
        )
        user.set_password(validated_data['password'])
        user.save()

        # updating user profile
        profile_data['user'] = user.id
        profile_ser = UserProfileSerializer(instance=user.profile, data=profile_data)
        if profile_ser.is_valid():
            profile_ser.save()
            return user

        raise ValidationErr(profile_ser.errors)
