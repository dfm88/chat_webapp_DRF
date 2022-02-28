from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.authentication import BasicAuthentication
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from authentication.serializers import  UserSerializer
from rest_framework.response import Response
from rest_framework import status



class UserListCreateAPIView(generics.ListCreateAPIView):
    # permission_classes = (IsAuthenticated, BasicAuthentication, SessionAuthentication)
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "id",
        "username",
        "first_name",
        "last_name",
        "profile__status"
    ]

    @transaction.atomic
    def post(self, request, format=None):
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response(str(ex), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes = (IsAuthenticated, BasicAuthentication, SessionAuthentication)
    queryset = User.objects.all()
    serializer_class = UserSerializer