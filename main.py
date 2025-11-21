#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
import platform
import threading
import queue
import re
import json
from pathlib import Path
from datetime import datetime
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
        self.root.geometry("1400x950")
        self.root.configure(bg='#0f0f23')
        
        # Set minimum window size
        self.root.minsize(1200, 700)
        
        # Configuration
        self.config_file = Path.home() / '.ai_terminal_config.json'
        self.load_config()
        
        # API Setup
        self.groq_api_key = self.load_api_key()
        if not self.groq_api_key:
            self.show_api_key_dialog()
        else:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                messagebox.showerror("Groq Error", f"Failed to initialize Groq client: {e}")
                self.groq_client = None
        
        # Terminal setup
        self.is_windows = platform.system() == 'Windows'
        self.shell = 'cmd.exe' if self.is_windows else 'bash'
        
        # State management
        self.current_input_line = ""
        self.pending_command = None
        self.last_command = ""
        self.output_buffer = []
        self.process = None
        self.command_history = []
        self.history_index = -1
        
        # ANSI escape pattern
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07\x1B]*(?:\x07|\x1B\\))')
        
        # Theme
        self.current_theme = self.config.get('theme', 'dark')
        self.themes = {
            'dark': {
                'bg': '#0f0f23',
                'fg': '#e0e0ff',
                'terminal_bg': '#0a0e27',
                'terminal_fg': '#00ff88',
                'ai_header': '#7b2cbf',
                'terminal_header': '#16213e',
                'input_bg': '#16213e',
                'button_bg': '#9d4edd',
                'button_hover': '#c77dff'
            },
            'light': {
                'bg': '#f0f0f5',
                'fg': '#1a1a2e',
                'terminal_bg': '#ffffff',
                'terminal_fg': '#008844',
                'ai_header': '#9d4edd',
                'terminal_header': '#c0c0d0',
                'input_bg': '#e8e8f0',
                'button_bg': '#7b2cbf',
                'button_hover': '#9d4edd'
            }
        }
        
        if not HAS_PTY:
            messagebox.showerror(
                "Missing Dependency",
                f"PTY library not found.\n"
                f"Install {'pywinpty' if self.is_windows else 'ptyprocess'} to use terminal features.\n\n"
                f"Command: pip install {'pywinpty' if self.is_windows else 'ptyprocess'}"
            )
        
        self.setup_ui()
        self.start_terminal()
        
        # Keyboard shortcuts
        self.setup_shortcuts()
    
    def load_config(self):
        """Load configuration from file"""
        self.config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except Exception:
                pass
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
            self.config_file.chmod(0o600)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    def load_api_key(self):
        """Load API key from environment or config"""
        api_key = os.environ.get('GROQ_API_KEY', '')
        if api_key:
            return api_key
        
        api_key = self.config.get('GROQ_API_KEY', '')
        if api_key:
            os.environ['GROQ_API_KEY'] = api_key
        return api_key
    
    def save_api_key(self, api_key):
        """Save API key to config"""
        try:
            self.config['GROQ_API_KEY'] = api_key
            return self.save_config()
        except Exception as e:
            print(f"Failed to save API key: {e}")
            return False
    
    def show_api_key_dialog(self):
        """Show API key setup dialog on first run"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Welcome to AI Terminal")
        dialog.geometry("600x400")
        dialog.configure(bg='#0f0f23')
        dialog.transient(self.root)
        dialog.grab_set()
        
        center_x = self.root.winfo_screenwidth() // 2 - 300
        center_y = self.root.winfo_screenheight() // 2 - 200
        dialog.geometry(f"+{center_x}+{center_y}")
        
        # Header
        header = tk.Frame(dialog, bg='#7b2cbf', height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="✨ Welcome to AI Terminal Assistant",
            bg='#7b2cbf',
            fg='white',
            font=('Segoe UI', 16, 'bold')
        )
        title_label.pack(pady=25)
        
        # Content
        content_frame = tk.Frame(dialog, bg='#0f0f23')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)
        
        info_text = tk.Label(
            content_frame,
            text="To use AI features, you need a Groq API key.\n\n"
                 "Get your free API key at:\nhttps://console.groq.com/keys\n\n"
                 "You can also skip this and add it later in Settings.",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 11),
            justify=tk.LEFT
        )
        info_text.pack(anchor=tk.W, pady=(0, 20))
        
        key_label = tk.Label(
            content_frame,
            text="API Key (optional):",
            bg='#0f0f23',
            fg='#ffd700',
            font=('Segoe UI', 11, 'bold')
        )
        key_label.pack(anchor=tk.W, pady=(0, 8))
        
        key_container = tk.Frame(content_frame, bg='#16213e', highlightthickness=2, 
                                highlightbackground='#2a2a4e', highlightcolor='#9d4edd')
        key_container.pack(fill=tk.X, pady=(0, 8))
        
        key_entry = tk.Entry(
            key_container,
            bg='#16213e',
            fg='#e0e0ff',
            font=('Consolas', 10),
            insertbackground='#c77dff',
            relief=tk.FLAT,
            borderwidth=0
        )
        key_entry.pack(fill=tk.X, padx=12, pady=10)
        key_entry.focus_set()
        
        def save_and_continue():
            api_key = key_entry.get().strip()
            if api_key:
                if self.update_api_key(api_key):
                    dialog.destroy()
                    messagebox.showinfo("Success", "API key saved successfully!")
                else:
                    messagebox.showerror("Error", "Invalid API key. Please check and try again.")
            else:
                dialog.destroy()
        
        def skip():
            self.groq_client = None
            dialog.destroy()
        
        button_frame = tk.Frame(content_frame, bg='#0f0f23')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_button = tk.Button(
            button_frame,
            text="💾 Save & Continue",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            command=save_and_continue,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        skip_button = tk.Button(
            button_frame,
            text="Skip",
            bg='#2a2a4e',
            fg='#e0e0ff',
            font=('Segoe UI', 11),
            command=skip,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        skip_button.pack(side=tk.LEFT)
        
        key_entry.bind('<Return>', lambda e: save_and_continue())
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-l>', lambda e: self.clear_terminal())
        self.root.bind('<Control-k>', lambda e: self.clear_ai_chat())
        self.root.bind('<Control-s>', lambda e: self.save_terminal_output())
        self.root.bind('<F1>', lambda e: self.show_help())
        
    def setup_ui(self):
        """Setup the user interface"""
        # Outer frame
        outer_frame = tk.Frame(self.root, bg='#0f0f23')
        outer_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Top menu bar
        menu_bar = tk.Frame(outer_frame, bg='#16213e', height=40)
        menu_bar.pack(fill=tk.X, pady=(0, 10))
        menu_bar.pack_propagate(False)
        
        # Menu buttons
        menu_buttons = [
            ("💾 Save Output", self.save_terminal_output),
            ("🗑️ Clear Terminal", self.clear_terminal),
            ("💬 Clear Chat", self.clear_ai_chat),
            ("🎨 Theme", self.toggle_theme),
            ("❓ Help", self.show_help)
        ]
        
        for text, command in menu_buttons:
            btn = tk.Button(
                menu_bar,
                text=text,
                bg='#16213e',
                fg='#e0e0ff',
                font=('Segoe UI', 9),
                command=command,
                cursor='hand2',
                relief=tk.FLAT,
                padx=12,
                pady=5
            )
            btn.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Hover effect
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#2a2a4e'))
            btn.bind('<Leave>', lambda e, b=btn: b.config(bg='#16213e'))
        
        # Status label
        self.status_label = tk.Label(
            menu_bar,
            text="Ready",
            bg='#16213e',
            fg='#00ff88',
            font=('Segoe UI', 9),
            anchor=tk.E
        )
        self.status_label.pack(side=tk.RIGHT, padx=15)
        
        # Main container with resizable panes
        main_container = tk.PanedWindow(
            outer_frame, 
            orient=tk.HORIZONTAL, 
            bg='#0f0f23',
            sashwidth=8,
            sashrelief=tk.FLAT,
            sashpad=3
        )
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Terminal frame
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
        
        # Font size controls
        font_frame = tk.Frame(terminal_header, bg='#16213e')
        font_frame.pack(side=tk.RIGHT, padx=15)
        
        self.font_size = tk.IntVar(value=11)
        
        tk.Button(
            font_frame,
            text="A-",
            bg='#2a2a4e',
            fg='#e0e0ff',
            font=('Segoe UI', 9),
            command=self.decrease_font,
            cursor='hand2',
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            font_frame,
            text="A+",
            bg='#2a2a4e',
            fg='#e0e0ff',
            font=('Segoe UI', 9),
            command=self.increase_font,
            cursor='hand2',
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side=tk.LEFT, padx=2)
        
        terminal_display_frame = tk.Frame(terminal_frame, bg='#1a1a2e')
        terminal_display_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        self.terminal_display = scrolledtext.ScrolledText(
            terminal_display_frame,
            bg='#0a0e27',
            fg='#00ff88',
            font=('Consolas', self.font_size.get()),
            insertbackground='#00ff88',
            wrap=tk.WORD,
            state=tk.NORMAL,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=2,
            highlightbackground='#2a2a4e',
            highlightcolor='#4a4aff',
            padx=12,
            pady=12,
            undo=True,
            maxundo=-1
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)
        self.terminal_display.bind('<KeyPress>', self.handle_key_press)
        
        # AI frame
        ai_frame = tk.Frame(main_container, bg='#1a1a2e', width=550, relief=tk.FLAT, bd=0)
        
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
            pady=8
        )
        settings_button.pack(side=tk.RIGHT, padx=15)
        
        # Hover effect for settings button
        settings_button.bind('<Enter>', lambda e: settings_button.config(bg='#c77dff'))
        settings_button.bind('<Leave>', lambda e: settings_button.config(bg='#9d4edd'))
        
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
        
        # AI chat tags
        self.ai_chat.tag_config('user', foreground='#c77dff', font=('Segoe UI', 11, 'bold'))
        self.ai_chat.tag_config('ai', foreground='#00ff88', font=('Segoe UI', 11))
        self.ai_chat.tag_config('system', foreground='#ffd700', font=('Segoe UI', 10, 'italic'))
        self.ai_chat.tag_config('command', background='#16213e', foreground='#00d4ff', 
                               font=('Consolas', 10), spacing1=5, spacing3=5)
        self.ai_chat.tag_config('error', foreground='#ff6b9d', font=('Segoe UI', 11))
        self.ai_chat.tag_config('timestamp', foreground='#808090', font=('Segoe UI', 9))
        
        # Input frame
        input_frame = tk.Frame(ai_frame, bg='#1a1a2e', height=80)
        input_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        input_frame.pack_propagate(False)
        
        input_container = tk.Frame(input_frame, bg='#16213e', highlightthickness=2, 
                                  highlightbackground='#2a2a4e', highlightcolor='#9d4edd')
        input_container.pack(fill=tk.BOTH, expand=True)
        
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
        self.ai_input.bind('<Up>', self.history_up)
        self.ai_input.bind('<Down>', self.history_down)
        
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
            pady=12
        )
        self.ask_button.pack(side=tk.RIGHT, padx=8, pady=8)
        
        # Hover effect for ask button
        self.ask_button.bind('<Enter>', lambda e: self.ask_button.config(bg='#c77dff'))
        self.ask_button.bind('<Leave>', lambda e: self.ask_button.config(bg='#9d4edd'))
        
        main_container.add(terminal_frame, width=850)
        main_container.add(ai_frame, width=550)
        
        # Welcome message
        welcome_msg = (
            "👋 Welcome to AI Terminal Assistant!\n\n"
            "Ask me for any command and I'll help you out.\n"
            "Try: 'list all files' or 'check disk space'"
        )
        self.add_ai_message(welcome_msg, 'system')
    
    def history_up(self, event):
        """Navigate up in AI input history"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.ai_input.delete(0, tk.END)
            self.ai_input.insert(0, self.command_history[-(self.history_index + 1)])
        return 'break'
    
    def history_down(self, event):
        """Navigate down in AI input history"""
        if self.history_index > 0:
            self.history_index -= 1
            self.ai_input.delete(0, tk.END)
            self.ai_input.insert(0, self.command_history[-(self.history_index + 1)])
        elif self.history_index == 0:
            self.history_index = -1
            self.ai_input.delete(0, tk.END)
        return 'break'
    
    def increase_font(self):
        """Increase terminal font size"""
        current = self.font_size.get()
        if current < 20:
            self.font_size.set(current + 1)
            self.terminal_display.config(font=('Consolas', self.font_size.get()))
    
    def decrease_font(self):
        """Decrease terminal font size"""
        current = self.font_size.get()
        if current > 8:
            self.font_size.set(current - 1)
            self.terminal_display.config(font=('Consolas', self.font_size.get()))
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.config['theme'] = self.current_theme
        self.save_config()
        messagebox.showinfo("Theme", "Theme will be applied on next restart")
    
    def clear_terminal(self):
        """Clear terminal display"""
        self.terminal_display.delete('1.0', tk.END)
        self.update_status("Terminal cleared")
    
    def clear_ai_chat(self):
        """Clear AI chat"""
        self.ai_chat.config(state=tk.NORMAL)
        self.ai_chat.delete('1.0', tk.END)
        self.ai_chat.config(state=tk.DISABLED)
        self.add_ai_message("Chat cleared. How can I help you?", 'system')
        self.update_status("Chat cleared")
    
    def save_terminal_output(self):
        """Save terminal output to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"terminal_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                content = self.terminal_display.get('1.0', tk.END)
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Saved", f"Output saved to {filename}")
                self.update_status("Output saved")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
    
    def show_help(self):
        """Show help dialog"""
        help_text = """
