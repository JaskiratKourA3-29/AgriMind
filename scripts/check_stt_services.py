import subprocess
import os

adb = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")
out = subprocess.check_output([adb, 'shell', 'dumpsys', 'package'], text=True, errors='replace')

lines = out.splitlines()
for i, line in enumerate(lines):
    if 'android.speech.RecognitionService' in line:
        start = max(0, i - 5)
        end = min(len(lines), i + 10)
        print("--- MATCH ---")
        for j in range(start, end):
            print(lines[j])

