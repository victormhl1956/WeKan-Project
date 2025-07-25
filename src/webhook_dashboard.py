#!/usr/bin/env python3
"""
Webhook Receiver Dashboard - GUI Monitoring Interface
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading
from datetime import datetime

class WebhookDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("WeKan-GitHub Webhook Monitor")
        self.root.geometry("800x600")
        
        # Status Frame
        self.status_frame = ttk.LabelFrame(root, text="System Status", padding=10)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_labels = {
            'server': ttk.Label(self.status_frame, text="Server: Stopped"),
            'requests': ttk.Label(self.status_frame, text="Requests: 0"),
            'last_event': ttk.Label(self.status_frame, text="Last Event: None")
        }
        
        for i, (_, label) in enumerate(self.status_labels.items()):
            label.grid(row=0, column=i, padx=10, pady=5, sticky=tk.W)
        
        # Event Log
        self.log_frame = ttk.LabelFrame(root, text="Event Log", padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            width=80,
            height=20
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Control Buttons
        self.control_frame = ttk.Frame(root)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = ttk.Button(
            self.control_frame,
            text="Start Server",
            command=self.start_server
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            self.control_frame,
            text="Stop Server",
            command=self.stop_server,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(
            self.control_frame,
            text="Refresh Status",
            command=self.refresh_status
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Initialize
        self.server_url = "http://localhost:5000"
        self.running = False
        self.request_count = 0
        self.refresh_status()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.update()

    def refresh_status(self):
        try:
            response = requests.get(f"{self.server_url}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.status_labels['server'].config(
                    text=f"Server: Running ({data['mode']} mode)"
                )
                self.running = True
                self.start_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
            else:
                self.set_server_stopped()
        except requests.exceptions.RequestException:
            self.set_server_stopped()

    def set_server_stopped(self):
        self.status_labels['server'].config(text="Server: Stopped")
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def start_server(self):
        def run_server():
            self.log_message("Starting webhook receiver server...")
            # In a real implementation, this would start the server process
            self.refresh_status()
        
        threading.Thread(target=run_server, daemon=True).start()

    def stop_server(self):
        def stop():
            self.log_message("Stopping webhook receiver server...")
            # In a real implementation, this would stop the server process
            self.set_server_stopped()
        
        threading.Thread(target=stop, daemon=True).start()

    def update_request_count(self):
        self.request_count += 1
        self.status_labels['requests'].config(text=f"Requests: {self.request_count}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WebhookDashboard(root)
    root.mainloop()
