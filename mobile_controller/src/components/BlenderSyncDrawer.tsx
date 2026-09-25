import React, { useState } from 'react';
import { SyncConfig, SyncLogEntry, ConnectionStatus } from '../types';
import { BLENDER_LISTENER_PYTHON_SCRIPT } from '../utils/blenderScript';
import {
  X,
  Copy,
  Check,
  Download,
  Terminal,
  RefreshCw,
  Server,
  SlidersHorizontal,
  Wifi,
  Layers,
  ChevronRight,
} from 'lucide-react';

interface BlenderSyncDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  config: SyncConfig;
  status: ConnectionStatus;
  logs: SyncLogEntry[];
  onSaveConfig: (newConfig: Partial<SyncConfig>) => void;
  onPing: () => Promise<{ success: boolean; message: string }>;
}

export const BlenderSyncDrawer: React.FC<BlenderSyncDrawerProps> = ({
  isOpen,
  onClose,
  config,
  status,
  logs,
  onSaveConfig,
  onPing,
}) => {
  const [hostInput, setHostInput] = useState(config.host);
  const [portInput, setPortInput] = useState(config.port.toString());
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'network' | 'script' | 'logs'>('network');

  if (!isOpen) return null;

  const handleApplyConfig = (e: React.FormEvent) => {
    e.preventDefault();
    const port = parseInt(portInput, 10) || 8080;
    onSaveConfig({
      host: hostInput.trim(),
      port,
    });
    setPingResult('Config updated.');
  };

  const handlePing = async () => {
    setIsPinging(true);
    setPingResult('Pinging laptop...');
    const result = await onPing();
    setIsPinging(false);
    setPingResult(result.message);
  };

  const handleCopyScript = () => {
    navigator.clipboard.writeText(BLENDER_LISTENER_PYTHON_SCRIPT);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadScript = () => {
    const blob = new Blob([BLENDER_LISTENER_PYTHON_SCRIPT], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'blender_digital_twin_listener.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const quickPresets = ['192.168.1.100', '192.168.0.100', 'localhost', '10.0.0.100'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-neutral-900 border border-neutral-800 rounded-2xl max-h-[90vh] sm:max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-3.5 sm:p-4 bg-neutral-950 border-b border-neutral-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
              <SlidersHorizontal className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h2 className="font-mono text-xs sm:text-sm font-bold text-neutral-100 uppercase tracking-wider">
                Settings & Blender Sync
              </h2>
              <p className="text-[11px] text-neutral-400 font-mono">
                Local Wi-Fi link between mobile & laptop
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center text-neutral-400 hover:text-neutral-100 rounded-lg hover:bg-neutral-800/80 transition-colors"
            aria-label="Close settings dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-neutral-800 bg-neutral-950/60 px-3 pt-2 gap-1 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab('network')}
            className={`min-h-[40px] px-3 font-mono text-xs font-semibold tracking-wider uppercase border-b-2 transition-colors shrink-0 ${
              activeTab === 'network'
                ? 'border-amber-400 text-amber-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Connection
          </button>
          <button
            onClick={() => setActiveTab('script')}
            className={`min-h-[40px] px-3 font-mono text-xs font-semibold tracking-wider uppercase border-b-2 transition-colors shrink-0 ${
              activeTab === 'script'
                ? 'border-amber-400 text-amber-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Blender Script (.py)
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`min-h-[40px] px-3 font-mono text-xs font-semibold tracking-wider uppercase border-b-2 transition-colors shrink-0 ${
              activeTab === 'logs'
                ? 'border-amber-400 text-amber-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Packet Log ({logs.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-4 overflow-y-auto flex-1 space-y-4">
          {activeTab === 'network' && (
            <div className="space-y-4">
              {/* Link Status Card */}
              <div className="bg-neutral-950 border border-neutral-800 p-3 rounded-xl text-xs space-y-2">
                <div className="flex items-center justify-between text-neutral-300 font-mono">
                  <span className="flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-neutral-400" />
                    <span>Link Status:</span>
                  </span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-[11px] font-mono ${
                      status === 'connected'
                        ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800/60'
                        : 'text-amber-400 bg-amber-950/60 border border-amber-800/60'
                    }`}
                  >
                    {status === 'connected' ? '● BLENDER ONLINE' : '● SIMULATED MODE'}
                  </span>
                </div>
                <p className="text-neutral-400 text-[11px] leading-relaxed">
                  Enter your laptop's Wi-Fi IP address below. As you adjust sliders on your mobile device, parameter changes stream directly to your 3D model in Blender.
                </p>
              </div>

              {/* Network Configuration Form */}
              <form onSubmit={handleApplyConfig} className="space-y-3.5">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider">
                      Laptop Local IP Address
                    </label>
                    <span className="text-[10px] font-mono text-neutral-500">Port {portInput}</span>
                  </div>
                  <input
                    type="text"
                    value={hostInput}
                    onChange={(e) => setHostInput(e.target.value)}
                    placeholder="e.g. 192.168.1.100 or localhost"
                    className="w-full min-h-[44px] px-3.5 bg-neutral-950 border border-neutral-700 rounded-xl text-neutral-100 font-mono text-sm focus:outline-none focus:border-amber-400 transition-colors"
                  />
                  {/* Quick Presets */}
                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    <span className="text-[10px] font-mono text-neutral-500 mr-1">Presets:</span>
                    {quickPresets.map((ip) => (
                      <button
                        key={ip}
                        type="button"
                        onClick={() => setHostInput(ip)}
                        className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
                          hostInput === ip
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                            : 'bg-neutral-950 text-neutral-400 border-neutral-800 hover:border-neutral-700'
                        }`}
                      >
                        {ip}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-neutral-400 uppercase tracking-wider mb-1">
                    Listener Port
                  </label>
                  <input
                    type="number"
                    value={portInput}
                    onChange={(e) => setPortInput(e.target.value)}
                    placeholder="8080"
                    className="w-full min-h-[44px] px-3.5 bg-neutral-950 border border-neutral-700 rounded-xl text-neutral-100 font-mono text-sm focus:outline-none focus:border-amber-400 transition-colors"
                  />
                </div>

                <div className="flex gap-2.5 pt-1">
                  <button
                    type="submit"
                    className="flex-1 min-h-[44px] px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 font-mono text-xs font-semibold uppercase tracking-wider rounded-xl border border-neutral-700 active:scale-[0.98] transition-all"
                  >
                    Save Target
                  </button>
                  <button
                    type="button"
                    onClick={handlePing}
                    disabled={isPinging}
                    className="min-h-[44px] px-4 py-2.5 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-mono text-xs font-bold uppercase tracking-wider rounded-xl active:scale-[0.98] transition-all disabled:opacity-50 shadow-md shadow-amber-500/10"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isPinging ? 'animate-spin' : ''}`} />
                    <span>{isPinging ? 'Testing...' : 'Test Ping'}</span>
                  </button>
                </div>
              </form>

              {pingResult && (
                <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl text-[11px] font-mono text-neutral-300">
                  <span className="text-amber-400 font-bold">STATUS:</span> {pingResult}
                </div>
              )}

              {/* Quick Setup Instructions */}
              <div className="border border-neutral-800 rounded-xl p-3 bg-neutral-950/60 space-y-2">
                <span className="font-mono text-xs font-semibold text-neutral-200 block uppercase">
                  Quick 3-Step Setup
                </span>
                <ol className="text-xs text-neutral-400 space-y-1.5 list-decimal pl-4">
                  <li>Ensure your phone and laptop are on the same Wi-Fi.</li>
                  <li>In Blender, paste and run the companion script from the next tab.</li>
                  <li>Enter your laptop IP above and adjust any slider for live updates!</li>
                </ol>
              </div>
            </div>
          )}

          {activeTab === 'script' && (
            <div className="space-y-3.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-neutral-300 truncate">
                  blender_digital_twin_listener.py
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleCopyScript}
                    className="min-h-[40px] px-3 py-1.5 flex items-center gap-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-mono text-xs rounded-lg border border-neutral-700 active:scale-[0.98] transition-all"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    onClick={handleDownloadScript}
                    className="min-h-[40px] px-3 py-1.5 flex items-center gap-1.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-mono text-xs font-bold rounded-lg active:scale-[0.98] transition-all"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>
                </div>
              </div>

              <div className="p-3 bg-neutral-950 rounded-xl border border-neutral-800 text-xs text-neutral-400 space-y-2">
                <p className="font-mono text-amber-300 font-bold">Quick Setup in Blender:</p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Open Blender on your laptop.</li>
                  <li>Click the <strong>Scripting</strong> workspace tab at the top.</li>
                  <li>Click <strong>+ New</strong>, paste this script, and click <strong>Run Script</strong>.</li>
                  <li>In 3D Viewport, press <kbd className="px-1 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-neutral-200 font-mono text-[10px]">Z</kbd> and choose <strong>Material Preview</strong> or <strong>Rendered</strong>.</li>
                </ol>
                <div className="pt-2 border-t border-neutral-800 text-[11px] font-mono text-neutral-300 space-y-1">
                  <span className="text-amber-400 font-bold block">Live Visual Reactions:</span>
                  <div>🔥 <strong>Temperature</strong>: Material emission shifts from cool blue to glowing red/orange.</div>
                  <div>⚡ <strong>Vibration</strong>: High-frequency mechanical chassis shake proportional to amplitude.</div>
                  <div>🔄 <strong>RPM</strong>: Rotor assembly spins live at exact angular velocity.</div>
                  <div>🧭 <strong>Pressure</strong>: Gauge needle sweeps and pressure chamber expands/deforms.</div>
                </div>
              </div>

              <div className="relative">
                <pre className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl text-[10px] font-mono text-neutral-300 max-h-64 overflow-y-auto leading-relaxed select-all">
                  {BLENDER_LISTENER_PYTHON_SCRIPT}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-mono text-neutral-400 pb-1">
                <span>Recent Outgoing Transmissions</span>
                <span>Protocol: HTTP POST</span>
              </div>
              {logs.length === 0 ? (
                <div className="p-8 text-center text-xs font-mono text-neutral-500 border border-neutral-800/80 rounded-xl bg-neutral-950/50">
                  No packets transmitted yet. Adjust any slider to stream live data.
                </div>
              ) : (
                <div className="space-y-1.5 max-h-72 overflow-y-auto">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-2.5 bg-neutral-950 border border-neutral-800/90 rounded-lg text-[11px] font-mono flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-neutral-500">{log.timestamp}</span>
                        <span className="text-amber-400 truncate">{log.machine_id}</span>
                        <span className="text-neutral-300">[{log.parameter}]</span>
                        <span className="text-white font-bold">{log.value}</span>
                      </div>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-mono shrink-0 ${
                          log.success
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50'
                            : 'bg-neutral-800 text-neutral-400'
                        }`}
                      >
                        {log.success ? 'SENT' : 'LOCAL'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3.5 bg-neutral-950 border-t border-neutral-800 flex justify-end">
          <button
            onClick={onClose}
            className="min-h-[44px] px-5 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-mono text-xs font-semibold uppercase tracking-wider rounded-xl transition-colors"
          >
            Close Settings
          </button>
        </div>
      </div>
    </div>
  );
};
