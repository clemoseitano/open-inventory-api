import os
import os
import uuid
from pathlib import Path

from celery.result import AsyncResult
from django.conf import settings
from rest_framework import permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_202_ACCEPTED,
)
from rest_framework.views import APIView

from discovery.models import Product
from discovery.permissions import IsOwnerOrStaff
from discovery.serializers import (
    ProductSerializer,
)
from discovery.tasks import process_product_images, process_structured_text
from service.celery import app


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

        if res.state == "SUCCESS":
            return Response(
                {"status": "success", "result": res.result}, status=status.HTTP_200_OK
            )
        elif res.state == "FAILURE":
            return Response(
                {"status": "error", "error": str(res.result)}, status=status.HTTP_200_OK
            )
        else:
            return Response({"status": "pending"}, status=status.HTTP_200_OK)
