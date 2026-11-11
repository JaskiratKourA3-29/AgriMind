import subprocess
import xml.etree.ElementTree as ET
import sys
import os

ADB = r"C:\Users\asus\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def run_adb(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def get_ui():
    run_adb("shell uiautomator dump /data/local/tmp/uidump.xml")
    run_adb("pull /data/local/tmp/uidump.xml outputs/stage_b3_active_dump.xml")
    if not os.path.exists("outputs/stage_b3_active_dump.xml"):
        print("No dump file")
        return []
    root = ET.parse("outputs/stage_b3_active_dump.xml").getroot()
    elements = []
    for e in root.iter():
        text = e.attrib.get("text", "")
        desc = e.attrib.get("content-desc", "")
        bounds = e.attrib.get("bounds", "")
        if text or desc:
            elements.append((text, desc, bounds))
            print(f"TEXT: '{text}' | DESC: '{desc}' | BOUNDS: {bounds}")
    return elements

def take_screenshot(name):
    path = f"outputs/{name}"
    run_adb("shell screencap -p /data/local/tmp/screen.png")
    run_adb(f"pull /data/local/tmp/screen.png {path}")
    print(f"Screenshot saved to {path} ({os.path.getsize(path)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "shot":
        take_screenshot(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "tap":
        x, y = sys.argv[2], sys.argv[3]
        run_adb(f"shell input tap {x} {y}")
        print(f"Tapped {x}, {y}")
    else:
        get_ui()

