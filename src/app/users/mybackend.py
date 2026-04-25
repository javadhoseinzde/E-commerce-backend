from django.contrib.auth.backends import ModelBackend
from .models import MyUser

class MobileBackend(ModelBackend):
    """
		customize django authentication for otp
    """

    def authenticate(self, request, mobile=None, otp=None, **kwargs):

        if mobile is None or otp is None:
            return None

        try:
            user = MyUser.objects.get(mobile=mobile)

            if not user.is_active:
                return None

            return user

        except MyUser.DoesNotExist:
            return None
        except Exception as e:
            return None