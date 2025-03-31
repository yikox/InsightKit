
from .analysis import AT

def at_record(arg):
    if callable(arg):
        # 没有参数的情况：tag是函数名, arg 就是 func
        func = arg
        def decorator(*args, **kwargs):
            AT.begin_record(func.__name__)
            result = func(*args, **kwargs)
            AT.end_record(func.__name__)
            return result
        return decorator
        
    else:
        # 带参数的情况：tag是参数
        def wrapper(func):
            def decorator(*args, **kwargs):
                AT.begin_record(arg)
                result = func(*args, **kwargs)
                AT.end_record(arg)
                return result
            return decorator
        return wrapper


