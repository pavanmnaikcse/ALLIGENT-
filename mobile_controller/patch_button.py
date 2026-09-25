import re

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/components/MachineControlScreen.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Find the onClick for the button that shows the modal
old_click = "onClick={() => setShowConnectModal(true)}"
new_click = "onClick={() => { import('../services/syncService').then(m => m.syncService.pingListener()); }}"

text = text.replace(old_click, new_click)

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/components/MachineControlScreen.tsx", "w", encoding="utf-8") as f:
    f.write(text)

print("done fixing connect button")
