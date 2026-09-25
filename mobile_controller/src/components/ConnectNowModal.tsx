import React from 'react';
import { X, Cpu, CheckCircle2 } from 'lucide-react';

interface ConnectNowModalProps {
  isOpen: boolean;
  onClose: () => void;
  machineName: string;
  machineId: string;
}

export const ConnectNowModal: React.FC<ConnectNowModalProps> = ({
  isOpen,
  onClose,
  machineName,
  machineId,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-sm bg-neutral-900 border border-neutral-700 rounded-xl p-5 shadow-2xl text-left"
        role="dialog"
        aria-modal="true"
        aria-labelledby="connect-dialog-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-amber-400" />
            <span id="connect-dialog-title" className="font-mono text-xs font-bold tracking-wider text-neutral-200 uppercase">
              Physical Machine Link
            </span>
          </div>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center text-neutral-400 hover:text-neutral-100 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message body */}
        <div className="py-4 space-y-3">
          <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-lg">
            <p className="font-mono text-xs font-semibold text-amber-400">
              Not available yet — using simulation mode.
            </p>
          </div>

          <p className="text-xs text-neutral-400 leading-relaxed">
            Hardware fieldbus interface (RS-485 / Modbus RTU / MQTT / CAN bus) for <span className="text-neutral-200 font-mono">{machineName}</span> ({machineId}) is scheduled for hardware phase.
          </p>

          <p className="text-xs text-neutral-400 leading-relaxed">
            Currently, this application functions as the <strong className="text-neutral-200">simulated stand-in</strong>. All parameter changes stream directly to your 3D digital twin inside Blender on your laptop in real time.
          </p>

          <div className="pt-2 flex items-center gap-2 text-[11px] font-mono text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            <span>Simulation engine active & streaming to Blender</span>
          </div>
        </div>

        {/* Action button */}
        <div className="pt-2">
          <button
            onClick={onClose}
            className="w-full min-h-[44px] px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 text-xs font-mono font-semibold tracking-wider uppercase rounded-lg border border-neutral-700 active:scale-[0.98] transition-all"
          >
            Acknowledge & Return
          </button>
        </div>
      </div>
    </div>
  );
};
