
import functools

from .analysis import AT

def at_record(arg):
    if callable(arg):
        # 没有参数的情况：tag是函数名, arg 就是 func
        func = arg
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            AT.begin_record(func.__name__)
            try:
                return func(*args, **kwargs)
            finally:
                AT.end_record(func.__name__)
        return decorator

    else:
        # 带参数的情况：tag是参数
        name = arg
        def wrapper(func):
            @functools.wraps(func)
            def decorator(*args, **kwargs):
                AT.begin_record(name)
                try:
                    return func(*args, **kwargs)
                finally:
                    AT.end_record(name)
            return decorator
        return wrapper


def at_scope(arg=None, *, print_result=True, save_to=None):
    """把一次函数调用标记为一轮独立的计时范围。

    进入时 ``AT.reset(tag)`` 清空全部历史数据，正常或异常退出时
    在 ``finally`` 里输出 / 保存本轮统计结果。

    支持裸用（``@at_scope``，tag 取函数名）和带参数（``@at_scope("exp1")``）。

    注意：``AT`` 是全局单例，进入 scope 会清空此前所有累计数据；
    请仅在"一次实验的入口函数"上使用该装饰器，不要在嵌套的内部函数上使用。
    """
    def wrapper(func):
        tag = arg if isinstance(arg, str) else func.__name__
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            AT.reset(tag)
            try:
                return func(*args, **kwargs)
            finally:
                if print_result:
                    print(AT)
                if save_to is not None:
                    AT.save(save_to)
        return decorator

    if callable(arg):
        # @at_scope 裸用：arg 就是 func
        return wrapper(arg)
    return wrapper
