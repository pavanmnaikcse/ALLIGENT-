import re

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/App.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Add pingListener to useEffect
old_effect = """  useEffect(() => {
    const unsubscribe = syncService.subscribe((status, logs) => {
      setConnectionStatus(status);
      setSyncLogs(logs);
    });
    return unsubscribe;
  }, []);"""

new_effect = """  useEffect(() => {
    const unsubscribe = syncService.subscribe((status, logs) => {
      setConnectionStatus(status);
      setSyncLogs(logs);
    });
    // Auto-connect on load
    syncService.pingListener();
    return unsubscribe;
  }, []);"""

text = text.replace(old_effect, new_effect)

with open("c:/Users/pn466/OneDrive/Documents/digital-twin-controller/src/App.tsx", "w", encoding="utf-8") as f:
    f.write(text)

print("done fixing auto connect")
