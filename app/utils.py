import datetime
import os
import textwrap

import terminaltables

try:
    import pwd
except ImportError:
    import getpass

    pwd = None

class BetterAsciiTable(terminaltables.AsciiTable):
    def __init__(self, *args, **kwargs):
        terminaltables.AsciiTable.__init__(self, *args, **kwargs)

    def add_rows(self, rows: list, sort_keys: bool =True, wrap_keys: dict =None):
        """
        Add a bunch of rows to table at once.  Each row should represent a dictionary.

        The table columns are taken from the first item in the list.  Any rows missing a key will
        cause a ValueError to be thrown.  Any extra keys will not be included in the output.

        :param rows: List of dictionaries.
        :param sort_keys: Sort the columns alphabetically.
        :param wrap_keys: A dictionary which is used with textwrap.wraps.  If a row key  is
        present in the dictionary, .wraps() is called w/ the arguments given in this dictionary.
        This allows setting per-key wrapping options.
        :return:
        """
        if wrap_keys is None:
            wrap_keys = {}
        keys = list(rows[0].keys())
        keys = [str(key) for key in keys]
        if sort_keys:
            keys.sort()
        self.table_data = [keys]
        for row in rows:
            t = []
            for k in keys:
                if k not in row:
                    raise ValueError('Row is missing key: {}'.format(k))
                v = str(row.get(k))
                if k in wrap_keys:
                    wrap_args = wrap_keys.get(k)
                    v = '\n'.join(textwrap.wrap(v, **wrap_args))
                t.append(v)
            self.table_data.append(t)


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
