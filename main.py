#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import sys
import platform
import threading
import queue
import re
from groq import Groq

IS_WINDOWS = platform.system() == 'Windows'

if IS_WINDOWS:
    try:
        from winpty import PtyProcess
        HAS_PTY = True
    except ImportError:
        HAS_PTY = False
        print("Warning: pywinpty not installed. Install with: pip install pywinpty")
else:
    try:
        from ptyprocess import PtyProcessUnicode as PtyProcess
        HAS_PTY = True
    except ImportError:
        HAS_PTY = False
        print("Warning: ptyprocess not installed. Install with: pip install ptyprocess")

class AITerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Terminal Assistant")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1e1e1e')
        
        self.groq_api_key = os.environ.get('GROQ_API_KEY', '')
        if not self.groq_api_key:
            messagebox.showwarning(
                "API Key Missing", 
                "GROQ_API_KEY not found in environment variables.\n"
                "AI features will be disabled.\n\n"
                "Get a free API key at: https://console.groq.com/keys"
            )
            self.groq_client = None
        else:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                messagebox.showerror("Groq Error", f"Failed to initialize Groq client: {e}")
                self.groq_client = None
        
        self.is_windows = platform.system() == 'Windows'
        self.shell = 'powershell.exe' if self.is_windows else 'bash'
        
        self.pending_command = None
        self.last_command = ""
        self.output_buffer = []
        self.process = None
        
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        if not HAS_PTY:
            messagebox.showerror(
                "Missing Dependency",
                f"PTY library not found.\n"
                f"Install {'pywinpty' if self.is_windows else 'ptyprocess'} to use terminal features.\n\n"
                f"Command: pip install {'pywinpty' if self.is_windows else 'ptyprocess'}"
            )
        
        self.setup_ui()
        self.start_terminal()
        
    def setup_ui(self):
        main_container = tk.PanedWindow(
            self.root, 
            orient=tk.HORIZONTAL, 
            bg='#1e1e1e',
            sashwidth=5,
            sashrelief=tk.RAISED
        )
        main_container.pack(fill=tk.BOTH, expand=True)
        
        terminal_frame = tk.Frame(main_container, bg='#1e1e1e')
        terminal_label = tk.Label(
            terminal_frame, 
            text="🖥️ Terminal", 
            bg='#2d2d30', 
            fg='white',
            font=('Arial', 11, 'bold'),
            pady=8
        )
        terminal_label.pack(fill=tk.X)
        
        self.terminal_display = scrolledtext.ScrolledText(
            terminal_frame,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Courier New', 10),
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.NORMAL
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.terminal_display.bind('<Return>', self.handle_terminal_input)
        self.terminal_display.bind('<Key>', self.handle_key_press)
        
        ai_frame = tk.Frame(main_container, bg='#252526', width=400)
        
        ai_header = tk.Frame(ai_frame, bg='#2d2d30')
        ai_header.pack(fill=tk.X)
        
        ai_label = tk.Label(
            ai_header, 
            text="🤖 AI Assistant", 
            bg='#2d2d30', 
            fg='white',
            font=('Arial', 11, 'bold'),
            pady=8
        )
        ai_label.pack(side=tk.LEFT, padx=10)
        
        settings_button = tk.Button(
            ai_header,
            text="⚙️",
            bg='#2d2d30',
            fg='white',
            font=('Arial', 14),
            command=self.open_settings,
            cursor='hand2',
            relief=tk.FLAT,
            borderwidth=0,
            padx=10
        )
        settings_button.pack(side=tk.RIGHT, padx=10)
        
        self.ai_chat = scrolledtext.ScrolledText(
            ai_frame,
            bg='#252526',
            fg='white',
            font=('Arial', 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.ai_chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.ai_chat.tag_config('user', foreground='#61afef', font=('Arial', 10, 'bold'))
        self.ai_chat.tag_config('ai', foreground='#98c379')
        self.ai_chat.tag_config('system', foreground='#e5c07b')
        self.ai_chat.tag_config('command', background='#2c313c', foreground='#abb2bf', font=('Courier New', 10))
        self.ai_chat.tag_config('error', foreground='#e06c75')
        
        input_frame = tk.Frame(ai_frame, bg='#2d2d30')
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.ai_input = tk.Entry(
            input_frame,
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 10),
            insertbackground='white'
        )
        self.ai_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.ai_input.bind('<Return>', lambda e: self.ask_ai())
        
        self.ask_button = tk.Button(
            input_frame,
            text="Ask AI",
            bg='#0e639c',
            fg='white',
            font=('Arial', 9, 'bold'),
            command=self.ask_ai,
            cursor='hand2',
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        self.ask_button.pack(side=tk.RIGHT)
        
        main_container.add(terminal_frame, width=800)
        main_container.add(ai_frame, width=400)
        
        self.add_ai_message("👋 Ask me for any command and I'll help!", 'system')
        
    def start_terminal(self):
        if not HAS_PTY:
            return
            
        try:
            self.output_queue = queue.Queue()
            
            if self.is_windows:
                self.process = PtyProcess.spawn([self.shell, '-NoLogo'], dimensions=(30, 100))
            else:
                self.process = PtyProcess.spawn([self.shell, '-i'], dimensions=(30, 100))
            
            self.read_thread = threading.Thread(target=self.read_terminal_output, daemon=True)
            self.read_thread.start()
            
            self.root.after(100, self.update_terminal_display)
        except Exception as e:
            messagebox.showerror("Terminal Error", f"Failed to start terminal: {e}")
            
    def read_terminal_output(self):
        while True:
            try:
                output = self.process.read()
                self.output_queue.put(output)
                self.output_buffer.append(output)
                
                if len(self.output_buffer) > 100:
                    self.output_buffer = self.output_buffer[-50:]
                    
                if self.last_command and any(error in output.lower() for error in 
                    ['command not found', 'no such file', 'permission denied', 'error', 'cannot']):
                    self.detect_error()
            except EOFError:
                break
            except Exception:
                break
                
    def strip_ansi_codes(self, text):
        return self.ansi_escape.sub('', text)
    
    def update_terminal_display(self):
        try:
            while True:
                output = self.output_queue.get_nowait()
                clean_output = self.strip_ansi_codes(output)
                self.terminal_display.insert(tk.END, clean_output)
                self.terminal_display.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.update_terminal_display)
            
    def handle_key_press(self, event):
        if event.char and event.keysym not in ['Return', 'BackSpace', 'Delete']:
            try:
                self.write_to_terminal(event.char)
                return 'break'
            except:
                pass
        elif event.keysym == 'BackSpace':
            try:
                self.write_to_terminal('\b')
                return 'break'
            except:
                pass
                
    def write_to_terminal(self, data):
        if self.process:
            if self.is_windows:
                data = data.replace('\n', '\r\n')
            self.process.write(data)
            
    def handle_terminal_input(self, event):
        try:
            index = self.terminal_display.index(tk.INSERT)
            line = self.terminal_display.get(f"{index} linestart", f"{index} lineend")
            
            self.last_command = line.strip()
            self.output_buffer = []
            
            self.write_to_terminal('\n')
            return 'break'
        except:
            pass
            
    def add_ai_message(self, message, tag='ai'):
        self.ai_chat.config(state=tk.NORMAL)
        self.ai_chat.insert(tk.END, f"\n{message}\n", tag)
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state=tk.DISABLED)
        
    def ask_ai(self):
        query = self.ai_input.get().strip()
        if not query:
            return
            
        if not self.groq_client:
            messagebox.showerror("Error", "Groq API client not initialized. Please set GROQ_API_KEY.")
            return
            
        self.ai_input.delete(0, tk.END)
        self.add_ai_message(f"You: {query}", 'user')
        self.add_ai_message("⏳ Thinking...", 'system')
        
        threading.Thread(target=self.get_command_suggestion, args=(query,), daemon=True).start()
        
    def get_command_suggestion(self, query):
        try:
            os_name = 'Windows' if self.is_windows else 'Linux'
            system_prompt = f"""You are a helpful terminal assistant. The user is on {os_name}.
When asked for a command, provide ONLY the command itself, nothing else. No explanations, no markdown, just the raw command.
If the user's request is unclear, provide the most likely command they need.

Examples:
User: "list files"
Assistant: ls -la

User: "find large files"
Assistant: find . -type f -size +100M

User: "check disk space"
Assistant: df -h"""

            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User request: {query}"}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            command = completion.choices[0].message.content.strip()
            
            self.root.after(0, lambda: self.show_command_suggestion(command))
            
        except Exception as e:
            self.root.after(0, lambda: self.add_ai_message(f"❌ Error: {str(e)}", 'error'))
            
    def show_command_suggestion(self, command):
        self.ai_chat.config(state=tk.NORMAL)
        last_line = self.ai_chat.get("end-2l", "end-1l")
        if "⏳ Thinking..." in last_line:
            self.ai_chat.delete("end-2l", "end-1l")
        self.ai_chat.config(state=tk.DISABLED)
        
        self.add_ai_message("AI: Here's the command:", 'ai')
        self.add_ai_message(f"  {command}", 'command')
        
        self.pending_command = command
        
        confirm_frame = tk.Frame(self.ai_chat, bg='#252526')
        self.ai_chat.window_create(tk.END, window=confirm_frame)
        
        tk.Button(
            confirm_frame,
            text="✓ Execute",
            bg='#0e639c',
            fg='white',
            command=lambda: self.execute_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            padx=10,
            pady=3
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(
            confirm_frame,
            text="✗ Cancel",
            bg='#3c3c3c',
            fg='white',
            command=lambda: self.cancel_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            padx=10,
            pady=3
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.ai_chat.config(state=tk.NORMAL)
        self.ai_chat.insert(tk.END, "\n")
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state=tk.DISABLED)
        
    def execute_pending_command(self, frame):
        if self.pending_command:
            frame.destroy()
            self.add_ai_message(f"✅ Executed: {self.pending_command}", 'system')
            
            self.last_command = self.pending_command
            self.output_buffer = []
            
            try:
                self.write_to_terminal(self.pending_command + '\n')
                self.terminal_display.focus_set()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to execute command: {e}")
                
            self.pending_command = None
            
    def cancel_pending_command(self, frame):
        frame.destroy()
        self.add_ai_message("Command rejected", 'system')
        self.pending_command = None
        
    def detect_error(self):
        if not self.last_command or not self.groq_client:
            return
            
        error_output = ''.join(self.output_buffer[-20:])
        
        self.root.after(0, lambda: self.add_ai_message(f"❌ Error detected in: {self.last_command}", 'error'))
        self.root.after(0, lambda: self.add_ai_message("⏳ Analyzing error...", 'system'))
        
        threading.Thread(
            target=self.troubleshoot_error,
            args=(self.last_command, error_output),
            daemon=True
        ).start()
        
        self.last_command = ""
        
    def troubleshoot_error(self, command, error_output):
        try:
            os_name = 'Windows' if self.is_windows else 'Linux'
            system_prompt = f"""You are a helpful terminal assistant debugging errors. The user is on {os_name}.
Analyze the error and provide:
1. A brief explanation of what went wrong
2. A suggested fix or corrected command
3. Keep your response concise and actionable

Format your response as:
Problem: [brief explanation]
Solution: [suggested fix or command]"""

            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Command executed: {command}\n\nError output:\n{error_output}"}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            solution = completion.choices[0].message.content
            
            self.root.after(0, lambda: self.show_troubleshooting_result(solution))
            
        except Exception as e:
            self.root.after(0, lambda: self.add_ai_message(f"❌ Failed to analyze: {str(e)}", 'error'))
            
    def show_troubleshooting_result(self, solution):
        self.ai_chat.config(state=tk.NORMAL)
        last_line = self.ai_chat.get("end-2l", "end-1l")
        if "⏳ Analyzing error..." in last_line:
            self.ai_chat.delete("end-2l", "end-1l")
        self.ai_chat.config(state=tk.DISABLED)
        
        self.add_ai_message(f"AI Analysis:\n{solution}", 'ai')
    
    def open_settings(self):
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Settings")
        settings_dialog.geometry("500x250")
        settings_dialog.configure(bg='#1e1e1e')
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        
        center_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        center_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 125
        settings_dialog.geometry(f"+{center_x}+{center_y}")
        
        title_label = tk.Label(
            settings_dialog,
            text="⚙️ Settings",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 14, 'bold'),
            pady=15
        )
        title_label.pack()
        
        info_frame = tk.Frame(settings_dialog, bg='#1e1e1e')
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_label = tk.Label(
            info_frame,
            text="Enter your Groq API Key\nGet a free key at: https://console.groq.com/keys",
            bg='#1e1e1e',
            fg='#98c379',
            font=('Arial', 9),
            justify=tk.LEFT
        )
        info_label.pack(anchor=tk.W)
        
        key_frame = tk.Frame(settings_dialog, bg='#1e1e1e')
        key_frame.pack(fill=tk.X, padx=20, pady=10)
        
        key_label = tk.Label(
            key_frame,
            text="API Key:",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        key_label.pack(anchor=tk.W, pady=(0, 5))
        
        key_entry = tk.Entry(
            key_frame,
            bg='#2d2d30',
            fg='white',
            font=('Courier New', 10),
            insertbackground='white',
            show='•'
        )
        key_entry.pack(fill=tk.X, ipady=5)
        key_entry.insert(0, self.groq_api_key if self.groq_api_key else '')
        key_entry.focus_set()
        
        show_var = tk.BooleanVar(value=False)
        
        def toggle_show():
            key_entry.config(show='' if show_var.get() else '•')
        
        show_check = tk.Checkbutton(
            key_frame,
            text="Show API Key",
            variable=show_var,
            command=toggle_show,
            bg='#1e1e1e',
            fg='#abb2bf',
            selectcolor='#2d2d30',
            activebackground='#1e1e1e',
            activeforeground='white',
            font=('Arial', 9)
        )
        show_check.pack(anchor=tk.W, pady=(5, 0))
        
        button_frame = tk.Frame(settings_dialog, bg='#1e1e1e')
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        def save_settings():
            new_key = key_entry.get().strip()
            if new_key:
                success = self.update_api_key(new_key)
                if success:
                    settings_dialog.destroy()
                    messagebox.showinfo("Settings Saved", "API key has been updated successfully!")
                else:
                    messagebox.showerror("Invalid API Key", "Failed to initialize Groq client. Please check your API key and try again.")
            else:
                messagebox.showwarning("Invalid Input", "Please enter a valid API key")
        
        def cancel_settings():
            settings_dialog.destroy()
        
        save_button = tk.Button(
            button_frame,
            text="💾 Save",
            bg='#0e639c',
            fg='white',
            font=('Arial', 10, 'bold'),
            command=save_settings,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_button = tk.Button(
            button_frame,
            text="✗ Cancel",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 10, 'bold'),
            command=cancel_settings,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        cancel_button.pack(side=tk.LEFT)
        
        key_entry.bind('<Return>', lambda e: save_settings())
        key_entry.bind('<Escape>', lambda e: cancel_settings())
    
    def update_api_key(self, new_key):
        self.groq_api_key = new_key
        try:
            self.groq_client = Groq(api_key=new_key)
            self.add_ai_message("✅ API key updated successfully!", 'system')
            return True
        except Exception as e:
            self.groq_client = None
            self.add_ai_message(f"❌ Failed to initialize Groq client: {str(e)}", 'error')
            return False

def main():
    root = tk.Tk()
    app = AITerminal(root)
    root.mainloop()

if __name__ == '__main__':
    main()
