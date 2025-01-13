import subprocess
import threading
import cv2
import time
import os

from config import VLC_PATH, OUTPUT_PATH, DUMP_PATH
from task import TASKS

# 日志功能
print_lock = threading.Lock()


def PrintLog(*args, **kwargs) -> None:
    with print_lock:
        print(*args, **kwargs)


Stop_Flag = False
flv_proc = []
worker_threads = []

def CheckVideo(file:str)->bool:
    '''
    Check if the file is a valid mp4 file
    '''
    cap = cv2.VideoCapture(file)
    if not cap.isOpened():
        return False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

    cap.release()
    return True

def Transform(input: str, output: str) -> None:
    '''
    由于 vlc 从直播中途开始录制，会导致时间戳错误
    所以再次使用 vlc 转流
    '''
    PrintLog(f"Checking {input}")
    if not CheckVideo(input):
        PrintLog(f"{input} is not a valid video")
        if os.path.getsize(input) <= 500:
            PrintLog(f"Removing {input}, since it's less than 500 bytes")
            os.remove(input)
        else:
            PrintLog(f"Moving {input} to dumps")
            os.rename(os.path.abspath(input), os.path.abspath(os.path.join(DUMP_PATH, os.path.basename(input))))
        return
    PrintLog(f"Starting transforming {input} to {output}")
    subprocess.run([
        VLC_PATH,
        "--intf", "dummy",
        os.path.abspath(input),
        "--sout", "#std{access=file,mux=mp4,dst=" +
        os.path.abspath(output) + "}",
        "--play-and-exit"
    ])
    os.remove(input)
    PrintLog(f"Transforming {input} to {output} finished")


def Worker(url: str, name: str) -> None:
    while not Stop_Flag:
        # 生成录制文件名
        cur_time = time.strftime('%Y-%m-%d_%H-%M-%S')
        rec_out = os.path.join(OUTPUT_PATH, os.path.join(
            name, f"{name}_tmp_{cur_time}.mp4"))

        # 开始录制
        PrintLog(f"Recording to {rec_out}")
        thr = subprocess.Popen([
            VLC_PATH,
            "--intf", "dummy",
            url,
            "--sout=#transcode{vcodec=h264,acodec=mp4a,ab=128,channels=1,samplerate=44100}:std{access=file,mux=mp4,dst=" +
            os.path.abspath(rec_out) + "}",
            "--play-and-exit"
        ])
        flv_proc.append(thr)

        # 录制结束
        thr.wait()
        flv_proc.remove(thr)
        PrintLog(f"Recording {name} stopped")
        # 生成输出文件名
        rec_res = os.path.join(
            OUTPUT_PATH, os.path.join(
                name, f"{name}_{cur_time} - {time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"))
        # 重新编码文件
        threading.Thread(target=Transform, args=(rec_out, rec_res)).start()
    PrintLog(f"Worker {name} stopped")


def Start() -> None:
    # 创建输出目录
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
    if not os.path.exists(DUMP_PATH):
        os.makedirs(DUMP_PATH)
    for task in TASKS:
        # 创建任务目录
        if not os.path.exists(os.path.join(OUTPUT_PATH, task["name"])):
            os.makedirs(os.path.join(OUTPUT_PATH, task["name"]))
        thr = threading.Thread(target=Worker, args=(
            task["url"], task["name"]))
        thr.start()
        worker_threads.append(thr)


def Stop() -> None:
    global Stop_Flag
    PrintLog('Stopping flvs...')
    Stop_Flag = True
    kill_lst = flv_proc[:]
    for thr in kill_lst:
        thr.kill()
    for thr in kill_lst:
        thr.wait()
    PrintLog('All flv processes Stopped.')
    for thr in worker_threads:
        thr.join()
    PrintLog('All worker threads Stopped.')
    PrintLog('exiting...')


if __name__ == "__main__":
    Start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        Stop()
