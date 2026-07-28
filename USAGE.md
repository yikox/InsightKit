# InsightKit 使用说明

InsightKit 是一个面向算法性能分析与调优的 Python 工具包，提供**函数级耗时分析**、**GPU/CPU 资源监控**、**图像差异对比**三类能力。

## 一、安装

### 方式 1：安装编译好的 whl（推荐）

```bash
pip install dist/insight_kit-0.0.2-py3-none-any.whl
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

print(AT)                      # 树状打印各节点 Count / Avg
AT.save("analysis.txt")        # 保存到文件
```

输出示例：

```
Analysis Tag: AT
Main      : Count: 1, Avg: 1.2035
    Sub1  : Count: 1, Avg: 0.1002
    Sub2  : Count: 10, Avg: 0.0101
```

#### 装饰器打点

```python
from insight_kit import at_record

@at_record                     # 用函数名作为标签
def preprocess(): ...

@at_record("自定义标签")        # 用自定义标签
def postprocess(): ...
```

#### 常用 API

| API | 说明 |
|---|---|
| `AT.begin_record(name)` | 开始计时，入栈 |
| `AT.end_record(name=None)` | 结束计时，出栈；name 可选用于校验匹配 |
| `AT.reset(tag="AT")` | 清空全部记录并重置根标签 |
| `AT.close()` | 关闭计时（后续打点全部忽略，零开销） |
| `AT.set_cuda_sync(True)` | 打点前后 `torch.cuda.synchronize()`，计时更准（需 torch + CUDA） |
| `AT.save(path)` | 保存统计结果到文本文件 |

#### diffusers Pipeline 自动打点（auto_decorate）

针对推理脚本的一键插桩：自动给脚本中的 `Process`/`Porcess` 函数包上 `main/pre/pipe/post` 四层计时。

```python
from insight_kit.analysis_time.auto_decorate import auto_install
auto_install()   # 扫描当前模块全局变量，包裹 Process 函数和 diffusers Pipeline
```

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

1. `auto_decorate` 的自动插桩发生在 `import insight_kit.analysis_time.auto_decorate` 时，且只对**调用方的全局变量**生效；在函数内部 import 不会扫描到目标变量。
2. 纯 Python 包（`py3-none-any`），但实际运行 GPU 功能依赖 NVIDIA 驱动与 `nvidia-smi`，Linux 服务器为主要目标平台。
