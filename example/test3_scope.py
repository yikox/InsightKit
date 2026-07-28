import time
from insight_kit import AT, at_record, at_scope


@at_record
def block_a():
    time.sleep(0.05)


@at_scope("my_exp")          # 进入即 reset，退出自动 print(AT)
def run_exp():
    AT.begin_record("Main")
    block_a()
    for _ in range(3):
        AT.begin_record("Loop")
        time.sleep(0.01)
        AT.end_record("Loop")
    AT.end_record("Main")


@at_scope                   # 裸用：tag 取函数名，这里即 "failing_exp"
def failing_exp():
    AT.begin_record("Main")
    time.sleep(0.02)
    raise RuntimeError("boom")


if __name__ == "__main__":
    run_exp()
    try:
        failing_exp()       # 异常退出也会先打印本轮已有的统计，再抛出
    except RuntimeError:
        pass
