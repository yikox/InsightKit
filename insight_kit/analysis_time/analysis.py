
import json
import time
import warnings
from contextlib import contextmanager

# 判断 torch 和 cuda 是否可用；不可用时 cuda_sync 自动跳过
CUDA_AVAILABLE = False
try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    pass


class Record:
    """单个计时节点的累计数据：各次耗时与次数。

    仅保存每次耗时与计数，均值/分位数等派生指标在输出时计算，
    保证 ``print(AT)`` 这类只读操作永远不修改内部状态、不产生副作用。
    """

    def __init__(self, name, parent_tag):
        self.name = name
        self.parent_tag = parent_tag  # 父节点的全路径 tag
        self.elapsed_lst = []         # 各次完成耗时（秒）
        self.begin_time = None        # 未完成的 begin 时刻；None 表示空闲

    @property
    def count(self):
        return len(self.elapsed_lst)

    @property
    def total(self):
        return sum(self.elapsed_lst)

    @property
    def avg(self):
        return self.total / len(self.elapsed_lst) if self.elapsed_lst else 0.0

    @property
    def min(self):
        return min(self.elapsed_lst) if self.elapsed_lst else 0.0

    @property
    def max(self):
        return max(self.elapsed_lst) if self.elapsed_lst else 0.0

    def percentile(self, p):
        """p ∈ [0,100] 的分位数（线性插值）；无数据返回 0.0。"""
        if not self.elapsed_lst:
            return 0.0
        ordered = sorted(self.elapsed_lst)
        if len(ordered) == 1:
            return ordered[0]
        pos = (len(ordered) - 1) * p / 100.0
        lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
        frac = pos - lo
        return ordered[lo] * (1 - frac) + ordered[hi] * frac

    def add_record(self, t):
        if self.begin_time is None:
            warnings.warn(f"[ATimer] record {self.name!r} ended before it began; ignored")
            return
        self.elapsed_lst.append(t - self.begin_time)
        self.begin_time = None

    def to_dict(self):
        return {
            "name": self.name,
            "parent": self.parent_tag,
            "count": self.count,
            "avg": self.avg,
            "min": self.min,
            "max": self.max,
            "p95": self.percentile(95),
            "total": self.total,
        }

    def __str__(self, tag_len):
        if self.count > 0:
            stats = (
                f"Avg: {self.avg:.4f}, Min: {self.min:.4f}, "
                f"Max: {self.max:.4f}, Total: {self.total:.4f}"
            )
        else:
            # 记录仍在进行中（未 end_record，如异常中断），无统计可算
            stats = "Avg: -, Min: -, Max: -, Total: -"
        return f"{self.name[:tag_len].ljust(tag_len)}: Count: {self.count}, {stats}"