AI Terminal Assistant - Help

KEYBOARD SHORTCUTS:
• Ctrl+L - Clear terminal
• Ctrl+K - Clear AI chat
• Ctrl+S - Save terminal output
• F1 - Show this help
• Up/Down arrows in AI input - Navigate history

FEATURES:
• Ask AI for commands in natural language
• Automatic error detection and suggestions
• Command execution with confirmation
• Resizable panes
• Adjustable font size
• Save terminal output

TIPS:
• Be specific in your requests
• Use natural language (e.g., "list all files")
• Review commands before executing
• Check error suggestions when commands fail

Get your Groq API key at:
https://console.groq.com/keys
        """
        
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("Help")
        help_dialog.geometry("600x500")
        help_dialog.configure(bg='#0f0f23')
        help_dialog.transient(self.root)
        
        header = tk.Frame(help_dialog, bg='#7b2cbf', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="❓ Help & Documentation",
            bg='#7b2cbf',
            fg='white',
            font=('Segoe UI', 16, 'bold')
        ).pack(pady=15)
        
        text_frame = tk.Frame(help_dialog, bg='#0f0f23')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        help_display = scrolledtext.ScrolledText(
            text_frame,
            bg='#0a0e27',
            fg='#e0e0ff',
            font=('Segoe UI', 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        help_display.pack(fill=tk.BOTH, expand=True)
        help_display.insert('1.0', help_text)
        help_display.config(state=tk.DISABLED)
        
        tk.Button(
            help_dialog,
            text="Close",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            command=help_dialog.destroy,
            cursor='hand2',
            relief=tk.FLAT,
            padx=30,
            pady=10
        ).pack(pady=(0, 20))
    
    def update_status(self, message, duration=3000):
        """Update status label"""
        self.status_label.config(text=message)
        if duration > 0:
            self.root.after(duration, lambda: self.status_label.config(text="Ready"))
        
    def start_terminal(self):
        """Start terminal process"""
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
            self.update_status("Terminal started")
        except Exception as e:
            messagebox.showerror("Terminal Error", f"Failed to start terminal: {e}")
            
    def read_terminal_output(self):
        """Read terminal output in background thread"""
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
        """Remove ANSI escape codes from text"""
        cleaned = self.ansi_escape.sub('', text)
        cleaned = re.sub(r'\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)', '', cleaned)
        cleaned = re.sub(r'\x9D[^\x9C]*\x9C', '', cleaned)
        cleaned = re.sub(r'^\d+;\d+;\d+;\d+\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\d+;\d+;\d+;\d+\s+[-\\|/]\s+', '', cleaned)
        cleaned = re.sub(r'^\d+;[^\n\r]+?(?=\n|\r|$)', '', cleaned, flags=re.MULTILINE)
        return cleaned
    
    def clear_terminal_screen(self):
        """Clear terminal screen"""
        self.terminal_display.delete('1.0', tk.END)
    
    def update_terminal_display(self):
        """Update terminal display with new output"""
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
        """Handle key press events in terminal"""
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
            return None  # Let our shortcut handler deal with it
        elif event.char:
            self.write_to_terminal(event.char)
        else:
            return None
        return 'break'
                
    def write_to_terminal(self, data):
        """Write data to terminal"""
        if self.process:
            if self.is_windows:
                data = data.replace('\n', '\r\n')
            self.process.write(data)
            
    def add_ai_message(self, message, tag='ai'):
        """Add message to AI chat"""
        self.ai_chat.config(state=tk.NORMAL)
        
        # Add timestamp for user messages
        if tag == 'user':
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.ai_chat.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        self.ai_chat.insert(tk.END, f"{message}\n", tag)
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state=tk.DISABLED)
        
    def ask_ai(self):
        """Ask AI for command suggestion"""
        query = self.ai_input.get().strip()
        if not query:
            return
            
        if not self.groq_client:
            messagebox.showwarning(
                "AI Not Available",
                "Groq API client not initialized. Please set your API key in Settings."
            )
            return
        
        # Add to history
        if not self.command_history or self.command_history[-1] != query:
            self.command_history.append(query)
        self.history_index = -1
            
        self.ai_input.delete(0, tk.END)
        self.add_ai_message(f"You: {query}", 'user')
        self.add_ai_message("⏳ Thinking...", 'system')
        self.update_status("Processing request...")
        
        threading.Thread(target=self.get_command_suggestion, args=(query,), daemon=True).start()
        
    def get_command_suggestion(self, query):
        """Get command suggestion from AI"""
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
            self.root.after(0, lambda: self.update_status("Command ready"))
            
        except Exception as e:
            self.root.after(0, lambda: self.add_ai_message(f"❌ Error: {str(e)}", 'error'))
            self.root.after(0, lambda: self.update_status("Error occurred"))
            
    def show_command_suggestion(self, command):
        """Show command suggestion with execute/cancel buttons"""
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
        
        execute_btn = tk.Button(
            confirm_frame,
            text="✓ Execute",
            bg='#00ff88',
            fg='#0a0e27',
            command=lambda: self.execute_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8
        )
        execute_btn.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Hover effect
        execute_btn.bind('<Enter>', lambda e: execute_btn.config(bg='#00cc66'))
        execute_btn.bind('<Leave>', lambda e: execute_btn.config(bg='#00ff88'))
        
        cancel_btn = tk.Button(
            confirm_frame,
            text="✗ Cancel",
            bg='#ff6b9d',
            fg='white',
            command=lambda: self.cancel_pending_command(confirm_frame),
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8
        )
        cancel_btn.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Hover effect
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#ff4477'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#ff6b9d'))
        
        copy_btn = tk.Button(
            confirm_frame,
            text="📋 Copy",
            bg='#4a4aff',
            fg='white',
            command=lambda: self.copy_command(command),
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8
        )
        copy_btn.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Hover effect
        copy_btn.bind('<Enter>', lambda e: copy_btn.config(bg='#6a6aff'))
        copy_btn.bind('<Leave>', lambda e: copy_btn.config(bg='#4a4aff'))
        
        self.ai_chat.config(state=tk.NORMAL)
        self.ai_chat.insert(tk.END, "\n")
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state=tk.DISABLED)
    
    def copy_command(self, command):
        """Copy command to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(command)
        self.update_status("Command copied to clipboard")
        
    def execute_pending_command(self, frame):
        """Execute pending command"""
        if self.pending_command:
            frame.destroy()
            self.add_ai_message(f"✅ Executed: {self.pending_command}", 'system')
            
            self.last_command = self.pending_command
            self.output_buffer = []
            
            try:
                self.write_to_terminal(self.pending_command + '\n')
                self.terminal_display.focus_set()
                self.update_status("Command executed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to execute command: {e}")
                
            self.pending_command = None
            
    def cancel_pending_command(self, frame):
        """Cancel pending command"""
        frame.destroy()
        self.add_ai_message("❌ Command cancelled", 'system')
        self.pending_command = None
        self.update_status("Command cancelled")
        
    def detect_error(self):
        """Detect and analyze errors"""
        if not self.last_command or not self.groq_client:
            return
            
        error_output = ''.join(self.output_buffer[-20:])
        
        self.root.after(0, lambda: self.add_ai_message(f"⚠️ Error detected in: {self.last_command}", 'error'))
        self.root.after(0, lambda: self.add_ai_message("⏳ Analyzing error...", 'system'))
        self.root.after(0, lambda: self.update_status("Analyzing error..."))
        
        threading.Thread(
            target=self.troubleshoot_error,
            args=(self.last_command, error_output),
            daemon=True
        ).start()
        
        self.last_command = ""
        
    def troubleshoot_error(self, command, error_output):
        """Troubleshoot command error"""
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
            self.root.after(0, lambda: self.update_status("Error analysis complete"))
            
        except Exception as e:
            self.root.after(0, lambda: self.add_ai_message(f"❌ Failed to analyze: {str(e)}", 'error'))
            self.root.after(0, lambda: self.update_status("Analysis failed"))
            
    def show_troubleshooting_result(self, solution):
        """Show troubleshooting result"""
        self.ai_chat.config(state=tk.NORMAL)
        last_line = self.ai_chat.get("end-2l", "end-1l")
        if "⏳ Analyzing error..." in last_line:
            self.ai_chat.delete("end-2l", "end-1l")
        self.ai_chat.config(state=tk.DISABLED)
        
        self.add_ai_message(f"🔍 AI Analysis:\n{solution}", 'ai')
    
    def open_settings(self):
        """Open settings dialog"""
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("⚙ Settings")
        settings_dialog.geometry("650x550")
        settings_dialog.configure(bg='#0f0f23')
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        
        center_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 325
        center_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
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
        
        # API Key section
        api_section = tk.LabelFrame(
            content_frame,
            text="API Configuration",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 11, 'bold'),
            relief=tk.FLAT
        )
        api_section.pack(fill=tk.X, pady=(0, 20))
        
        info_label = tk.Label(
            api_section,
            text="Get your free API key at: https://console.groq.com/keys",
            bg='#0f0f23',
            fg='#ffd700',
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        info_label.pack(anchor=tk.W, padx=15, pady=(10, 5))
        info_label.bind('<Button-1>', lambda e: self.open_url('https://console.groq.com/keys'))
        
        key_label = tk.Label(
            api_section,
            text="API Key:",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 10, 'bold')
        )
        key_label.pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        key_container = tk.Frame(api_section, bg='#16213e', highlightthickness=2, 
                                highlightbackground='#2a2a4e', highlightcolor='#9d4edd')
        key_container.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        key_entry = tk.Entry(
            key_container,
            bg='#16213e',
            fg='#e0e0ff',
            font=('Consolas', 10),
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
            api_section,
            text="Show API Key",
            variable=show_var,
            command=toggle_show,
            bg='#0f0f23',
            fg='#c77dff',
            selectcolor='#16213e',
            activebackground='#0f0f23',
            activeforeground='#e0e0ff',
            font=('Segoe UI', 9)
        )
        show_check.pack(anchor=tk.W, padx=15, pady=(0, 10))
        
        # Model selection
        model_section = tk.LabelFrame(
            content_frame,
            text="Model Settings",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 11, 'bold'),
            relief=tk.FLAT
        )
        model_section.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            model_section,
            text="AI Model:",
            bg='#0f0f23',
            fg='#e0e0ff',
            font=('Segoe UI', 10)
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        model_var = tk.StringVar(value="llama-3.3-70b-versatile")
        model_dropdown = ttk.Combobox(
            model_section,
            textvariable=model_var,
            values=["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
            state="readonly",
            font=('Segoe UI', 10)
        )
        model_dropdown.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        def save_settings():
            new_key = key_entry.get().strip()
            if new_key and new_key != self.groq_api_key:
                success = self.update_api_key(new_key)
                if success:
                    settings_dialog.destroy()
                    messagebox.showinfo("Settings Saved", "API key has been updated and saved successfully!")
                else:
                    messagebox.showerror("Invalid API Key", "Failed to initialize Groq client. Please check your API key.")
            else:
                settings_dialog.destroy()
        
        def cancel_settings():
            settings_dialog.destroy()
        
        button_frame = tk.Frame(content_frame, bg='#0f0f23')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_button = tk.Button(
            button_frame,
            text="💾 Save & Close",
            bg='#9d4edd',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            command=save_settings,
            cursor='hand2',
            relief=tk.FLAT,
            padx=25,
            pady=12
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
            pady=12
        )
        cancel_button.pack(side=tk.LEFT)
        
        key_entry.bind('<Return>', lambda e: save_settings())
        key_entry.bind('<Escape>', lambda e: cancel_settings())
    
    def open_url(self, url):
        """Open URL in browser"""
        import webbrowser
        webbrowser.open(url)
    
    def update_api_key(self, new_key):
        """Update API key"""
        self.groq_api_key = new_key
        try:
            self.groq_client = Groq(api_key=new_key)
            
            os.environ['GROQ_API_KEY'] = new_key
            
            if self.save_api_key(new_key):
                self.add_ai_message("✅ API key updated and saved successfully!", 'system')
                self.update_status("API key updated")
            else:
                self.add_ai_message("✅ API key updated for this session (save failed)", 'system')
            
            return True
        except Exception as e:
            self.groq_client = None
            self.add_ai_message(f"❌ Failed to initialize Groq client: {str(e)}", 'error')
            return False


def main():
    root = tk.Tk()
    
    # Set icon if available
    try:
        if platform.system() == 'Windows':
            root.iconbitmap('icon.ico')
        else:
            icon = tk.PhotoImage(file='icon.png')
            root.iconphoto(True, icon)
    except:
        pass
    
    app = AITerminal(root)
    root.mainloop()


if __name__ == '__main__':
    main()
