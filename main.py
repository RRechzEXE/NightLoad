import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import subprocess
import threading
import re
import queue
import speedtest

def download_with_aria2(url, options=[]):
    aria2_path = r"C:\BasicDownload\aria2-1.37.0-win-64bit-build1\aria2c.exe"
    command = [aria2_path, url]
    command.extend(options)
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def monitor_download(process, output_queue):
    for line in iter(process.stdout.readline, ''):
        output_queue.put(line)
    
    process.stdout.close()
    process.wait()
    output_queue.put("done")

def update_progress():
    try:
        while True:
            line = output_queue.get_nowait()
            if line == "done":
                update_status(0)
                return
            # İndirme yüzdesini ve hızını güncelle
            percentage_match = re.search(r"(\d+(\.\d+)?)%", line)
            speed_match = re.search(r"(\d+(\.\d+)?)KB/s", line)
            
            if percentage_match:
                percentage = float(percentage_match.group(1))
                percent_label.config(text=f"İlerleme: {percentage:.2f}%")
                
            if speed_match:
                speed = float(speed_match.group(1)) / 1024  # KB/s to MB/s
                speed_label.config(text=f"Hız: {speed:.2f} MB/s")

    except queue.Empty:
        root.after(100, update_progress)  # 100 ms sonra tekrar dene

def get_internet_speed():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000  # bps to Mbps
    upload_speed = st.upload() / 1_000_000    # bps to Mbps
    return download_speed, upload_speed

def update_speed():
    download_speed, _ = get_internet_speed()
    speed_label.config(text=f"Hız: {download_speed:.2f} MB/s")
    root.after(5000, update_speed)  # Her 5 saniyede bir hız güncelle

def update_status(returncode):
    # İlerleme çubuğunu durdur ve doldur
    progress_bar.stop()
    progress_bar['mode'] = 'determinate'
    progress_bar['value'] = 100

    if returncode == 0:
        status_message = "İndirme başarıyla tamamlandı."
    else:
        status_message = f"İndirme sırasında hata oluştu."

    status_label.config(text=status_message)
    if "Hata" in status_message or "hata" in status_message:
        messagebox.showerror("Hata", status_message)
    else:
        messagebox.showinfo("Başarılı", status_message)

def download():
    url = url_entry.get()
    options = []
    
    progress_bar['mode'] = 'indeterminate'
    progress_bar.start()

    process = download_with_aria2(url, options)
    
    global output_queue
    output_queue = queue.Queue()
    
    thread = threading.Thread(target=monitor_download, args=(process, output_queue))
    thread.start()

    update_speed()
    update_progress()

# Ana pencere oluşturma
root = tk.Tk()
root.title("NightLoad with Aria2")

frame = tk.Frame(root)
frame.pack(pady=10)

percent_label = tk.Label(frame, text="İlerleme: 0.00%")
percent_label.pack(side=tk.LEFT)

url_entry = tk.Entry(frame, width=50)
url_entry.pack(side=tk.LEFT)

speed_label = tk.Label(frame, text="Hız: 0.00 MB/s")
speed_label.pack(side=tk.RIGHT)

progress_bar = ttk.Progressbar(root, length=400, mode='indeterminate')
progress_bar.pack(pady=10)

download_button = tk.Button(root, text="İndir", command=download)
download_button.pack()

status_label = tk.Label(root, text="")
status_label.pack(pady=10)

root.mainloop()
