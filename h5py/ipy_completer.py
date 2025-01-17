#+
#
# This file is part of h5py, a low-level Python interface to the HDF5 library.
#
# Contributed by Darren Dale
#
# Copyright (C) 2009 Darren Dale
#
# http://h5py.org
# License: BSD  (See LICENSE.txt for full license)
#
#-

# pylint: disable=eval-used,protected-access

"""
    This is the h5py completer extension for ipython.  It is loaded by
    calling the function h5py.enable_ipython_completer() from within an
    interactive IPython session.

    It will let you do things like::

      f=File('foo.h5')
      f['<tab>
      # or:
      f['ite<tab>

    which will do tab completion based on the subgroups of `f`. Also::

      f['item1'].at<tab>

    will perform tab completion for the attributes in the usual way. This should
    also work::

      a = b = f['item1'].attrs.<tab>

    as should::

      f['item1/item2/it<tab>
"""

import posixpath
import re
try:
    import readline
except ImportError:
    readline = None
from warnings import warn
from ._hl.attrs import AttributeManager
from ._hl.base import HLObject


try:
    # >=ipython-1.0
    from IPython import get_ipython
except ImportError:
    try:
        # support >=ipython-0.11, <ipython-1.0
        from IPython.core.ipapi import get as get_ipython
    except ImportError:
        # support <ipython-0.11
        from IPython.ipapi import get as get_ipython
try:
    # support >=ipython-0.11
    from IPython.utils import generics
except ImportError:
    # support <ipython-0.11
    from IPython import generics

try:
    from IPython.core.error import TryNext
except ImportError:
    try:
        from IPython import TryNext
    except ImportError:
        from IPython.ipapi import TryNext

re_attr_match = re.compile(r"(?:.*\=)?(.+\[.*\].*)\.(\w*)$")
re_item_match = re.compile(r"""(?:.*\=)?(.*)\[(?P<s>['|"])(?!.*(?P=s))(.*)$""")
re_object_match = re.compile(r"(?:.*\=)?(.+?)(?:\[)")


def _retrieve_obj(name, context):
    """ Filter function for completion. """

    # we don't want to call any functions, but I couldn't find a robust regex
    # that filtered them without unintended side effects. So keys containing
    # "(" will not complete.

    if '(' in name:
        raise ValueError()

    try:
        # older versions of IPython:
        obj = eval(name, context.shell.user_ns)
    except AttributeError:
        # as of IPython-1.0:
        obj = eval(name, context.user_ns)
    return obj


def h5py_item_completer(context, command):
    """Compute possible item matches for dict-like objects"""

    base, item = re_item_match.split(command)[1:4:2]

    try:
        obj = _retrieve_obj(base, context)
    except Exception:
        return []

    path, _ = posixpath.split(item)

    try:
        if path:
            items = (posixpath.join(path, name) for name in obj[path].keys())
        else:
            items = obj.keys()
    except AttributeError:
        return []

    items = list(items)
    readline.set_completer_delims(' \t\n`!@#$^&*()=+[{]}\\|;:\'",<>?')

    return [i for i in items if i[:len(item)] == item]


def h5py_attr_completer(context, command):
    """Compute possible attr matches for nested dict-like objects"""

    base, attr = re_attr_match.split(command)[1:3]
    base = base.strip()

    try:
        obj = _retrieve_obj(base, context)
    except Exception:
        return []

    attrs = dir(obj)
    try:
        attrs = generics.complete_object(obj, attrs)
    except TryNext:
        pass

    omit__names = None
    try:
        # support >=ipython-0.12
        omit__names = get_ipython().Completer.omit__names
    except AttributeError:
        pass
    if omit__names is None:
        try:
            # support ipython-0.11
            omit__names = get_ipython().readline_omit__names
        except AttributeError:
            pass
    if omit__names is None:
        try:
            # support <ipython-0.11
            omit__names = get_ipython().options.readline_omit__names
        except AttributeError:
            omit__names = 0
    if omit__names == 1:
        attrs = [a for a in attrs if not a.startswith('__')]
    elif omit__names == 2:
        attrs = [a for a in attrs if not a.startswith('_')]

    readline.set_completer_delims(' =')

    return ["%s.%s" % (base, a) for a in attrs if a[:len(attr)] == attr]


def h5py_completer(self, event):
    """ Completer function to be loaded into IPython """
    base = re_object_match.split(event.line)[1]

    if not isinstance(self._ofind(base).get('obj'), (AttributeManager, HLObject)):
        raise TryNext

    try:
        return h5py_attr_completer(self, event.line)
    except ValueError:
        pass

    try:
        return h5py_item_completer(self, event.line)
    except ValueError:
        pass

    return []


def load_ipython_extension(ip=None):
    """ Load completer function into IPython """
    if readline:
        if ip is None:
            ip = get_ipython()
        ip.set_hook('complete_command', h5py_completer, re_key=r"(?:.*\=)?(.+?)\[")
    else:
        warn("Readline is not available to enable completions.")
