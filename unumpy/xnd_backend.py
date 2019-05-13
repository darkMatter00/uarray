import numpy as np
import xnd
import gumath.functions as fn
import gumath as gu
import uarray as ua
from uarray import DispatchableInstance
from .multimethods import ufunc, ufunc_list, ndarray
import unumpy.multimethods as multimethods
import functools

from typing import Dict

_ufunc_mapping: Dict[ufunc, np.ufunc] = {}

__ua_domain__ = "numpy"


def compat_check(args):
    args = [arg.value if isinstance(arg, DispatchableInstance) else arg for arg in args]
    return all(
        isinstance(arg, (xnd.array, np.generic, gu.gufunc))
        for arg in args
        if arg is not None
    )


_implementations: Dict = {
    multimethods.ufunc.__call__: gu.gufunc.__call__,
    multimethods.ufunc.reduce: gu.reduce,
}


def __ua_function__(method, args, kwargs, dispatchable_args):
    if not compat_check(dispatchable_args):
        return NotImplemented

    if method in _implementations:
        return _implementations[method](*args, **kwargs)

    return _generic(method, args, kwargs, dispatchable_args)


def __ua_coerce__(value, dispatch_type):
    if dispatch_type is ndarray:
        return convert(value) if value is not None else None

    if dispatch_type is ufunc and hasattr(fn, value.name):
        return getattr(fn, value.name)

    return NotImplemented


def replace_self(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        if self not in _ufunc_mapping:
            return NotImplemented

        return func(_ufunc_mapping[self], *args, **kwargs)

    return inner


def _generic(method, args, kwargs, dispatchable_args):
    if not compat_check(dispatchable_args):
        return NotImplemented

    try:
        import numpy as np
        import unumpy.numpy_backend as NumpyBackend
    except ImportError:
        return NotImplemented

    with ua.set_backend(NumpyBackend, coerce=True):
        try:
            out = method(*args, **kwargs)
        except TypeError:
            return NotImplemented

    return convert_out(out)


def convert_out(x):
    if isinstance(x, (tuple, list)):
        return type(x)(map(convert_out, x))

    return convert(x)


def convert(x):
    if isinstance(x, np.ndarray):
        return xnd.array.from_buffer(x)
    elif isinstance(x, np.generic):
        try:
            return xnd.array.from_buffer(memoryview(x))
        except TypeError:
            return NotImplemented
    else:
        return xnd.array(x)
