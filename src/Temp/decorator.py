from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from Temp.message import result_message

def admin_required(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(result_message("ERROR", status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        return func(self, request, *args, **kwargs)
    return wrapper