import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
import threading
import queue
import re
import psutil
import time

log_file_path = "download_logs.txt"  # Log dosyasının kaydedileceği yer

def write_to_log(message):
    with open(log_file_path, "a") as log_file:
        log_file.write(message + "\n")

def download_with_aria2(url, options=[]):
    aria2_path = r"C:\BasicDownload\aria2-1.37.0-win-64bit-build1\aria2c.exe"
    command = [aria2_path] + options + [url]  # Kullanıcıdan alınan iş parçacığı sayısını komuta ekle
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start download: {str(e)}")
        write_to_log(f"Failed to start download: {str(e)}")
        return None

def monitor_download(process, output_queue):
    try:
        for line in iter(process.stdout.readline, ''):
            output_queue.put(line)
            write_to_log(f"stdout: {line.strip()}")

        process.stdout.close()
        process.wait()
        output_queue.put("done")
    except Exception as e:
        output_queue.put(f"error: {str(e)}")
        write_to_log(f"Error: {str(e)}")

    # Check for errors in stderr
    for err_line in iter(process.stderr.readline, ''):
        output_queue.put(f"error: {err_line.strip()}")
        write_to_log(f"stderr: {err_line.strip()}")

    process.stderr.close()

def update_progress(process):
    try:
        if process.poll() is not None:
            update_status(process.returncode)
            return

        while not output_queue.empty():
            line = output_queue.get_nowait()

            if line.startswith("error"):
                status_label.config(text="An error occurred.", fg="red")
                messagebox.showerror("Error", line)
                write_to_log(line)
                return

            if line == "done":
                update_status(0)
                return
            
            percentage_match = re.search(r"(\d+(\.\d+)?)%", line)

            if percentage_match:
                percentage = float(percentage_match.group(1))
                percent_label.config(text=f"Progress: {int(percentage)}%")  # Tek haneli olarak göster

    except queue.Empty:
        pass
    
    root.after(10000, update_progress, process)  # 10 saniyede bir güncelle

def update_speed():
    try:
        net_io = psutil.net_io_counters()
        download_speed = (net_io.bytes_recv / 1024 / 1024) / 8  # Bytes to MB, converted to MB/s
        speed_label.config(text=f"Speed: {download_speed:.2f} MB/s")
    except Exception as e:
        messagebox.showerror("Error", f"Could not update speed: {str(e)}")
        write_to_log(f"Could not update speed: {str(e)}")
    
    root.after(8000, update_speed)  # 8 saniyede bir güncelle

def update_status(returncode):
    progress_bar.stop()
    progress_bar['mode'] = 'determinate'
    progress_bar['value'] = 100

    if returncode == 0:
        status_message = "Download completed successfully."
        status_label.config(fg="green")
    else:
        status_message = "An error occurred during download."
        status_label.config(fg="red")

    status_label.config(text=status_message)
    write_to_log(status_message)
    messagebox.showinfo("Status", status_message)

def download():
    url = url_entry.get()
    if not url:
        messagebox.showerror("Error", "Please enter a URL to download.")
        return

    # Kullanıcıdan iş parçacığı sayısını al
    thread_count = thread_entry.get()
    if not thread_count.isdigit() or int(thread_count) < 1:
        messagebox.showerror("Error", "Please enter a valid number for threads.")
        return

    options = ["-s", thread_count, "-x", thread_count]  # Dinamik olarak iş parçacığı sayısını ayarlıyoruz

    # "Threads" bilgisini arayüzde göster
    threads_label.config(text=f"Downloading with {thread_count} threads")

    progress_bar['mode'] = 'indeterminate'
    progress_bar.start()

    process = download_with_aria2(url, options)
    if not process:
        return  # Eğer indirme başlatılamazsa, fonksiyondan çık
    
    global output_queue
    output_queue = queue.Queue()
    
    thread = threading.Thread(target=monitor_download, args=(process, output_queue))
    thread.daemon = True  # Threadi arka planda çalıştır
    thread.start()

    update_speed()
    update_progress(process)

# Ana pencere oluşturma
root = tk.Tk()
root.title("NightLoad with Aria2")

# Üst başlık
header_frame = tk.Frame(root, bg="#2C3E50", pady=10)
header_frame.pack(fill=tk.X)

header_label = tk.Label(header_frame, text="NightLoad BETA v3.2.0", fg="white", bg="#2C3E50", font=("Helvetica", 18, "bold"))
header_label.pack(side=tk.LEFT, padx=10)

# Ana içerik çerçevesi
main_frame = tk.Frame(root, padx=20, pady=20)
main_frame.pack()

url_label = tk.Label(main_frame, text="URL:", font=("Arial", 12))
url_label.grid(row=0, column=0, sticky=tk.W)

url_entry = tk.Entry(main_frame, width=50, font=("Arial", 12))
url_entry.grid(row=0, column=1, padx=10)

download_button = tk.Button(main_frame, text="Download", command=download, bg="#3498DB", fg="white", font=("Arial", 12, "bold"), relief=tk.RAISED)
download_button.grid(row=0, column=2, padx=10)

# İş parçacığı sayısı giriş alanı
thread_label = tk.Label(main_frame, text="Threads:", font=("Arial", 12))
thread_label.grid(row=1, column=0, sticky=tk.W)

thread_entry = tk.Entry(main_frame, width=10, font=("Arial", 12))
thread_entry.grid(row=1, column=1, padx=10)
thread_entry.insert(0, "4")  # Varsayılan olarak 4 iş parçacığı

progress_label_frame = tk.Frame(main_frame)
progress_label_frame.grid(row=2, column=0, columnspan=3, pady=(20, 10))

percent_label = tk.Label(progress_label_frame, text="Progress: 0%", font=("Arial", 12))
percent_label.pack(side=tk.LEFT)

speed_label = tk.Label(progress_label_frame, text="Speed: N/A", font=("Arial", 12))
speed_label.pack(side=tk.RIGHT)

# İş parçacığı sayısını gösteren label
threads_label = tk.Label(main_frame, text="", font=("Arial", 12))
threads_label.grid(row=3, column=0, columnspan=3, pady=(10, 20))

progress_bar = ttk.Progressbar(main_frame, length=400, mode='indeterminate', style='TProgressbar')
progress_bar.grid(row=4, column=0, columnspan=3, pady=(10, 20))

# Stil oluşturma
style = ttk.Style()
style.configure('TProgressbar', thickness=20, troughcolor='#BDC3C7', background='#3498DB')

status_label = tk.Label(root, text="", font=("Arial", 12))
status_label.pack(pady=10)

root.mainloop()
