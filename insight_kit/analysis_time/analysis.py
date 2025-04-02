
import time

CUDA_AVAILABLE = True
try:
    # 判断 torch 和 cuda 是否可用
    import torch
    assert torch.cuda.is_available()
    CUDA_AVAILABLE = True
except ImportError:
    # print("torch is not installed, cuda_sync will be ignored.")
    CUDA_AVAILABLE = False

TAG_LEN = 8
class Record:
    def __init__(self):
        self.name = None
        self.parent_tag = None
        self.recore_lst = []
        self.avg = 0
        self.count = 0

        self.begin_time = None

        self.tag_len = TAG_LEN
    def add_record(self, t):
        self.recore_lst.append(t - self.begin_time)
        self.count += 1
        

    def __str__(self):
        self.avg = sum(self.recore_lst) / self.count
        return f"{self.name[:self.tag_len].ljust(self.tag_len)}: Count: {self.count}, Avg: {self.avg:.4f}"

class Analysis:
    def __init__(self, atag="AT"):
        self.records = {} # key: tag, value: records
        self.parent_tag = atag
        self.a_tag = atag # analysis tag
        self.current_tag = [] # stack of tags
        self.close_flag = False
        self.cuda_sync = False
    
    def close(self):
        self.close_flag = True
        self.reset()

    def reset(self, atag="AT"):
        self.records = {}
        self.a_tag = atag
        self.parent_tag = self.a_tag

    def set_cuda_sync(self, cuda_sync):
        if cuda_sync == False:
            self.cuda_sync = False
            return

        self.cuda_sync = cuda_sync and CUDA_AVAILABLE
    
    def _sync(self):
        if self.cuda_sync:
            torch.cuda.synchronize()
        

    def begin_record(self, name):
        if self.close_flag:
            return
        tag= self.parent_tag + "/" + name
        self._sync()
        t = time.time()
        if tag in self.records.keys():
            record = self.records[tag]
            record.begin_time = t
        else:
            record = Record()
            record.name = name
            record.parent_tag = self.parent_tag
            record.begin_time = t
            self.records[tag] = record
        self.current_tag.append(tag)
        self.parent_tag = tag

    def end_record(self,name = None):
        if self.close_flag:
            return
        self._sync()
        t = time.time()
        if len(self.current_tag) == 0:
            print("Error: No tag to end")
            return
        top = self.current_tag.pop()
        if name is None:
            tag = top
        elif top.split('/')[-1] != name:
            print("top:", top)
            print("tag:", name)
            print("Error: Tag mismatch")
            return
        record = self.records[top]
        record.add_record(t)
        self.parent_tag = record.parent_tag

    def __str__(self):
        if self.close_flag:
            return "Analysis closed."
        try:
            name_lst = [tag.split('/')[-1] for tag in self.records.keys()]
            max_tag_len = len(max(name_lst, key=len))
            res = f"Analysis Tag: {self.a_tag}\n"
            for k, v in self.records.items():
                Indent = ""
                ptag = v.parent_tag
                while self.a_tag != ptag:
                    Indent += "    "
                    ptag = self.records[ptag].parent_tag
                v.tag_len = max_tag_len
                res += Indent + str(v) + "\n"
        except Exception as e:
            self.reset(self.a_tag) # reset the analysis
            res = f"[ATimer failed] Error: {e}"
        return res
    def save(self, path="analysis.txt"):
        if self.close_flag:
            print("Analysis closed.")
            return
        with open(path, "w") as f:
            f.write(str(self))
        print(f"Analysis result saved to {path}")
AT = Analysis("AT")

if __name__ == "__main__":
    # AT.close()
    AT.begin_record("Main")
    time.sleep(0.1)
    AT.begin_record("Sub1")
    time.sleep(0.1)
    AT.end_record("Sub1")
    for i in range(10):
        AT.begin_record(f"Sub2")
        time.sleep(0.01)
        AT.begin_record(f"Sub2-1")
        time.sleep(0.01)
        AT.end_record()
        AT.end_record(f"Sub2")
    AT.end_record("Main")
    AT.begin_record("Main1")
    time.sleep(0.1)
    AT.end_record("Main1")

    # AT.save()

    print(AT)
