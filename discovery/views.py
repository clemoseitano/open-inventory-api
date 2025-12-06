import os
import secrets
import time
import json
import uuid
from pathlib import Path

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth import authenticate, password_validation
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib import messages
from django.core.exceptions import ValidationError

from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_202_ACCEPTED,
)
from rest_framework.views import APIView

from discovery import services
from discovery.models import Product
from discovery.permissions import IsOwnerOrStaff
from discovery.serializers import (
    RegistrationSerializer,
    LoginSerializer,
    ProductSerializer,
)
from discovery.utils import account_activation_token, password_reset_token
from discovery.tasks import process_product_images, process_structured_text
from service.celery import app


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


class ProductViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """

    permission_classes = [IsOwnerOrStaff]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProcessImagesView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        """
        Accepts multiple image uploads, saves them to a shared volume,
        and triggers a Celery task to process them.
        """
        images = request.FILES.getlist("images")

        # 1. Validate that files were actually uploaded.
        if not images:
            return Response(
                {"error": "No images were provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_paths = []

        # 2. Ensure the media directory exists inside the container.
        # This is a crucial step that prevents errors on the first upload.
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        for uploaded_file in images:
            # 3. Generate a unique filename to prevent collisions.
            # We use a UUID and preserve the original file extension.
            original_extension = Path(uploaded_file.name).suffix
            unique_filename = f"{uuid.uuid4()}{original_extension}"

            # 4. Define the full, absolute path for saving the file inside the container.
            save_path = os.path.join(settings.MEDIA_ROOT, unique_filename)

            # 5. Save the uploaded file to the designated path.
            # This logic reads the file in chunks to efficiently handle large files
            # without consuming too much memory.
            try:
                with open(save_path, "wb+") as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

                # Append the container-absolute path for the Celery worker to use.
                image_paths.append(save_path)

            except IOError as e:
                # Handle potential file system errors (e.g., disk full, permissions)
                return Response(
                    {"error": f"Failed to save file: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # 6. If all files are saved successfully, dispatch the Celery task.
        # The worker will receive a list of paths like: ['/code/media/uuid.jpg', ...]
        task = process_product_images.delay(image_paths)
        print(image_paths)

        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class ProcessTextView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        structured_text = request.data.get("structured_text")
        if not structured_text:
            return Response(
                {"error": "structured_text is required."}, status=HTTP_400_BAD_REQUEST
            )

        task = process_structured_text.delay(structured_text)
        return Response({"task_id": task.id}, status=HTTP_202_ACCEPTED)


class CheckResultView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, task_id, *args, **kwargs):
        res = AsyncResult(task_id, app=app)

        if res.state == 'SUCCESS':
            return Response({'status': 'success', 'result': res.result}, status=status.HTTP_200_OK)
        elif res.state == 'FAILURE':
            return Response({'status': 'error', 'error': str(res.result)}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'pending'}, status=status.HTTP_200_OK)
