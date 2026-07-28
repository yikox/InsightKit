"""演示上下文管理器与结构化输出（v0.0.4 新增）。"""

import json
import time

from insight_kit import AT


def flaky(step):
    """模拟一个偶尔失败的步骤。"""
    time.sleep(0.02)
    if step == "bad":
        raise RuntimeError("boom")


if __name__ == "__main__":
    # 1. with AT.record(name): 异常安全的打点，无需手动 begin/end 配对
    with AT.record("Main"):
        time.sleep(0.05)
        for _ in range(3):
            with AT.record("Step"):
                time.sleep(0.01)
        try:
            with AT.record("MayFail"):
                flaky("bad")
        except RuntimeError:
            pass  # 即使块内抛异常，MayFail 的计时也已正确结束

    print(AT)

    # 2. 结构化输出：to_dict() / to_json()，可直接喂给 wandb / tensorboard
    print(json.dumps(AT.to_dict(), ensure_ascii=False))

    # 3. with AT.experiment(tag): 独立实验轮次，退出后历史数据自动恢复
    baseline = len(AT.records)
    with AT.experiment("exp1"):
        with AT.record("only_in_exp1"):
            time.sleep(0.03)
        print("---- experiment exp1 ----")
        print(AT)
    assert len(AT.records) == baseline, "实验块退出后应恢复历史数据"
    print("---- history restored, exp1 数据未泄露到全局 ----")
