import psutil  # 用于获取 CPU 使用率

class CpuInfo:
    def __init__(self):
        pass

    def get_cpu_info(self):
        """获取 CPU 信息"""
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_memory = psutil.virtual_memory()
        mem_percent = cpu_memory.percent  # 直接获取内存使用百分比
        return cpu_percent, mem_percent