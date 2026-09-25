with open('src/services/syncService.ts', 'r', encoding='utf-8') as f:
    code = f.read()

old_limits = '''      // Hardcoded thresholds for demo:
      const limits = {
          temperature: { min: 5, max: 130 },
          vibration: { min: 0.1, max: 8.5 },
          rpm: { min: 100, max: 5500 },
          pressure: { min: 1.0, max: 45.0 }
      };'''

new_limits = '''      // Industrial operational limits - crossing triggers multi-agent investigation:
      const limits = {
          temperature: { min: 20, max: 75 },
          vibration: { min: 0.2, max: 3.8 },
          rpm: { min: 800, max: 2800 },
          pressure: { min: 2.0, max: 15.0 }
      };'''

if old_limits in code:
    code = code.replace(old_limits, new_limits, 1)
    with open('src/services/syncService.ts', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Updated syncService.ts limits")
else:
    print("old_limits not found in syncService.ts")
