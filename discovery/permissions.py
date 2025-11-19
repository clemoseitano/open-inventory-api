from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrStaff(BasePermission):
    """
    The request is authenticated as a user for read-only, and as a staff for read-write request.
    """

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated) and bool(
            request.user == obj.user or request.user.is_staff
        )
