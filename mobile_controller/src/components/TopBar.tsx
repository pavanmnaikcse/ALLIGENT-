import React from 'react';
import { ConnectionStatus } from '../types';
import { Wifi, WifiOff, Terminal, SlidersHorizontal, Layers } from 'lucide-react';

interface TopBarProps {
  currentView: 'home' | 'control';
  machineName?: string;
  machineCode?: string;
  connectionStatus: ConnectionStatus;
  onOpenSyncDrawer: () => void;
  onNavigateHome: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentView,
  machineName,
  machineCode,
  connectionStatus,
  onOpenSyncDrawer,
  onNavigateHome,
}) => {
  const getStatusDisplay = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          label: 'LINKED',
          dotClass: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]',
          textClass: 'text-emerald-400',
        };
      case 'connecting':
        return {
          label: 'SYNCING',
          dotClass: 'bg-amber-400 animate-pulse',
          textClass: 'text-amber-400',
        };
      case 'simulated':
      default:
        return {
          label: 'SIMULATED',
          dotClass: 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]',
          textClass: 'text-amber-300',
        };
      case 'error':
        return {
          label: 'OFFLINE',
          dotClass: 'bg-rose-500',
          textClass: 'text-rose-400',
        };
    }
  };

  const status = getStatusDisplay();

  return (
    <header className="sticky top-0 z-30 w-full bg-neutral-950/95 backdrop-blur-md border-b border-neutral-800/80 px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between gap-2 pt-[max(0.625rem,env(safe-area-inset-top))]">
      {/* Zone 1: Navigation & Brand Wordmark */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {currentView === 'control' && (
          <button
            onClick={onNavigateHome}
            className="min-h-[44px] min-w-[36px] -ml-1 sm:ml-0 flex items-center justify-center text-neutral-400 hover:text-neutral-100 transition-colors shrink-0"
            title="Return to systems list"
            aria-label="Back to machine systems"
          >
            <span className="font-mono text-lg font-bold">←</span>
          </button>
        )}
        <div className="flex flex-col min-w-0">
          <span className="font-mono text-xs sm:text-sm font-bold tracking-wider text-neutral-100 uppercase truncate">
            Digital Twin Controller
          </span>
          {currentView === 'control' && machineName && (
            <div className="flex items-center gap-1.5 text-[11px] text-neutral-400 truncate">
              <span className="font-mono text-amber-400 font-semibold">{machineCode || 'SYS'}</span>
              <span aria-hidden="true">·</span>
              <span className="truncate font-medium text-neutral-300">{machineName}</span>
            </div>
          )}
        </div>
      </div>

      {/* Zone 2: Settings & Connection Status Button */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={onOpenSyncDrawer}
          className="min-h-[44px] px-2.5 sm:px-3 py-1.5 flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded-lg hover:border-neutral-700 active:scale-[0.98] transition-all"
          title="Open Settings & Blender Sync"
          aria-label="Settings and Blender Sync"
        >
          <span className={`w-2 h-2 rounded-full shrink-0 ${status.dotClass}`} />
          <span className={`font-mono text-[11px] font-semibold tracking-wider ${status.textClass} whitespace-nowrap`}>
            {status.label}
          </span>
          <div className="flex items-center gap-1 text-neutral-300 font-mono text-[11px] font-medium pl-1.5 border-l border-neutral-800">
            <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="hidden xs:inline sm:inline">Settings</span>
          </div>
        </button>
      </div>
    </header>
  );
};
