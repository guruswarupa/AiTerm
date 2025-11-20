# AI Terminal Assistant

A native desktop application that combines a terminal with AI-powered command assistance.

## Overview

This is a cross-platform native application built with Python and Tkinter that provides:
- **Live terminal** with full shell access (Bash on Linux, PowerShell on Windows)
- **AI assistant** powered by Groq's free API using Llama 3.3
- **Command suggestions** when you ask for help in natural language
- **Execution confirmation** before running AI-suggested commands
- **Automatic error detection** and AI-powered troubleshooting

## Recent Changes

- **2025-11-20**: Settings feature added
  - Added gear icon (⚙️) button in AI Assistant header
  - Implemented modal settings dialog for API key management
  - Added masked entry field with show/hide toggle
  - Implemented proper error handling for invalid API keys
  - API key can now be updated at runtime without restarting the app

- **2025-11-20**: Initial implementation
  - Created native desktop GUI with split-pane layout
  - Integrated Groq AI for command assistance
  - Implemented cross-platform terminal emulation (ptyprocess for Linux, subprocess for Windows)
  - Added command confirmation and error detection features
  - Configured VNC workflow for native desktop display
  - Fixed Windows compatibility by adding subprocess-based terminal backend

## Features

### Terminal (Left Pane)
- Fully functional terminal with your system shell
- Type commands directly as you would in a normal terminal
- Cross-platform support (Windows PowerShell / Linux Bash)
- Real-time output display

### AI Assistant (Right Pane)
- Ask for commands in plain English (e.g., "list all files")
- AI suggests the appropriate command
- Confirmation dialog before executing suggested commands
- Automatic error detection when commands fail
- AI-powered troubleshooting with solution suggestions

## How to Use

1. **Running the Application**: The app runs automatically via VNC workflow and displays in your browser
2. **Using the Terminal**: Click in the terminal pane and type commands normally
3. **Asking AI for Help**: 
   - Type your request in the AI input box (e.g., "find large files")
   - Click "Ask AI" or press Enter
   - Review the suggested command
   - Click "✓ Execute" to run it or "✗ Cancel" to reject
4. **Error Troubleshooting**: If a command fails, the AI automatically analyzes the error and suggests fixes

## Project Architecture

### Main Components

- `main.py`: Main application file
  - `AITerminal` class: Core application logic
  - Terminal emulation using ptyprocess (Linux) or subprocess (Windows)
  - Groq AI integration for command assistance
  - Tkinter GUI with split-pane layout
  - Cross-platform terminal backend with automatic OS detection

### Technology Stack

- **GUI Framework**: Python Tkinter (native desktop UI)
- **Terminal Emulation**: ptyprocess (cross-platform PTY handling)
- **AI Service**: Groq API with Llama 3.3-70B model (free tier)
- **Display**: VNC for streaming native desktop to browser

### Dependencies

- `groq`: Groq AI SDK for command suggestions and error analysis
- `ptyprocess`: Pseudo-terminal process management (Linux/Mac)
- `pywinpty`: Windows pseudo-terminal (ConPTY/WinPTY support)
- `psutil`: System utilities
- `tkinter`: Built-in Python GUI framework

**Platform-specific**:
- Linux/Mac: Uses `ptyprocess` for PTY (pre-installed on Replit)
- Windows: Uses `pywinpty` for ConPTY (Windows 10+) or WinPTY (legacy)
  - Windows users need to install: `pip install pywinpty`
  - The application detects the platform and uses the appropriate backend automatically

## Configuration

### Environment Variables

- `GROQ_API_KEY`: Your Groq API key (required for AI features)
  - Get a free key at: https://console.groq.com/keys

### Workflow

- **Name**: AI Terminal Native
- **Command**: `python main.py`
- **Output**: VNC (native desktop display)

## User Preferences

None specified yet.

## Notes

- The application works on both Windows and Linux
- Groq's free tier provides generous rate limits for personal use
- The terminal runs your actual system shell, so use caution with commands
- All AI-suggested commands require explicit confirmation before execution
