from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    """
    Allows access only to super users.
    """

    def has_permission(self, request, view):
        # فقط به کاربرانی که is_superuser=True دارند اجازه دسترسی می‌دهد
        return bool(request.user and request.user.is_superuser)