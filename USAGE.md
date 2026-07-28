# InsightKit 使用说明

InsightKit 是一个面向算法性能分析与调优的 Python 工具包，提供**函数级耗时分析**、**GPU/CPU 资源监控**、**图像差异对比**三类能力。

## 一、安装

### 方式 1：安装编译好的 whl（推荐）

```bash
pip install dist/insight_kit-0.0.4-py3-none-any.whl
```

### 方式 2：从 Git 仓库直接安装

```bash
pip install git+https://github.com/yikox/InsightKit.git
```

### 方式 3：从源码自行编译

```bash
pip install build
python -m build --wheel   # 产物位于 dist/ 目录
```

### 依赖说明

| 依赖 | 用途 | 说明 |
|---|---|---|
| `numpy` / `Pillow` / `opencv-python` / `scikit-image` | 图像对比 | 安装 whl 时自动装 |
| `psutil` | CPU/内存监控 | 安装 whl 时自动装 |
| `pynvml` | GPU 信息查询 | 安装 whl 时自动装，**运行需 NVIDIA 驱动** |
| `torch`（可选） | `AT.set_cuda_sync(True)` 时做 CUDA 同步计时 | 未安装则自动跳过同步 |

> ⚠️ macOS / 无 NVIDIA GPU 的机器上，包可正常安装和 `import`，但 GPU 相关功能（`GPUProfiler`、`monitor` 命令）无法运行。

---

## 二、功能模块

### 1. 耗时分析 `analysis_time`（ATimer）

对代码块 / 函数做嵌套式耗时统计，支持树状结果输出。

#### 手动打点

```python
import time
from insight_kit import AT

AT.begin_record("Main")
time.sleep(0.1)
AT.begin_record("Sub1")
time.sleep(0.1)
AT.end_record("Sub1")          # 可省略参数，按栈顶自动匹配

for _ in range(10):
    AT.begin_record("Sub2")
    time.sleep(0.01)
    AT.end_record("Sub2")
AT.end_record("Main")

print(AT)                      # 树状打印各节点 Count / Avg / Min / Max / Total
AT.save("analysis.txt")        # 保存到文件
```

**推荐用上下文管理器**（v0.0.4+）：无需手动配对 `begin`/`end`，块内抛异常也能正确结束计时——忘记 `end_record` 导致数据静默错乱的老问题从此消失：

```python
from insight_kit import AT

with AT.record("Main"):        # 进入即计时，退出即结束，异常安全
    with AT.record("Sub"):
        ...
```

输出示例：

```
Analysis Tag: AT
Main      : Count: 1, Avg: 1.2035, Min: 1.2035, Max: 1.2035, Total: 1.2035
    Sub1  : Count: 1, Avg: 0.1002, Min: 0.1002, Max: 0.1002, Total: 0.1002
    Sub2  : Count: 10, Avg: 0.0101, Min: 0.0100, Max: 0.0102, Total: 0.1010
```

> 无数据时 `print(AT)` 输出 `(empty)`，绝不出错、绝不修改内部状态。

#### 装饰器打点

```python
from insight_kit import at_record

@at_record                     # 用函数名作为标签
def preprocess(): ...

@at_record("自定义标签")        # 用自定义标签
def postprocess(): ...
```

#### 实验式打点（at_scope / experiment）

`@at_scope` 把一次调用标记为一轮独立实验：**正常或异常退出时自动打印本轮统计**，省去手写 `print(AT)` 样板。v0.0.4 起底层改用**快照-恢复**语义：实验块内的打点不会污染调用前的历史数据，实验结束后历史自动还原——**可安全多次调用、嵌套使用**。

```python
from insight_kit import AT, at_scope

@at_scope("my_exp")                      # tag 可选；省略时用函数名
def run_exp():
    AT.begin_record("Main")
    preprocess()
    AT.end_record("Main")

run_exp()                                # 退出时自动打印本轮树状统计
run_exp()                                # 每轮相互独立，结果互不污染
```

不用装饰器时，可用等价的上下文管理器只包裹一段代码：

```python
from insight_kit import AT

with AT.experiment("exp1"):              # 块内看到的是纯本轮数据
    with AT.record("Main"):
        ...
    print(AT)                            # 打印本轮（或用 save_to=）
# 退出后，全局历史数据自动恢复
```

- `print_result=False` 可关闭自动打印；`save_to="analysis.txt"` 退出时顺带保存。

#### 常用 API

| API | 说明 |
|---|---|
| `with AT.record(name):` | **推荐**：代码块计时，异常安全，无需手动配对 |
| `AT.begin_record(name)` | 开始计时，入栈 |
| `AT.end_record(name=None)` | 结束计时，出栈；name 不匹配时忽略本次调用并告警（不污染栈状态） |
| `@at_record` / `@at_record(tag)` | 装饰器：包裹函数体计时（异常安全） |
| `with AT.experiment(tag):` | 独立实验块：退出后自动恢复历史数据，可嵌套 |
| `@at_scope` / `@at_scope(tag)` | 装饰器：独立实验，退出自动打印（可 `print_result=` / `save_to=`） |
| `AT.to_dict()` / `AT.to_json()` | 结构化输出（树状），便于接入 wandb/tensorboard/自研分析 |
| `AT.reset(tag="AT")` | 清空全部记录并重置根标签与计时栈 |
| `AT.close()` | 关闭计时（后续打点全部忽略，零开销） |
| `AT.set_cuda_sync(True)` | 打点前后 `torch.cuda.synchronize()`，计时更准（需 torch + CUDA；不满足会告警提示） |
| `AT.save(path)` | 保存统计结果到文本文件 |

