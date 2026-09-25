import { ParameterKey, SyncConfig, SyncLogEntry, SyncPayload, ConnectionStatus } from '../types';

const SYNC_CONFIG_KEY = 'dt_sync_config_v1';
const DEFAULT_CONFIG: SyncConfig = {
  host: window.location.hostname || '192.168.1.100',
  port: 8000,
  protocol: 'http',
  autoSync: true,
};

class SyncService {
  private config: SyncConfig;
  private status: ConnectionStatus = 'simulated';
  private logs: SyncLogEntry[] = [];
  private listeners: Array<(status: ConnectionStatus, logs: SyncLogEntry[]) => void> = [];
  
  private inFlight: Record<string, boolean> = {};
  private pendingQueue: Record<string, SyncPayload> = {};
  
  // Throttle investigation triggers to avoid spam (10 minutes)
  private lastInvestigationTime: number = 0;

  constructor() {
    this.config = this.loadConfig();
    // Force backend port 8000 and dynamic host for mobile Wi-Fi gateway
    this.config.host = window.location.hostname;
    this.config.port = 8000;
  }

  private loadConfig(): SyncConfig {
    return {
      host: window.location.hostname,
      port: 8000,
      protocol: 'http',
      autoSync: true,
    };
  }

  public saveConfig(newConfig: Partial<SyncConfig>): SyncConfig {
    this.config = { ...this.config, ...newConfig };
    this.config.host = window.location.hostname; // ensure always points to laptop
    this.config.port = 8000;
    try {
      localStorage.setItem(SYNC_CONFIG_KEY, JSON.stringify(this.config));
    } catch {}
    this.notify();
    return this.config;
  }

  public getConfig(): SyncConfig {
    return { ...this.config };
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  public getLogs(): SyncLogEntry[] {
    return [...this.logs];
  }

  public subscribe(fn: (status: ConnectionStatus, logs: SyncLogEntry[]) => void): () => void {
    this.listeners.push(fn);
    fn(this.status, this.logs);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn);
    };
  }

  private notify() {
    this.listeners.forEach((fn) => fn(this.status, this.logs));
  }

  private addLog(entry: Omit<SyncLogEntry, 'id' | 'timestamp'>) {
    const newEntry: SyncLogEntry = {
      ...entry,
      id: Math.random().toString(36).slice(2, 9),
      timestamp: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    };
    this.logs = [newEntry, ...this.logs.slice(0, 29)];
    this.notify();
  }

  public async pingListener(): Promise<{ success: boolean; message: string }> {
    this.status = 'connecting';
    this.notify();

    const url = `${this.config.protocol}://${this.config.host}:${this.config.port}/docs`;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const res = await fetch(url, {
        method: 'GET',
        signal: controller.signal,
        mode: 'cors',
      });
      clearTimeout(timeoutId);

      if (res.ok || res.status === 200) {
        this.status = 'connected';
        this.addLog({
          type: 'info',
          message: `Connected to FactoryBrain Backend at ${this.config.host}:${this.config.port}`,
          endpoint: '/docs',
        });
        this.notify();
        return { success: true, message: 'Connected to Backend' };
      }
      throw new Error('Invalid response');
    } catch (err: any) {
      this.status = 'error';
      this.addLog({
        type: 'error',
        message: err.name === 'AbortError' ? 'Connection timed out' : err.message || 'Connection failed',
        endpoint: '/docs',
      });
      this.notify();
      return { success: false, message: 'Connection failed' };
    }
  }

  public sendUpdate(machine_id: string, parameter: ParameterKey, value: number, forceImmediate = false) {
    if (!this.config.autoSync) return;

    const payload: SyncPayload = { machine_id, parameter, value, timestamp: Date.now() };
    const key = `${machine_id}_${parameter}`;

    if (forceImmediate || !this.inFlight[key]) {
      this.executeSend(key, payload);
    } else {
      this.pendingQueue[key] = payload;
    }
    
    this.checkThresholdsAndInvestigate(machine_id, parameter, value);
  }
  
  private async checkThresholdsAndInvestigate(machine_id: string, parameter: ParameterKey, value: number) {
      // Industrial operational limits - crossing triggers multi-agent investigation:
      const limits = {
          temperature: { min: 20, max: 75 },
          vibration: { min: 0.2, max: 3.8 },
          rpm: { min: 800, max: 2800 },
          pressure: { min: 2.0, max: 15.0 }
      };
      
      const paramLimits = limits[parameter as keyof typeof limits];
      if (!paramLimits) return;
      
      if (value <= paramLimits.min || value >= paramLimits.max) {
          const now = Date.now();
          // User: "if the Ollama model runs more than 10 minutes, automatically it should update. Don't use when the again case runs"
          // Debounce investigation trigger by 10 minutes (600,000 ms)
          if (now - this.lastInvestigationTime > 600000) {
              this.lastInvestigationTime = now;
              this.triggerOutsideInvestigation(machine_id, parameter, value);
          }
      }
  }
  
  private async triggerOutsideInvestigation(machine_id: string, parameter: string, value: number) {
      const url = `${this.config.protocol}://${this.config.host}:${this.config.port}/investigate/outside`;
      try {
          await fetch(url, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ machine_id, parameter, value }),
              mode: 'cors'
          });
          this.addLog({
            type: 'info',
            message: `TRIGGERED OUTSIDE INVESTIGATION for ${parameter}=${value}`,
            endpoint: '/investigate/outside'
          });
      } catch (err) {
          console.error("Failed to trigger outside investigation", err);
      }
  }

  private async executeSend(key: string, payload: SyncPayload) {
    this.inFlight[key] = true;
    const url = `${this.config.protocol}://${this.config.host}:${this.config.port}/parameters/batch`;
    
    // We transform the digital twin format into the backend format
    const backendPayload = {
      source: "digital-twin-mobile",
      changes: {
        [`machines.${payload.machine_id}.${payload.parameter}`]: payload.value
      }
    };

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(backendPayload),
        mode: 'cors', // Ensure CORS is handled by backend!
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      this.addLog({
        type: 'success',
        message: `Synced ${payload.parameter} = ${payload.value}`,
        endpoint: '/parameters/batch',
        payload: backendPayload,
      });
      if (this.status !== 'connected') {
        this.status = 'connected';
        this.notify();
      }
    } catch (err: any) {
      this.status = 'error';
      this.addLog({
        type: 'error',
        message: `Sync failed: ${err.message}`,
        endpoint: '/parameters/batch',
        payload: backendPayload,
      });
      this.notify();
    } finally {
      this.inFlight[key] = false;
      const pending = this.pendingQueue[key];
      if (pending) {
        delete this.pendingQueue[key];
        this.executeSend(key, pending);
      }
    }
  }
}

export const syncService = new SyncService();
