import json
import uuid

from django.contrib import messages
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_408_REQUEST_TIMEOUT,
)
from rest_framework.views import APIView

from discovery import services
from discovery.serializers import (
    RegistrationSerializer,
    LoginSerializer,
)
from discovery.utils import account_activation_token, password_reset_token


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"success": "User registered successfully"}, status=HTTP_200_OK
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ActivateAccountView(generics.CreateAPIView):
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()

            messages.success(
                request,
                "Your email has been verified successfully. Now you can login to your account.",
            )
            return Response(
                {"success": "User email verified successfully"}, status=HTTP_200_OK
            )

        else:
            messages.error(request, "Activation link is invalid!")
            return Response(
                {"error": "Activation link is invalid!"}, status=HTTP_404_NOT_FOUND
            )


class LoginView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        print(request.data)
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        print(type(user))
        if user is not None and not isinstance(user, AnonymousUser):
            # Get access tokens
            token = services.generate_access_token(user)
            serializer = LoginSerializer(user)
            return Response(
                {"user": {**serializer.data}, "token": token}, status=HTTP_200_OK
            )
        return Response(
            {"error": "Invalid email or password"}, status=HTTP_401_UNAUTHORIZED
        )


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "")
        user = User.objects.filter(email=email)
        if not user:
            return Response({"error": "Invalid email"}, status=HTTP_404_NOT_FOUND)

        email_token = str(uuid.uuid4())
        site_url = get_current_site().domain
        template_args = {
            "user": user.username,
            "domain": site_url,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": password_reset_token.make_token(user),
        }
        task_args = [
            email,
            "Password Reset",
            "password_reset_email.html",
            json.dumps(template_args),
            email_token,
        ]

        services.schedule_email(task_args, email_token)
        return Response(
            {"success": f"Email will be sent to {email} in a moment"},
            status=HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and password_reset_token.check_token(user, token):
            password = request.data.get("password")
            try:
                password_validation.validate_password(password, user=user)
            except ValidationError as e:
                return Response({"error": e.errors}, status=HTTP_400_BAD_REQUEST)
            user.set_password(password)
            user.save()
            return Response(
                {"success": "Password updated successfully"}, status=HTTP_200_OK
            )
        return Response(
            {"error": "Password could not be updated"}, status=HTTP_408_REQUEST_TIMEOUT
        )
