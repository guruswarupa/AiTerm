#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import sys
import platform
import threading
import queue
import re
import json
from pathlib import Path
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
        self.root.title("✨ AI Terminal Assistant")
        self.root.geometry("1400x800")
        self.root.configure(bg='#0f0f23')
        
        self.config_file = Path.home() / '.ai_terminal_config.json'
        
        self.groq_api_key = self.load_api_key()
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
        self.shell = 'cmd.exe' if self.is_windows else 'bash'
        
        self.current_input_line = ""
        
        self.pending_command = None
        self.last_command = ""
        self.output_buffer = []
        self.process = None
        
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07\x1B]*(?:\x07|\x1B\\))')
        
        if not HAS_PTY:
            messagebox.showerror(
                "Missing Dependency",
                f"PTY library not found.\n"
                f"Install {'pywinpty' if self.is_windows else 'ptyprocess'} to use terminal features.\n\n"
                f"Command: pip install {'pywinpty' if self.is_windows else 'ptyprocess'}"
            )
        
        self.setup_ui()
        self.start_terminal()
    
    def load_api_key(self):
        api_key = os.environ.get('GROQ_API_KEY', '')
        if api_key:
            return api_key
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    api_key = config.get('GROQ_API_KEY', '')
                    if api_key:
                        os.environ['GROQ_API_KEY'] = api_key
                    return api_key
            except Exception:
                pass
        
        return ''
    
    def save_api_key(self, api_key):
        try:
            config = {}
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                except Exception:
                    pass
            
            config['GROQ_API_KEY'] = api_key
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
            self.config_file.chmod(0o600)
            
            return True
        except Exception as e:
            print(f"Failed to save API key: {e}")
            return False
        
    def setup_ui(self):
        outer_frame = tk.Frame(self.root, bg='#0f0f23')
        outer_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        main_container = tk.PanedWindow(
            outer_frame, 
            orient=tk.HORIZONTAL, 
            bg='#0f0f23',
            sashwidth=8,
            sashrelief=tk.FLAT,
            sashpad=3
        )
        main_container.pack(fill=tk.BOTH, expand=True)
        
        terminal_frame = tk.Frame(main_container, bg='#1a1a2e', relief=tk.FLAT, bd=0)
        
        terminal_header = tk.Frame(terminal_frame, bg='#16213e', height=60)
        terminal_header.pack(fill=tk.X)
        terminal_header.pack_propagate(False)
        
        terminal_title_frame = tk.Frame(terminal_header, bg='#16213e')
        terminal_title_frame.pack(side=tk.LEFT, padx=20, pady=12)
        
        terminal_icon = tk.Label(
            terminal_title_frame,
            text="💻",
            bg='#16213e',
            font=('Segoe UI Emoji', 20)
        )
        terminal_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        terminal_label = tk.Label(
            terminal_title_frame, 
            text="Terminal", 
            bg='#16213e', 
            fg='#e0e0ff',
            font=('Segoe UI', 14, 'bold')
        )
        terminal_label.pack(side=tk.LEFT)
        
        terminal_display_frame = tk.Frame(terminal_frame, bg='#1a1a2e')
        terminal_display_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        self.terminal_display = scrolledtext.ScrolledText(
            terminal_display_frame,
            bg='#0a0e27',
            fg='#00ff88',
            font=('Consolas', 11),
            insertbackground='#00ff88',
            wrap=tk.WORD,
            state=tk.NORMAL,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=2,
            highlightbackground='#2a2a4e',
            highlightcolor='#4a4aff',
            padx=12,
            pady=12
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)
        self.terminal_display.bind('<KeyPress>', self.handle_key_press)
        
        ai_frame = tk.Frame(main_container, bg='#1a1a2e', width=500, relief=tk.FLAT, bd=0)
        
        ai_header = tk.Frame(ai_frame, bg='#7b2cbf', height=60)
        ai_header.pack(fill=tk.X)
        ai_header.pack_propagate(False)
        
        ai_title_frame = tk.Frame(ai_header, bg='#7b2cbf')
        ai_title_frame.pack(side=tk.LEFT, padx=20, pady=12)
        
        ai_icon = tk.Label(
            ai_title_frame,
            text="✨",
            bg='#7b2cbf',
            font=('Segoe UI Emoji', 20)
        )
        ai_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        ai_label = tk.Label(
            ai_title_frame, 
            text="AI Assistant", 
            bg='#7b2cbf', 
            fg='#ffffff',
            font=('Segoe UI', 14, 'bold')
        )
        ai_label.pack(side=tk.LEFT)
        
        settings_button = tk.Button(
            ai_header,
            text="⚙",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 16),
            command=self.open_settings,
            cursor='hand2',
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=8,
            activebackground='#c77dff',
            activeforeground='white'
        )
        settings_button.pack(side=tk.RIGHT, padx=15)
        
        ai_chat_frame = tk.Frame(ai_frame, bg='#1a1a2e')
        ai_chat_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        self.ai_chat = scrolledtext.ScrolledText(
            ai_chat_frame,
            bg='#0a0e27',
            fg='#e0e0ff',
            font=('Segoe UI', 11),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=2,
            highlightbackground='#2a2a4e',
            highlightcolor='#9d4edd',
            padx=15,
            pady=15
        )
        self.ai_chat.pack(fill=tk.BOTH, expand=True)
        
        self.ai_chat.tag_config('user', foreground='#c77dff', font=('Segoe UI', 11, 'bold'))
        self.ai_chat.tag_config('ai', foreground='#00ff88', font=('Segoe UI', 11))
        self.ai_chat.tag_config('system', foreground='#ffd700', font=('Segoe UI', 10, 'italic'))
        self.ai_chat.tag_config('command', background='#16213e', foreground='#00d4ff', font=('Consolas', 10), spacing1=5, spacing3=5)
        self.ai_chat.tag_config('error', foreground='#ff6b9d', font=('Segoe UI', 11))
        
        input_frame = tk.Frame(ai_frame, bg='#1a1a2e')
        input_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        
        input_container = tk.Frame(input_frame, bg='#16213e', highlightthickness=2, highlightbackground='#2a2a4e', highlightcolor='#9d4edd')
        input_container.pack(fill=tk.X)
        
        self.ai_input = tk.Entry(
            input_container,
            bg='#16213e',
            fg='#e0e0ff',
            font=('Segoe UI', 12),
            insertbackground='#c77dff',
            relief=tk.FLAT,
            borderwidth=0
        )
        self.ai_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=12)
        self.ai_input.bind('<Return>', lambda e: self.ask_ai())
        
        self.ask_button = tk.Button(
            input_container,
            text="Ask AI ✨",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            command=self.ask_ai,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            activebackground='#c77dff',
            activeforeground='white'
        )
        self.ask_button.pack(side=tk.RIGHT, padx=8, pady=6)
        
        main_container.add(terminal_frame, width=850)
        main_container.add(ai_frame, width=550)
        
        self.add_ai_message("👋 Welcome! Ask me for any command and I'll help you out!", 'system')
        
    def start_terminal(self):
        if not HAS_PTY:
            return
            
        try:
            self.output_queue = queue.Queue()
            
            if self.is_windows:
                self.process = PtyProcess.spawn([self.shell], dimensions=(30, 100))
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
                
                if '\x1b[2J' in output or '\x1b[H\x1b[2J' in output or '\x1b[3J' in output:
                    self.root.after(0, self.clear_terminal_screen)
                
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
        cleaned = self.ansi_escape.sub('', text)
        cleaned = re.sub(r'\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)', '', cleaned)
        cleaned = re.sub(r'\x9D[^\x9C]*\x9C', '', cleaned)
        cleaned = re.sub(r'^\d+;\d+;\d+;\d+\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\d+;\d+;\d+;\d+\s+[-\\|/]\s+', '', cleaned)
        cleaned = re.sub(r'^\d+;[^\n\r]+?(?=\n|\r|$)', '', cleaned, flags=re.MULTILINE)
        return cleaned
    
    def clear_terminal_screen(self):
        self.terminal_display.delete('1.0', tk.END)
    
    def update_terminal_display(self):
        try:
            while True:
                output = self.output_queue.get_nowait()
                clean_output = self.strip_ansi_codes(output)
                
                i = 0
                while i < len(clean_output):
                    char = clean_output[i]
                    
                    if char == '\b' or char == '\x7f':
                        current_content = self.terminal_display.get('1.0', tk.END)
                        if len(current_content) > 1:
                            self.terminal_display.delete(f"{tk.END}-2c")
                    elif char == '\r':
                        if i + 1 < len(clean_output) and clean_output[i + 1] == '\n':
                            pass
                        else:
                            current_line_start = self.terminal_display.index(f"{tk.END} linestart")
                            self.terminal_display.delete(current_line_start, f"{tk.END}-1c")
                    else:
                        self.terminal_display.insert(tk.END, char)
                    
                    i += 1
                
                self.terminal_display.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.update_terminal_display)
            
    def handle_key_press(self, event):
        if event.keysym == 'BackSpace':
            if self.is_windows:
                self.write_to_terminal('\b')
            else:
                self.write_to_terminal('\x7f')
        elif event.keysym == 'Return':
            self.write_to_terminal('\n')
        elif event.keysym == 'Tab':
            self.write_to_terminal('\t')
        elif event.keysym == 'Up':
            self.write_to_terminal('\x1b[A')
        elif event.keysym == 'Down':
            self.write_to_terminal('\x1b[B')
        elif event.keysym == 'Right':
            self.write_to_terminal('\x1b[C')
        elif event.keysym == 'Left':
            self.write_to_terminal('\x1b[D')
        elif event.keysym == 'Home':
            self.write_to_terminal('\x1b[H')
        elif event.keysym == 'End':
            self.write_to_terminal('\x1b[F')
        elif event.keysym == 'Delete':
            self.write_to_terminal('\x1b[3~')
        elif event.state & 0x4 and event.keysym == 'c':
            if event.state & 0x1:
                return None
            try:
                if self.terminal_display.tag_ranges(tk.SEL):
                    return None
            except:
                pass
            self.write_to_terminal('\x03')
        elif event.state & 0x4 and event.keysym == 'd':
            self.write_to_terminal('\x04')
        elif event.state & 0x4 and event.keysym == 'z':
            self.write_to_terminal('\x1a')
        elif event.state & 0x4 and event.keysym == 'l':
            self.write_to_terminal('\x0c')
        elif event.char:
            self.write_to_terminal(event.char)
        else:
            return None
        return 'break'
                
    def write_to_terminal(self, data):
        if self.process:
            if self.is_windows:
                data = data.replace('\n', '\r\n')
            self.process.write(data)
            
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
        
        confirm_frame = tk.Frame(self.ai_chat, bg='#0a0e27')
        self.ai_chat.window_create(tk.END, window=confirm_frame)
        
        tk.Button(
            confirm_frame,
            text="✓ Execute",
            bg='#00ff88',
            fg='#0a0e27',
            command=lambda: self.execute_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8,
            activebackground='#00cc66',
            activeforeground='#0a0e27'
        ).pack(side=tk.LEFT, padx=8, pady=8)
        
        tk.Button(
            confirm_frame,
            text="✗ Cancel",
            bg='#ff6b9d',
            fg='white',
            command=lambda: self.cancel_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8,
            activebackground='#ff4477',
            activeforeground='white'
        ).pack(side=tk.LEFT, padx=8, pady=8)
        
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
        settings_dialog.title("⚙ Settings")
        settings_dialog.geometry("550x320")
        settings_dialog.configure(bg='#0f0f23')
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        
        center_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 275
        center_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 160
        settings_dialog.geometry(f"+{center_x}+{center_y}")
        
        header = tk.Frame(settings_dialog, bg='#7b2cbf', height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="⚙ Settings",
            bg='#7b2cbf',
            fg='white',
            font=('Segoe UI', 18, 'bold'),
            pady=20
        )
        title_label.pack()
        
        content_frame = tk.Frame(settings_dialog, bg='#0f0f23')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        info_label = tk.Label(
            content_frame,
            text="Enter your Groq API Key\nGet a free key at: https://console.groq.com/keys",
            bg='#0f0f23',
            fg='#ffd700',
            font=('Segoe UI', 10),
            justify=tk.LEFT
        )
        info_label.pack(anchor=tk.W, pady=(0, 15))
        
        key_label = tk.Label(
            content_frame,
            text="API Key:",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 11, 'bold')
        )
        key_label.pack(anchor=tk.W, pady=(0, 8))
        
        key_container = tk.Frame(content_frame, bg='#16213e', highlightthickness=2, highlightbackground='#2a2a4e', highlightcolor='#9d4edd')
        key_container.pack(fill=tk.X, pady=(0, 8))
        
        key_entry = tk.Entry(
            key_container,
            bg='#16213e',
            fg='#e0e0ff',
            font=('Consolas', 11),
            insertbackground='#c77dff',
            show='•',
            relief=tk.FLAT,
            borderwidth=0
        )
        key_entry.pack(fill=tk.X, padx=12, pady=10)
        key_entry.insert(0, self.groq_api_key if self.groq_api_key else '')
        key_entry.focus_set()
        
        show_var = tk.BooleanVar(value=False)
        
        def toggle_show():
            key_entry.config(show='' if show_var.get() else '•')
        
        show_check = tk.Checkbutton(
            content_frame,
            text="Show API Key",
            variable=show_var,
            command=toggle_show,
            bg='#0f0f23',
            fg='#c77dff',
            selectcolor='#16213e',
            activebackground='#0f0f23',
            activeforeground='#e0e0ff',
            font=('Segoe UI', 10)
        )
        show_check.pack(anchor=tk.W, pady=(0, 20))
        
        def save_settings():
            new_key = key_entry.get().strip()
            if new_key:
                success = self.update_api_key(new_key)
                if success:
                    settings_dialog.destroy()
                    messagebox.showinfo("Settings Saved", "API key has been updated and saved successfully!")
                else:
                    messagebox.showerror("Invalid API Key", "Failed to initialize Groq client. Please check your API key and try again.")
            else:
                messagebox.showwarning("Invalid Input", "Please enter a valid API key")
        
        def cancel_settings():
            settings_dialog.destroy()
        
        button_frame = tk.Frame(content_frame, bg='#0f0f23')
        button_frame.pack(fill=tk.X)
        
        save_button = tk.Button(
            button_frame,
            text="💾 Save",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            command=save_settings,
            cursor='hand2',
            relief=tk.FLAT,
            padx=25,
            pady=10,
            activebackground='#c77dff',
            activeforeground='white'
        )
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_button = tk.Button(
            button_frame,
            text="✗ Cancel",
            bg='#2a2a4e',
            fg='#e0e0ff',
            font=('Segoe UI', 11, 'bold'),
            command=cancel_settings,
            cursor='hand2',
            relief=tk.FLAT,
            padx=25,
            pady=10,
            activebackground='#3a3a5e',
            activeforeground='white'
        )
        cancel_button.pack(side=tk.LEFT)
        
        key_entry.bind('<Return>', lambda e: save_settings())
        key_entry.bind('<Escape>', lambda e: cancel_settings())
    
    def update_api_key(self, new_key):
        self.groq_api_key = new_key
        try:
            self.groq_client = Groq(api_key=new_key)
            
            os.environ['GROQ_API_KEY'] = new_key
            
            if self.save_api_key(new_key):
                self.add_ai_message("✅ API key updated and saved successfully!", 'system')
            else:
                self.add_ai_message("✅ API key updated for this session (save failed)", 'system')
            
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
