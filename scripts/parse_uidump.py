import xml.etree.ElementTree as ET

tree = ET.parse('docs/uidump.xml')
root = tree.getroot()
for n in root.iter():
    desc = n.attrib.get('content-desc', '')
    text = n.attrib.get('text', '')
    bounds = n.attrib.get('bounds', '')
    if desc or text:
        try:
            print(f"{desc.encode('ascii', 'replace').decode()} | {text.encode('ascii', 'replace').decode()} | {bounds}")
        except Exception:
            pass

