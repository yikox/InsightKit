import subprocess
import time
import csv
import threading
import psutil  # 用于获取 CPU 使用率
import argparse

class SystemMonitor:
    """系统性能监控工具，支持 GPU/CPU 数据采集和分钟级平均统计"""
    def __init__(self, interval=0.25, output_file="system_stats.csv"):
        self.interval = interval
        self.output_file = output_file
        self.data = []
        self.monitoring = False
        self.thread = None
        
        # 分钟统计相关变量
        self.minute_start = None
        self.gpu_utils = [] # GPU 利用率列表
        self.cpu_utils = [] # CPU 利用率列表
        self.gpu_mem_percents = []  # GPU 显存占比
        self.cpu_mem_percents = []  # CPU 内存占比

    def _get_gpu_stats(self):
        """获取 GPU 利用率、显存使用及占比"""
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        parts = result.stdout.strip().split(", ")
        # 计算 GPU 显存使用占比（百分比）
        mem_used = float(parts[1])
        mem_total = float(parts[2])
        mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
        return parts[0], mem_used, mem_total, mem_percent  # 返回 GPU 数据及显存占比

    def _get_cpu_stats(self):
        """获取 CPU 使用率及内存占比"""
        cpu_usage = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()
        mem_percent = mem_info.percent  # 直接获取内存使用百分比
        return cpu_usage, mem_percent
    
    def _monitor_loop(self):
        """持续监控 GPU/CPU 状态"""
        start_time = time.time()
        self.minute_start = time.time()  # 初始化分钟计时
        print("🚀 系统监控开始...")
        
        while self.monitoring:
            # 获取当前时间戳和运行时间
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            elapsed = round(time.time() - start_time, 2)
            
            # 获取 GPU 数据（包含显存占比）
            gpu_util, gpu_mem_used, gpu_mem_total, gpu_mem_percent = self._get_gpu_stats()
            
            # 获取 CPU 数据（包含内存占比）
            cpu_util, cpu_mem_percent = self._get_cpu_stats()

            # 记录数据（新增显存和内存占比）
            self.data.append([
                timestamp, elapsed,
                float(gpu_util), gpu_mem_used, gpu_mem_total, gpu_mem_percent,
                cpu_util, cpu_mem_percent
            ])
            
            # 统计分钟数据
            self.gpu_utils.append(float(gpu_util))
            self.cpu_utils.append(cpu_util)
            self.gpu_mem_percents.append(gpu_mem_percent)
            self.cpu_mem_percents.append(cpu_mem_percent)

            # 每分钟输出一次平均数据
            current_time = time.time()
            if current_time - self.minute_start >= 60:
                avg_gpu = sum(self.gpu_utils) / len(self.gpu_utils)
                avg_cpu = sum(self.cpu_utils) / len(self.cpu_utils)
                avg_gpu_mem = sum(self.gpu_mem_percents) / len(self.gpu_mem_percents)
                avg_cpu_mem = sum(self.cpu_mem_percents) / len(self.cpu_mem_percents)
                print(
                    f"[{timestamp}] 过去一分钟平均利用率:\n"
                    f"  GPU利用率 = {avg_gpu:.2f}%\n"
                    f"  GPU显存占比 = {avg_gpu_mem:.2f}%\n"
                    f"  CPU利用率 = {avg_cpu:.2f}%\n"
                    f"  系统内存占比 = {avg_cpu_mem:.2f}%\n"
                    f"  (采样间隔={self.interval}s)"
                )
                
                # 重置统计
                self.minute_start = current_time
                self.gpu_utils.clear()
                self.cpu_utils.clear()
                self.gpu_mem_percents.clear()
                self.cpu_mem_percents.clear()
            
            time.sleep(self.interval)
        
        print("🛑 系统监控结束！")

    def start(self):
        """启动监控线程"""
        if not self.monitoring:
            self.monitoring = True
            self.thread = threading.Thread(target=self._monitor_loop)
            self.thread.start()

    def stop(self):
        """停止监控线程，并保存数据"""
        if self.monitoring:
            self.monitoring = False
            self.thread.join()
            self._save_to_file()

    def _save_to_file(self):
        """保存采集数据到 CSV 文件"""
        with open(self.output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Time", "Elapsed(s)", 
                "GPU_Util(%)", "Memory_Used(MiB)", "Memory_Total(MiB)",
                "CPU_Util(%)"
            ])
            writer.writerows(self.data)
        print(f"✅ 数据已保存到 {self.output_file}")


def monitor():
    parser = argparse.ArgumentParser(description='系统监控工具')
    parser.add_argument('--interval', type=float, help='输入整数', default=0.25)
    parser.add_argument('--output-file', type=str, help='输出文件名', default='system_stats.csv')
    args = parser.parse_args()
    
    """系统监控入口函数"""
    profiler = SystemMonitor(interval=args.interval)  # 采样间隔设为 0.5 秒
    profiler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        profiler.stop()

# 使用示例
if __name__ == "__main__":
    monitor()