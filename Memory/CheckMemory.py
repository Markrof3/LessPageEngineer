import time
import tracemalloc
import os
from datetime import datetime
from threading import Thread
class CheckMemory:

    def __init__(self, ):
        self.folder_name = 'memory_file'
        tracemalloc.start()
    def main(self):
        current_path = os.getcwd()
        folder_path = os.path.join(current_path, self.folder_name)
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            # 文件夹不存在，则创建文件夹
            os.makedirs(folder_path)
            print(f"文件夹'{self.folder_name}'已创建在路径'{current_path}'下。")
        else:
            print(f"文件夹'{self.folder_name}'已存在于路径'{current_path}'下。")
        while True:
            sp = tracemalloc.take_snapshot()
            sp.dump(f"./memory_file/{datetime.now().strftime('%Y-%m-%dTG%H-%M-%S')}")
            time.sleep(300)

    def run(self):
        t1 = Thread(target=self.main)
        t1.setDaemon(True)
        t1.start()

    def load_snapshot(self):
        current_path = os.getcwd()
        folder_path = os.path.join(current_path, self.folder_name)
        sp_list = []
        for dirpath, dirnames, filenames in os.walk(folder_path):
            # 打印当前目录路径
            print(f"正在遍历目录: {dirpath}")
            # 遍历目录中的文件
            for filename in filenames:
                # 打印文件名
                print(f"文件名: {filename}")
                # 构建完整的文件路径
                file_path = os.path.join(dirpath, filename)
                sp = tracemalloc.Snapshot.load(file_path)
                sp_list.append(sp)
            top_stats = sp_list[-2].compare_to(sp_list[1], 'lineno')
            for stat in top_stats[:10]:
                print(stat)

if __name__ == '__main__':
    c = CheckMemory()
    c.load_snapshot()