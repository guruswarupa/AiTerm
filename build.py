#!/usr/bin/env python3
"""
Build script for creating standalone executables for AI Terminal Assistant.
Supports Windows (.exe) and Linux/Mac (binary).

Requirements:
- PyInstaller: pip install pyinstaller

Usage:
    python build.py
"""

import os
import sys
import platform
import subprocess
import shutil

def main():
    print("=" * 60)
    print("AI Terminal Assistant - Build Script")
    print("=" * 60)
    
    os_name = platform.system()
    print(f"\nDetected OS: {os_name}")
    
    if not shutil.which('pyinstaller'):
        print("\n❌ Error: PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)
    
    print("\n📦 Building standalone executable...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=AITerminal',
        'main.py'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\n✅ Build successful!")
        print("\n📁 Output locations:")
        
        if os_name == 'Windows':
            exe_path = os.path.join('dist', 'AITerminal.exe')
            print(f"   Windows executable: {exe_path}")
        else:
            exe_path = os.path.join('dist', 'AITerminal')
            print(f"   Linux/Mac executable: {exe_path}")
            
            os.chmod(exe_path, 0o755)
            print("   (Made executable with chmod +x)")
        
        print(f"\nFile size: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        
        print("\n🚀 To run your executable:")
        if os_name == 'Windows':
            print(f"   {exe_path}")
        else:
            print(f"   ./{exe_path}")
            
        print("\n⚠️  Note: The executable needs GROQ_API_KEY environment variable")
        print("   Or you can set it in the Settings dialog when running the app")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
