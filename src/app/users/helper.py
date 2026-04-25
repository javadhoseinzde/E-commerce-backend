from . import models
import datetime

def check_otp_expiration(mobile):
    try:
        user = models.MyUser.objects.get(mobile=mobile)
        now = datetime.datetime.now()

        otp_time = user.otp_create_time
        diff_time = now - otp_time
        if diff_time.seconds > 30:
            return False
        else:
            return True
    except models.MyUser.DoesNotExist:
        return False