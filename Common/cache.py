import inspect
import types


class make_cache:
    def __init__(self, func):
        self.func = func

        fargspec = inspect.getfullargspec(func)
        if len(fargspec.args) != 1 or fargspec.args[0] != "self":
            raise Exception("@memoize must be `(self)`")

        # set key for this function
        self.func_key = str(func)

    def __get__(self, instance, cls):
        if instance is None:
            raise Exception("@memoize's must be bound")

        if not hasattr(instance, "_memoize_cache"):
            setattr(instance, "_memoize_cache", {})

        return types.MethodType(self, instance)

    def __call__(self, *args, **kwargs):
        instance = args[0]
        cache = instance._memoize_cache

        if self.func_key in cache:
            return cache[self.func_key]

        result = self.func(*args, **kwargs)
        cache[self.func_key] = result
        return result
