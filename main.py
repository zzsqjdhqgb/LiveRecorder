import subprocess
import threading
import time
import os
import sys
import signal
import psutil

from config import VLC_PATH, OUTPUT_PATH

from task import TASKS

print_lock = threading.Lock()

def thread_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def Transform(input: str, output: str) -> None:
    # input = os.path.abspath(input)
    # output = os.path.abspath(output)
    thread_print(f"Starting transforming {input} to {output}")
    subprocess.run([
        VLC_PATH,
        "--intf", "dummy",
        os.path.abspath(input),
        "--sout", "#std{access=file,mux=mp4,dst=" +
        os.path.abspath(output) + "}",
        "--play-and-exit"
    ])
    os.remove(input)
    thread_print(f"Transforming {input} to {output} finished")


Stop_Flag = False


def Worker(url: str, name: str) -> None:
    while not Stop_Flag:
        cur_time = time.strftime('%Y-%m-%d_%H-%M-%S')
        rec_out = f"{name}/tmp_{cur_time}.mp4"
        rec_out = os.path.join(OUTPUT_PATH, rec_out)
        # rec_out = os.path.abspath(rec_out)
        thread_print(f"Recording to {rec_out}")
        subprocess.run([
            VLC_PATH,
            "--intf", "dummy",
            url,
            "--sout=#transcode{vcodec=h264,acodec=mp4a,ab=128,channels=1,samplerate=44100}:std{access=file,mux=mp4,dst=" +
            os.path.abspath(rec_out) + "}",
            "--play-and-exit"
        ])
        thread_print(f"Recording {name} stopped")
        rec_res = f"{
            name}/{cur_time} - {time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        rec_res = os.path.join(OUTPUT_PATH, rec_res)
        threading.Thread(target=Transform, args=(rec_out, rec_res)).start()
    thread_print(f"Worker {name} stopped")


def init() -> None:
    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)
    for task in TASKS:
        if not os.path.exists(os.path.join(OUTPUT_PATH, task["name"])):
            os.mkdir(os.path.join(OUTPUT_PATH, task["name"]))
        threading.Thread(target=Worker, args=(
            task["url"], task["name"])).start()


def signal_handler(sig, frame) -> None:
    global Stop_Flag
    thread_print('Received Ctrl+C. Terminating all subprocesses...')
    Stop_Flag = True
    parent = psutil.Process()
    for child in parent.children(recursive=True):
        child.terminate()
        try:
            child.wait(timeout=10)  # 等待子进程结束，超时时间为10秒
        except psutil.TimeoutExpired:
            child.kill()  # 如果子进程没有在10秒内结束，强制终止
    thread_print('All subprocesses terminated.')
    sys.exit(0)


if __name__ == "__main__":
    # 注册信号处理函数
    signal.signal(signal.SIGINT, signal_handler)
    init()
    while True:
        time.sleep(1)
