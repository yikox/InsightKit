from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo, nvmlDeviceGetUtilizationRates, nvmlShutdown  # 新增 NVML 库


class NvidiaInfo:
    def __init__(self, gpu_id=0):
        """
        初始化 NVIDIA GPU 信息获取类
        :param gpu_id: GPU ID (默认监控第一个 GPU)
        """
        nvmlInit()
        self.gpu_handle = nvmlDeviceGetHandleByIndex(0)  # 默认监控第一个 GPU
    def get_gpu_util_info(self):
        """
        获取 GPU 利用率、显存带宽
        :return: GPU 利用率、显存带宽
        """
        util = nvmlDeviceGetUtilizationRates(self.gpu_handle)
        gpu_util = util.gpu
        mem_bw_util = util.memory
        return gpu_util, mem_bw_util
    def get_gpu_memory_info(self):
        """
        获取 GPU 显存使用情况
        :return: 显存使用情况
        """
        mem_info = nvmlDeviceGetMemoryInfo(self.gpu_handle)
        mem_used = mem_info.used // (1024**2)
        mem_total = mem_info.total // (1024**2)
        mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
        return mem_used, mem_total, mem_percent
    def __del__(self):
        """
        释放 NVML 资源
        """
        nvmlShutdown()

if __name__ == "__main__":
    nvidia_info = NvidiaInfo()
    gpu_util, mem_bw_util = nvidia_info.get_gpu_util_info()
    mem_used, mem_total, mem_percent = nvidia_info.get_gpu_memory_info()
    print(f"GPU Utilization: {gpu_util}%")
    print(f"Memory Bandwidth Utilization: {mem_bw_util}%")
    print(f"Memory Used: {mem_used} MiB")
    print(f"Memory Total: {mem_total} MiB")
    print(f"Memory Percent: {mem_percent:.2f}%")