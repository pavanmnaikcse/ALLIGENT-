import React, { useState } from 'react';
import { MachineSystem, ParameterKey, PARAMETER_CONFIGS, ConnectionStatus } from '../types';
import { SimulatedTwinVisualizer } from './SimulatedTwinVisualizer';
import { ConnectNowModal } from './ConnectNowModal';
import {
  Flame,
  Activity,
  RotateCw,
  Gauge,
  Sliders,
  Eye,
  EyeOff,
  RotateCcw,
  Zap,
} from 'lucide-react';

interface MachineControlScreenProps {
  machine: MachineSystem;
  onUpdateParameter: (machineId: string, param: ParameterKey, value: number) => void;
  onResetNominal: (machineId: string) => void;
  connectionStatus: ConnectionStatus;
  onOpenSyncDrawer: () => void;
}

export const MachineControlScreen: React.FC<MachineControlScreenProps> = ({
  machine,
  onUpdateParameter,
  onResetNominal,
  connectionStatus,
  onOpenSyncDrawer,
}) => {
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showVisualizer, setShowVisualizer] = useState(true);

  const getParamIcon = (key: ParameterKey) => {
    switch (key) {
      case 'temperature':
        return <Flame className="w-4 h-4 text-amber-400" />;
      case 'vibration':
        return <Activity className="w-4 h-4 text-cyan-400" />;
      case 'rpm':
        return <RotateCw className="w-4 h-4 text-emerald-400" />;
      case 'pressure':
        return <Gauge className="w-4 h-4 text-sky-400" />;
    }
  };

  const parametersList: ParameterKey[] = ['temperature', 'vibration', 'rpm', 'pressure'];

  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          text: 'CONNECTED TO BLENDER',
          color: 'text-emerald-400 border-emerald-800/80 bg-emerald-950/50',
          dot: 'bg-emerald-400',
        };
      case 'connecting':
        return {
          text: 'CONNECTING...',
          color: 'text-amber-300 border-amber-800/80 bg-amber-950/50',
          dot: 'bg-amber-400 animate-pulse',
        };
      case 'simulated':
      default:
        return {
          text: 'SIMULATED MODE',
          color: 'text-amber-400 border-amber-800/80 bg-amber-950/40',
          dot: 'bg-amber-400',
        };
      case 'error':
        return {
          text: 'NOT CONNECTED',
          color: 'text-neutral-400 border-neutral-800 bg-neutral-900',
          dot: 'bg-neutral-500',
        };
    }
  };

  const statusBadge = getStatusBadge();

  return (
    <div className="flex-1 flex flex-col p-4 max-w-xl mx-auto w-full space-y-4 pb-24">
      {/* Machine Identity & Status Strip */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 flex items-center justify-between">
        <div className="truncate pr-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-amber-400 font-bold">{machine.code}</span>
            <span className="font-mono text-sm font-bold text-neutral-100 truncate">{machine.name}</span>
            {machine.stageNumber && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700 shrink-0">
                STAGE {machine.stageNumber}
              </span>
            )}
          </div>
          <div className="text-[11px] font-mono text-neutral-400 mt-0.5 truncate flex items-center gap-1.5">
            <span className="text-neutral-300">{machine.type}</span>
            <span aria-hidden="true">·</span>
            <span>Target: <span className="text-neutral-200">{machine.id}</span></span>
          </div>
        </div>

        {/* Live Status Indicator & Settings Trigger */}
        <button
          onClick={onOpenSyncDrawer}
          className={`min-h-[38px] flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono font-semibold hover:opacity-90 active:scale-[0.98] transition-all shrink-0 ${statusBadge.color}`}
          title="Click to view Blender sync settings & diagnostics"
          aria-label="Blender sync settings"
        >
          <span className={`w-2 h-2 rounded-full shrink-0 ${statusBadge.dot}`} />
          <span className="truncate">{statusBadge.text}</span>
        </button>
      </div>

      {/* Simulated Stand-In 2D Twin Viewport */}
      {showVisualizer && (
        <SimulatedTwinVisualizer
          parameters={machine.parameters}
          machineName={machine.name}
          machineId={machine.id}
        />
      )}

      {/* Control Panel Header with View Toggle & Reset */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-neutral-400" />
          <span className="font-mono text-xs font-bold text-neutral-300 uppercase tracking-wider">
            Parameter Controls
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowVisualizer(!showVisualizer)}
            className="min-h-[38px] px-2.5 py-1 text-xs font-mono text-neutral-400 hover:text-neutral-200 bg-neutral-900 border border-neutral-800 rounded-lg flex items-center gap-1.5 transition-colors"
            title="Toggle digital twin schematic"
          >
            {showVisualizer ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{showVisualizer ? 'Hide Twin' : 'Show Twin'}</span>
          </button>
          <button
            onClick={() => onResetNominal(machine.id)}
            className="min-h-[38px] px-2.5 py-1 text-xs font-mono text-neutral-400 hover:text-neutral-200 bg-neutral-900 border border-neutral-800 rounded-lg flex items-center gap-1.5 transition-colors"
            title="Reset parameters to nominal factory values"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* The 4 Tactical Sliders / Direct Numeric Inputs */}
      <div className="space-y-3">
        {parametersList.map((paramKey) => {
          const config = PARAMETER_CONFIGS[paramKey];
          const currentValue = machine.parameters[paramKey];

          const handleRangeChange = (e: React.ChangeEvent<HTMLInputElement> | React.FormEvent<HTMLInputElement>) => {
            const target = e.currentTarget as HTMLInputElement;
            const val = parseFloat(target.value);
            onUpdateParameter(machine.id, paramKey, Number.isNaN(val) ? config.defaultValue : val);
          };

          const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const val = parseFloat(e.target.value);
            if (!Number.isNaN(val)) {
              const clamped = Math.min(Math.max(val, config.min), config.max);
              onUpdateParameter(machine.id, paramKey, clamped);
            }
          };

          const handleStep = (direction: 1 | -1) => {
            const next = currentValue + direction * config.step;
            const clamped = Math.min(Math.max(Number(next.toFixed(2)), config.min), config.max);
            onUpdateParameter(machine.id, paramKey, clamped);
          };

          return (
            <div
              key={paramKey}
              className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 space-y-3 hover:border-neutral-700 transition-colors"
            >
              {/* Header: Label + Unit + Numeric Input */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded bg-neutral-800 flex items-center justify-center">
                    {getParamIcon(paramKey)}
                  </div>
                  <div>
                    <div className="font-mono text-xs font-bold text-neutral-200 uppercase tracking-wider">
                      {config.label}
                    </div>
                    <div className="text-[10px] font-mono text-neutral-500">
                      Driver: {config.blenderDriver}
                    </div>
                  </div>
                </div>

                {/* Direct Numeric Input with stepper buttons */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleStep(-1)}
                    disabled={currentValue <= config.min}
                    className="w-8 h-8 rounded bg-neutral-800 hover:bg-neutral-700 disabled:opacity-30 text-neutral-200 font-mono font-bold text-sm flex items-center justify-center border border-neutral-700 active:scale-95 transition-all"
                    aria-label={`Decrease ${config.label}`}
                  >
                    -
                  </button>

                  <div className="flex items-center bg-neutral-950 border border-neutral-700 rounded px-2 h-8">
                    <input
                      type="number"
                      step={config.step}
                      min={config.min}
                      max={config.max}
                      value={currentValue}
                      onChange={handleNumberChange}
                      className="w-16 bg-transparent text-right font-mono text-sm font-bold text-neutral-100 tabular-nums focus:outline-none"
                    />
                    <span className="ml-1 text-[11px] font-mono text-neutral-400 select-none">
                      {config.unit}
                    </span>
                  </div>

                  <button
                    onClick={() => handleStep(1)}
                    disabled={currentValue >= config.max}
                    className="w-8 h-8 rounded bg-neutral-800 hover:bg-neutral-700 disabled:opacity-30 text-neutral-200 font-mono font-bold text-sm flex items-center justify-center border border-neutral-700 active:scale-95 transition-all"
                    aria-label={`Increase ${config.label}`}
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Slider Element */}
              <div className="pt-1.5 pb-0.5">
                <input
                  type="range"
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  value={currentValue}
                  onInput={handleRangeChange}
                  onChange={handleRangeChange}
                  className="w-full h-2.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer accent-amber-500 hover:accent-amber-400 transition-all focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  aria-label={`${config.label} slider`}
                />
              </div>

              {/* Min and Max Range Scale */}
              <div className="flex items-center justify-between text-[10px] font-mono text-neutral-500 px-0.5">
                <span>{config.min} {config.unit}</span>
                <span className="text-neutral-400 font-medium">
                  Current: {currentValue} {config.unit}
                </span>
                <span>{config.max} {config.unit}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Sticky Bottom Action Zone: "Connect Now" button */}
      <div className="fixed bottom-0 left-0 right-0 p-3.5 bg-gradient-to-t from-neutral-950 via-neutral-950/95 to-transparent border-t border-neutral-800/80 backdrop-blur-md z-20 pb-[max(0.875rem,env(safe-area-inset-bottom))]">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <button
            onClick={() => { import('../services/syncService').then(m => m.syncService.pingListener()); }}
            className="flex-1 min-h-[48px] px-4 py-2.5 bg-neutral-900 hover:bg-neutral-850 text-neutral-100 font-mono text-xs font-bold uppercase tracking-wider rounded-xl border border-amber-500/50 hover:border-amber-400 active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg shadow-black/40"
          >
            <Zap className="w-4 h-4 text-amber-400" />
            <span>Connect Now</span>
            <span className="text-[10px] font-normal text-amber-400/90 font-mono lowercase">
              (simulation active)
            </span>
          </button>
        </div>
      </div>

      {/* Connect Now Hardware Modal */}
      <ConnectNowModal
        isOpen={showConnectModal}
        onClose={() => setShowConnectModal(false)}
        machineName={machine.name}
        machineId={machine.id}
      />
    </div>
  );
};
