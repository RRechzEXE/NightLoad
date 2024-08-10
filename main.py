import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
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
            percentage_match = re.search(r"(\d+(\.\d+)?)%", line)
            speed_match = re.search(r"(\d+(\.\d+)?)KB/s", line)
            
            if percentage_match:
                percentage = float(percentage_match.group(1))
                percent_label.config(text=f"Progress: {percentage:.2f}%")
                
            if speed_match:
                speed = float(speed_match.group(1)) / 1024  # KB/s to MB/s
                speed_label.config(text=f"Speed: {speed:.2f} MB/s")

    except queue.Empty:
        root.after(100, update_progress)

def get_internet_speed():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000  # bps to Mbps
    return download_speed

def update_speed():
    download_speed = get_internet_speed()
    speed_label.config(text=f"Speed: {download_speed:.2f} MB/s")
    root.after(5000, update_speed)

def update_status(returncode):
    progress_bar.stop()
    progress_bar['mode'] = 'determinate'
    progress_bar['value'] = 100

    if returncode == 0:
        status_message = "Download completed successfully."
    else:
        status_message = "An error occurred during download."

    status_label.config(text=status_message)
    if "error" in status_message.lower():
        messagebox.showerror("Error", status_message)
    else:
        messagebox.showinfo("Success", status_message)

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

# Üst başlık
header_frame = tk.Frame(root, bg="#4A90E2", pady=10)
header_frame.pack(fill=tk.X)

header_label = tk.Label(header_frame, text="NightLoad BETA v2.0", fg="white", bg="#4A90E2", font=("Arial", 16))
header_label.pack(side=tk.LEFT, padx=10)

# Ana içerik çerçevesi
main_frame = tk.Frame(root, padx=20, pady=20)
main_frame.pack()

url_label = tk.Label(main_frame, text="URL:")
url_label.grid(row=0, column=0, sticky=tk.W)

url_entry = tk.Entry(main_frame, width=50)
url_entry.grid(row=0, column=1, padx=10)

download_button = tk.Button(main_frame, text="Download", command=download)
download_button.grid(row=0, column=2, padx=10)

progress_label_frame = tk.Frame(main_frame)
progress_label_frame.grid(row=1, column=0, columnspan=3, pady=(20, 10))

percent_label = tk.Label(progress_label_frame, text="Progress: 0.00%")
percent_label.pack(side=tk.LEFT)

speed_label = tk.Label(progress_label_frame, text="Speed: 0.00 MB/s")
speed_label.pack(side=tk.RIGHT)

progress_bar = ttk.Progressbar(main_frame, length=400, mode='indeterminate')
progress_bar.grid(row=2, column=0, columnspan=3, pady=(10, 20))

status_label = tk.Label(root, text="")
status_label.pack(pady=10)

root.mainloop()
