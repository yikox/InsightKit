import subprocess
import time
import csv
import threading

class GPUProfiler:
    """封装 GPU 监控工具，支持开始、结束、保存数据"""
    def __init__(self, interval=0.25, output_file="gpu_stats.csv"):
        self.interval = interval
        self.output_file = output_file
        self.data = []
        self.monitoring = False
        self.thread = None

    def _get_gpu_stats(self):
        """获取 GPU 利用率和显存数据"""
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def _monitor_loop(self):
        """持续监控 GPU 状态，直到手动停止"""
        start_time = time.time()
        print("🚀 GPU 监控开始...")
        
        while self.monitoring:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            gpu_data = self._get_gpu_stats()
            elapsed = round(time.time() - start_time, 2)
            self.data.append([timestamp, elapsed] + gpu_data.split(", "))
            print(f"{timestamp}, {elapsed}s, {gpu_data}")
            time.sleep(self.interval)
        
        print("🛑 GPU 监控结束！")

    def start(self):
        """启动 GPU 监控线程"""
        if not self.monitoring:
            self.monitoring = True
            self.thread = threading.Thread(target=self._monitor_loop)
            self.thread.start()

    def stop(self):
        """停止 GPU 监控线程，并保存数据"""
        if self.monitoring:
            self.monitoring = False
            self.thread.join()
            self._save_to_file()

    def _save_to_file(self):
        """保存采集数据到 CSV 文件"""
        with open(self.output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "Elapsed(s)", "GPU_Util(%)", "Memory_Used(MiB)", "Memory_Total(MiB)"])
            writer.writerows(self.data)
        print(f"✅ 数据已保存到 {self.output_file}")