每个记录节点的统计包含 `Count / Avg / Min / Max / Total`；`to_dict()` 还额外提供 `p95`。

#### diffusers Pipeline 自动打点（auto_decorate）

针对推理脚本的一键插桩：自动给脚本中的 `Process`/`Porcess` 函数包上 `main/pre/pipe/post` 四层计时。

```python
from insight_kit.analysis_time.auto_decorate import auto_install
auto_install()   # 需在模块顶层显式调用；扫描当前模块全局变量，包裹 Process 函数和 diffusers Pipeline
```

> v0.0.4 起 import 本模块不再自动触发插桩（此前会在 import 时产生副作用），请显式调用 `auto_install()`。包裹动作会通过 `logging`（logger 名 `insight_kit.auto_decorate`）输出日志，便于排查"它到底包了什么"。

也可注册自定义 pipeline 类型：`register_pipeline_type(MyPipeline)`。

### 2. GPU 监控 `gpu_profiler`

#### `GPUProfiler` 类（库内调用）

```python
from insight_kit import GPUProfiler

profiler = GPUProfiler(interval=0.25, output_file="gpu_stats.csv")
profiler.start()       # 后台线程持续采样：GPU 利用率、显存带宽利用率、显存占用
# ... 跑业务代码 ...
profiler.stop()        # 停止并自动存 CSV
```

#### `monitor` 命令行工具（GPU + CPU 联合监控）

```bash
monitor --interval 0.5 --output-file system_stats.csv
```

- 每 60 秒终端打印一次分钟级平均（GPU/CPU 利用率、显存/内存占比）
- `Ctrl+C` 停止并保存 CSV

### 3. 设备信息 `device`（底层 API）

| 类 | 方法 | 返回 |
|---|---|---|
| `NvidiaInfo(gpu_id=0)` | `get_gpu_util_info()` | `(GPU利用率%, 显存带宽利用率%)` |
| | `get_gpu_memory_info()` | `(已用MiB, 总量MiB, 占比%)` |
| `CpuInfo` | `get_cpu_info()` | `(CPU利用率%, 内存占比%)` |

```python
from insight_kit.device.nvidia_info import NvidiaInfo
nvidia_info = NvidiaInfo()
gpu_util, mem_bw = nvidia_info.get_gpu_util_info()
```

### 4. 图像对比 `img_tool`

#### 命令行工具

```bash
diff_picture img1.png img2.png
```

输出两图的 MAE / MSE / PSNR / SSIM 四项指标。

#### 库内调用

```python
from insight_kit.img_tool.diff_picture import (
    calculate_mae, calculate_mse, calculate_psnr, calculate_ssim,
)
# 参数为 shape 相同的 numpy 数组 (H, W, C)
psnr = calculate_psnr(img1, img2)
```

---

## 三、已知限制

1. `auto_install()` 只对**调用方的模块级全局变量**生效；在函数内部调用（局部变量可见性）不会扫描到目标变量——此时会输出 warning 日志。
2. 纯 Python 包（`py3-none-any`），但实际运行 GPU 功能依赖 NVIDIA 驱动与 `nvidia-smi`，Linux 服务器为主要目标平台。

---

## 四、版本变更记录

### v0.0.4（当前）

- **新增** `with AT.record(name)` 上下文管理器：异常安全、无需手动配对 `begin`/`end`。
- **新增** `with AT.experiment(tag)` 与 `@at_scope` 的快照-恢复语义：实验轮次不再清空全局历史数据，可安全嵌套 / 多次调用。
- **新增** `AT.to_dict()` / `AT.to_json()` 结构化输出（含 p95），可直接接入 wandb/tensorboard。
- **改进** 输出增加 `Min / Max / Total` 统计；`print(AT)` 不再有任何副作用（此前的致命缺陷：`__str__` 出错会静默清空全部数据）。
- **修复** `end_record` tag 不匹配时状态栈被永久污染的问题（现在忽略本次调用并发出 `warnings` 告警）。
- **修复** `reset` 未清空计时栈的问题；重复 `begin` 同一记录、栈空 `end` 等误用均改为 `warnings` 告警而非静默。
- **改进** `set_cuda_sync(True)` 在缺 torch/CUDA 的环境下会告警提示已跳过同步。
- **变更** `auto_decorate` 不再在 import 时自动插桩，需显式 `auto_install()`；插桩动作有 logging 日志。

> ⚠️ 行为变更：旧版 `@at_scope` 进入时会 `reset()` 清空全局数据，新版不再清空。如果你的脚本依赖这个副作用来分轮，请改用显式 `AT.reset()`。