class Analysis:
    """全局单例式耗时分析器。

    打点用嵌套的标签栈管理，支持三种使用姿势：
    - ``begin_record`` / ``end_record`` 手动打点；
    - ``with AT.record(name):`` 上下文管理器（异常安全，无需手动配对）;
    - ``with AT.experiment(tag):`` 把一段代码标记为独立实验，退出时恢复
      此前的历史数据（可安全嵌套；打印由调用方在块内自行触发，
      或由装饰器 ``at_scope`` 自动完成）。
    """

    def __init__(self, atag="AT"):
        self.records = {}     # key: 全路径 tag, value: Record
        self.a_tag = atag     # 根标签
        self.parent_tag = atag
        self.current_tag = [] # 正在计时的标签栈
        self.close_flag = False
        self.cuda_sync = False
        self._cuda_warned = False

    # ------------------------------------------------------------------ #
    # 控制开关
    # ------------------------------------------------------------------ #
    def close(self):
        self.close_flag = True
        self.reset()

    def reset(self, atag="AT"):
        """清空全部记录并重置根标签与计时栈。"""
        self.records = {}
        self.a_tag = atag
        self.parent_tag = atag
        self.current_tag = []

    def set_cuda_sync(self, cuda_sync):
        if not cuda_sync:
            self.cuda_sync = False
            return
        self.cuda_sync = CUDA_AVAILABLE
        # 用户明确要求同步但环境不支持：提示一次，避免其误以为计时已含同步
        if not CUDA_AVAILABLE and not self._cuda_warned:
            self._cuda_warned = True
            warnings.warn(
                "[ATimer] set_cuda_sync(True) 需要 torch 且 CUDA 可用；"
                "当前环境不满足，已自动跳过同步，计时不含 cuda.synchronize()"
            )

    def _sync(self):
        if self.cuda_sync:
            torch.cuda.synchronize()

    # ------------------------------------------------------------------ #
    # 内部状态快照/恢复（供 experiment 使用）
    # ------------------------------------------------------------------ #
    def _snapshot(self):
        return {
            "records": dict(self.records),
            "a_tag": self.a_tag,
            "parent_tag": self.parent_tag,
            "current_tag": list(self.current_tag),
        }

    def _restore(self, snap):
        self.records = snap["records"]
        self.a_tag = snap["a_tag"]
        self.parent_tag = snap["parent_tag"]
        self.current_tag = snap["current_tag"]

    # ------------------------------------------------------------------ #
    # 打点
    # ------------------------------------------------------------------ #
    def begin_record(self, name):
        if self.close_flag:
            return
        tag = self.parent_tag + "/" + name
        self._sync()
        t = time.time()
        record = self.records.get(tag)
        if record is not None and record.begin_time is not None:
            warnings.warn(
                f"[ATimer] record {tag!r} is already running; re-beginning overwrites its start time"
            )
        if record is None:
            record = Record(name, self.parent_tag)
            self.records[tag] = record
        record.begin_time = t
        self.current_tag.append(tag)
        self.parent_tag = tag

    def end_record(self, name=None):
        if self.close_flag:
            return
        if not self.current_tag:
            warnings.warn("[ATimer] end_record() called but the stack is empty; ignored")
            return
        top = self.current_tag.pop()
        if name is not None and top.split("/")[-1] != name:
            # 名称不匹配：把栈顶放回去，保持状态一致，避免后续记录挂错父级
            self.current_tag.append(top)
            warnings.warn(
                f"[ATimer] end_record({name!r}) 与栈顶 {top.split('/')[-1]!r} 不匹配；"
                f"本次调用已被忽略，请检查 begin/end 是否配对"
            )
            return
        self._sync()
        t = time.time()
        record = self.records[top]
        record.add_record(t)
        self.parent_tag = record.parent_tag

    # ------------------------------------------------------------------ #
    # 上下文管理器
    # ------------------------------------------------------------------ #
    @contextmanager
    def record(self, name):
        """把代码块作为一次计时记录，块内抛异常也会正确结束计时。"""
        self.begin_record(name)
        try:
            yield
        finally:
            self.end_record(name)

    @contextmanager
    def experiment(self, tag=None):
        """把代码块标记为一轮独立实验。

        进入时对历史数据做快照，退出时（正常或异常）**恢复**此前的
        历史数据——因此可安全嵌套、多次调用，互不破坏。
        实验块内 ``print(AT)`` / ``AT.save()`` 看到的就是纯本轮数据。

        参数 ``tag`` 作为本轮统计的根标签。在块内需要打印/保存时，
        推荐直接使用装饰器 ``at_scope``，它会替你处理。
        """
        snap = self._snapshot()
        self.reset(self.a_tag if tag is None else tag)
        try:
            yield
        finally:
            self._restore(snap)

    # ------------------------------------------------------------------ #
    # 输出
    # ------------------------------------------------------------------ #
    def to_dict(self):
        """以树状结构返回全部记录，便于接入 wandb/tensorboard 等分析流程。"""
        root = {"tag": self.a_tag, "children": []}
        by_tag = {}
        for tag, rec in self.records.items():
            node = rec.to_dict()
            node["tag"] = tag
            node["children"] = []
            by_tag[tag] = node
        for tag, rec in self.records.items():
            node = by_tag[tag]
            parent = by_tag.get(rec.parent_tag)
            (parent["children"] if parent else root["children"]).append(node)
        return root

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def __str__(self):
        if self.close_flag:
            return "Analysis closed."
        if not self.records:
            return f"Analysis Tag: {self.a_tag}\n(empty)"
        try:
            max_tag_len = max(len(rec.name) for rec in self.records.values())
            lines = [f"Analysis Tag: {self.a_tag}"]
            for rec in self.records.values():
                # 沿父链计算缩进；父链异常时用 visited 兜底，绝不清空数据
                depth, ptag, seen = 0, rec.parent_tag, set()
                while ptag != self.a_tag and ptag in self.records and ptag not in seen:
                    seen.add(ptag)
                    depth += 1
                    ptag = self.records[ptag].parent_tag
                lines.append("    " * depth + rec.__str__(max_tag_len))
            return "\n".join(lines)
        except Exception as e:
            # __str__ 是只读操作：出错时报告诊断但保留全部数据
            return (
                f"[ATimer failed] {e}\n"
                f"(已保留 {len(self.records)} 条原始记录，可用 AT.to_dict() 查看)"
            )

    def save(self, path="analysis.txt"):
        if self.close_flag:
            print("Analysis closed.")
            return
        with open(path, "w") as f:
            f.write(str(self))
        print(f"Analysis result saved to {path}")


AT = Analysis("AT")

if __name__ == "__main__":
    # 手动打点
    AT.begin_record("Main")
    time.sleep(0.1)
    AT.begin_record("Sub1")
    time.sleep(0.1)
    AT.end_record("Sub1")
    for i in range(10):
        AT.begin_record("Sub2")
        time.sleep(0.01)
        AT.begin_record("Sub2-1")
        time.sleep(0.01)
        AT.end_record()
        AT.end_record("Sub2")
    AT.end_record("Main")
    AT.begin_record("Main1")
    time.sleep(0.1)
    AT.end_record("Main1")

    # 上下文管理器：异常安全
    with AT.record("CtxMain"):
        time.sleep(0.05)
        try:
            with AT.record("CtxWillRaise"):
                time.sleep(0.02)
                raise RuntimeError("boom")
        except RuntimeError:
            pass

    print(AT)

    # 结构化输出
    print(AT.to_json())

    # 实验块：退出后历史数据自动恢复
    with AT.experiment("exp1"):
        with AT.record("OnlyThisRound"):
            time.sleep(0.03)
        print("---- experiment exp1 report ----")
        print(AT)
    print("---- after experiment, history restored ----")
    print(AT)
