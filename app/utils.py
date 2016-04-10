import datetime
import os

try:
    import pwd
except ImportError:
    import getpass

    pwd = None


def now():
    """
    Get a datedate object representing the current UTC time.

    :return:
    """
    return datetime.datetime.utcnow()


def current_user():
    """
    http://stackoverflow.com/a/19865396

    :return:
    """
    if pwd:
        return pwd.getpwuid(os.geteuid()).pw_name
    else:
        return getpass.getuser()
