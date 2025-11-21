# Building Standalone Executables

This guide explains how to create standalone executable files for the AI Terminal Assistant that can run on Windows and Linux without requiring Python to be installed.

## Prerequisites

1. **Python 3.11+** installed on your system
2. **PyInstaller** - Install it with:
   ```bash
   pip install pyinstaller
   ```

## Quick Build (Automated)

The easiest way to build is using the provided build script:

```bash
python build.py
```

This will automatically:
- Detect your operating system
- Build the appropriate executable
- Place it in the `dist/` folder

## Manual Build Instructions

### For Windows (.exe)

1. Open Command Prompt or PowerShell
2. Navigate to the project directory
3. Run:
   ```bash
   pyinstaller --onefile --windowed --name=AITerminal main.py
   ```
4. The executable will be created at: `dist/AITerminal.exe`

### For Linux/Mac (binary)

1. Open Terminal
2. Navigate to the project directory
3. Run:
   ```bash
   pyinstaller --onefile --windowed --name=AITerminal main.py
   ```
4. The executable will be created at: `dist/AITerminal`
5. Make it executable:
   ```bash
   chmod +x dist/AITerminal
   ```

## Build Options Explained

- `--onefile`: Packages everything into a single executable file
- `--windowed`: No console window appears (GUI only)
- `--name=AITerminal`: Sets the output filename

### Advanced Options

For smaller file sizes or custom icons:

```bash
pyinstaller --onefile --windowed --name=AITerminal \
  --exclude-module matplotlib \
  --exclude-module numpy \
  main.py
```

To add a custom icon (if you have one):
```bash
# Windows
pyinstaller --onefile --windowed --icon=icon.ico --name=AITerminal main.py

# Linux/Mac
pyinstaller --onefile --windowed --icon=icon.icns --name=AITerminal main.py
```

## Running Your Executable

### Windows
Simply double-click `AITerminal.exe` or run from Command Prompt:
```
dist\AITerminal.exe
```

### Linux/Mac
Run from Terminal:
```bash
./dist/AITerminal
```

## Important Notes

### API Key Configuration

The executable needs the Groq API key to work. You can provide it in two ways:

1. **Environment Variable** (before running):
   ```bash
   # Windows (Command Prompt)
   set GROQ_API_KEY=your_key_here
   dist\AITerminal.exe
   
   # Windows (PowerShell)
   $env:GROQ_API_KEY="your_key_here"
   dist\AITerminal.exe
   
   # Linux/Mac
   export GROQ_API_KEY=your_key_here
   ./dist/AITerminal
   ```

2. **Settings Dialog** (after running):
   - Launch the application
   - Click the ⚙️ gear icon in the AI Assistant panel
   - Enter your API key
   - It will be saved permanently in `~/.ai_terminal_config.json`

### File Size

The executable will be 20-40 MB depending on your platform, as it includes:
- Python interpreter
- All required libraries (groq, ptyprocess, psutil, tkinter)
- Your application code

### Distribution

You can share the executable file with others, but:
- Windows .exe only works on Windows
- Linux binary only works on Linux (same architecture)
- Mac binary only works on macOS

For cross-platform distribution, you need to build on each target platform.

## Troubleshooting

### "Failed to execute script" error
- Make sure all dependencies are installed before building
- Try building with `--debug` flag to see detailed errors

### Executable won't start
- On Linux, ensure it has execute permissions: `chmod +x dist/AITerminal`
- Check if antivirus is blocking it (Windows)

### Large file size
- Use `--exclude-module` to remove unused libraries
- Consider using UPX compression: `pyinstaller --onefile --upx-dir=/path/to/upx main.py`

### Terminal doesn't work
- On Linux, ensure `ptyprocess` is properly bundled
- On Windows, ensure `pywinpty` is installed before building

## Clean Build

To clean build artifacts:

```bash
# Remove build files
rm -rf build/ dist/ *.spec

# Windows
rmdir /s /q build dist
del *.spec
```

Then rebuild using the instructions above.

## Getting Help

If you encounter issues:
1. Check PyInstaller documentation: https://pyinstaller.org/
2. Ensure all dependencies are installed: `pip install -r requirements.txt`
3. Try building with verbose output: `pyinstaller --onefile --windowed --name=AITerminal --log-level=DEBUG main.py`
