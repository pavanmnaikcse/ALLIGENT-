import re

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/services/syncService.ts", "r", encoding="utf-8") as f:
    text = f.read()

# Completely override loadConfig to ignore local storage and strictly enforce http / 8000
replacement = """  private loadConfig(): SyncConfig {
    return {
      host: window.location.hostname,
      port: 8000,
      protocol: 'http',
      autoSync: true,
    };
  }"""

text = re.sub(r'  private loadConfig\(\): SyncConfig \{.*?\n  \}', replacement, text, flags=re.DOTALL)

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/services/syncService.ts", "w", encoding="utf-8") as f:
    f.write(text)

print("done clearing cache")
