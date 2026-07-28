
import functools

from .analysis import AT


def at_record(arg):
    """装饰器：把整个函数体作为一次计时记录。

    支持裸用（``@at_record``，tag 取函数名）和带标签（``@at_record("自定义")``）。
    内部基于 ``with AT.record(...)``，函数抛异常时也会正确结束计时。
    """
    def wrapper(tag):
        def decorator(func):
            @functools.wraps(func)
            def wrapper_fn(*args, **kwargs):
                with AT.record(tag):
                    return func(*args, **kwargs)
            return wrapper_fn
        return decorator

    if callable(arg):
        # 裸用：@at_record，tag 取函数名
        return wrapper(arg.__name__)(arg)
    # 带参：@at_record("自定义标签")
    return wrapper(arg)


def at_scope(arg=None, *, print_result=True, save_to=None):
    """装饰器：把一次函数调用标记为一轮独立实验。

    基于 ``with AT.experiment(tag)``：
    - 进入时对本轮统计使用独立根标签，**不影响也不清空**调用前的历史数据；
    - 正常或异常退出时，先输出/保存本轮统计，再自动恢复历史数据。

    因此它可以安全地多次调用、嵌套使用——此前版本会 ``reset()`` 掉全局
    数据的副作用已移除。

    支持裸用（``@at_scope``，tag 取函数名）和带参数（``@at_scope("exp1")``）。
    ``print_result=False`` 关闭自动打印；``save_to="path"`` 退出时顺带保存。
    """
    def wrapper(func):
        tag = arg if isinstance(arg, str) else func.__name__

        @functools.wraps(func)
        def decorator(*args, **kwargs):
            with AT.experiment(tag):
                try:
                    return func(*args, **kwargs)
                finally:
                    # 异常路径下也先落盘/打印本轮已有的统计
                    if print_result:
                        print(AT)
                    if save_to is not None:
                        AT.save(save_to)

        return decorator

    if callable(arg):
        # @at_scope 裸用：arg 就是 func
        return wrapper(arg)
    return wrapper
