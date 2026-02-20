import os

from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from discovery.models import SyncJournal, SyncPushLog, TenantMember
from discovery.serializers import SyncActionSerializer, SyncJournalSerializer
from discovery.services.tenant_manager import TenantDatabaseManager


class SyncPushView(APIView):
    def post(self, request):
        tenant_slug = request.data.get("tenant_slug")
        if not tenant_slug:
            return Response(
                {"error": "tenant_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            membership = TenantMember.objects.get(
                user=request.user, tenant__slug=tenant_slug
            )
        except TenantMember.DoesNotExist:
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        tenant = membership.tenant
        TenantDatabaseManager.initialize_tenant_db(tenant.slug)

        actions_data = request.data.get("actions", [])

        # 1. Log raw push for auditing
        SyncPushLog.objects.create(
            tenant=tenant, tenant_member=membership, data=request.data
        )

        serializer = SyncActionSerializer(data=actions_data, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for action in serializer.validated_data:
                if SyncJournal.objects.filter(action_id=action["id"]).exists():
                    continue

                # 2. Record in Journal (Pull table)
                SyncJournal.objects.create(
                    tenant=tenant,
                    tenant_member=membership,
                    action_id=action["id"],
                    action_type=action["actionType"],
                    payload=action["payload"],
                )

                # 3. Apply to SQLite Snapshot
                TenantDatabaseManager.apply_action(
                    tenant.slug, action["actionType"], action["payload"]
                )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SyncPullView(APIView):
    def get(self, request):
        tenant_slug = request.query_params.get("tenant_slug")
        since = request.query_params.get("since", "1970-01-01 00:00:00")

        if not tenant_slug:
            return Response(
                {"error": "tenant_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            membership = TenantMember.objects.get(
                user=request.user, tenant__slug=tenant_slug
            )
        except TenantMember.DoesNotExist:
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # REBASE CHECK: Is the client's timestamp older than our oldest journal entry?
        oldest_entry = (
            SyncJournal.objects.filter(tenant=membership.tenant)
            .order_by("created_at")
            .first()
        )

        if oldest_entry and since < oldest_entry.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        ):
            return Response(
                {
                    "instruction": "FULL_SYNC_REQUIRED",
                    "message": "Your local data is too far behind. Please perform a full database download.",
                },
                status=status.HTTP_410_GONE,
            )

        events = SyncJournal.objects.filter(
            tenant=membership.tenant, created_at__gt=since
        ).exclude(tenant_member=membership)

        serializer = SyncJournalSerializer(events, many=True)
        return Response(serializer.data)


class DownloadDatabaseView(APIView):
    def get(self, request):
        tenant_slug = request.query_params.get("tenant_slug")
        try:
            membership = TenantMember.objects.get(
                user=request.user, tenant__slug=tenant_slug
            )
        except TenantMember.DoesNotExist:
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        db_path = TenantDatabaseManager.get_db_path(membership.tenant.slug)
        if not os.path.exists(db_path):
            return Response(
                {"error": "Database not initialized"}, status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(db_path, "rb"),
            as_attachment=True,
            filename=f"{membership.tenant.slug}.db",
        )
