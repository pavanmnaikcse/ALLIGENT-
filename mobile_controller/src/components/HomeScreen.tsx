import React, { useState } from 'react';
import { MachineSystem, ConnectionStatus } from '../types';
import {
  Plus,
  ChevronRight,
  Trash2,
  Gauge,
  Cpu,
  Layers,
  Flame,
  Bot,
  Scan,
  ArrowRightLeft,
  PackageCheck,
  Boxes,
  Database,
  Sliders,
} from 'lucide-react';

interface HomeScreenProps {
  machines: MachineSystem[];
  onSelectMachine: (machineId: string) => void;
  onAddMachine: (name: string, id: string, type: string) => void;
  onDeleteMachine: (machineId: string) => void;
  connectionStatus: ConnectionStatus;
  onOpenSyncDrawer: () => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  machines,
  onSelectMachine,
  onAddMachine,
  onDeleteMachine,
  connectionStatus,
  onOpenSyncDrawer,
}) => {
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newId, setNewId] = useState('');
  const [newType, setNewType] = useState('Silo & Feeder Conveyor');

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    const id = (newId.trim() || newName.toLowerCase().replace(/[^a-z0-9]/g, '_')).slice(0, 32);
    onAddMachine(newName.trim(), id, newType.trim());
    setNewName('');
    setNewId('');
    setIsAdding(false);
  };

  const getMachineIcon = (machine: MachineSystem) => {
    switch (machine.id) {
      case 'raw_material':
        return <Database className="w-4 h-4 text-sky-400" />;
      case 'processing_unit':
        return <Flame className="w-4 h-4 text-rose-400" />;
      case 'robot_pick_place':
        return <Bot className="w-4 h-4 text-amber-400" />;
      case 'ai_vision_inspection':
        return <Scan className="w-4 h-4 text-cyan-400" />;
      case 'automated_sorting':
        return <ArrowRightLeft className="w-4 h-4 text-indigo-400" />;
      case 'automated_packaging':
        return <PackageCheck className="w-4 h-4 text-emerald-400" />;
      case 'finished_goods':
        return <Boxes className="w-4 h-4 text-amber-300" />;
      default:
        return <Gauge className="w-4 h-4 text-amber-400" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 max-w-xl mx-auto w-full space-y-4">
      {/* System Status Banner */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 flex items-center justify-between">
        <div>
          <div className="font-mono text-xs font-bold text-neutral-200 uppercase tracking-wider">
            Manufacturing Line Overview
          </div>
          <div className="text-xs text-neutral-400 mt-0.5">
            {machines.length} Production Stages · All Live Synced to Blender
          </div>
        </div>
        <button
          onClick={onOpenSyncDrawer}
          className="min-h-[44px] px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded-lg text-xs font-mono font-semibold uppercase tracking-wider transition-colors flex items-center gap-1.5"
        >
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          <span>Sync Settings</span>
        </button>
      </div>

      {/* Machine Systems List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <span className="font-mono text-xs font-bold text-neutral-400 uppercase tracking-wider">
            Production Stages ({machines.length})
          </span>
          <button
            onClick={() => setIsAdding(true)}
            className="min-h-[44px] px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 rounded-lg text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-1.5 active:scale-[0.98] transition-transform shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>Add Machine</span>
          </button>
        </div>

        {machines.length === 0 ? (
          <div className="p-8 text-center bg-neutral-900 border border-neutral-800 rounded-xl space-y-3">
            <Layers className="w-8 h-8 text-neutral-500 mx-auto" />
            <div className="font-mono text-xs text-neutral-400">
              No machine systems active. Add a machine to begin remote control.
            </div>
            <button
              onClick={() => setIsAdding(true)}
              className="min-h-[44px] px-4 py-2 bg-amber-500 text-neutral-950 font-mono text-xs font-bold uppercase rounded-lg"
            >
              Add First Machine
            </button>
          </div>
        ) : (
          <div className="space-y-2.5">
            {machines.map((machine, index) => (
              <div
                key={machine.id}
                onClick={() => onSelectMachine(machine.id)}
                className="group w-full bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-neutral-700 rounded-xl p-4 text-left transition-all cursor-pointer relative overflow-hidden"
              >
                {/* Top Row: Machine Header */}
                <div className="flex items-center justify-between gap-3 mb-2.5">
                  <div className="flex items-center gap-2.5 truncate">
                    <div className="w-8 h-8 rounded-lg bg-neutral-800 border border-neutral-700 flex items-center justify-center shrink-0">
                      {getMachineIcon(machine)}
                    </div>
                    <div className="truncate">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-neutral-100 truncate group-hover:text-amber-300 transition-colors">
                          {machine.name}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700 shrink-0">
                          STAGE {machine.stageNumber || index + 1}
                        </span>
                      </div>
                      <div className="text-[11px] text-neutral-400 font-mono flex items-center gap-1.5 mt-0.5">
                        <span className="text-amber-400">{machine.code}</span>
                        <span aria-hidden="true">·</span>
                        <span className="truncate">{machine.type}</span>
                        <span aria-hidden="true">·</span>
                        <span className="text-neutral-500 truncate">ID: {machine.id}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete machine ${machine.name}?`)) {
                          onDeleteMachine(machine.id);
                        }
                      }}
                      className="min-h-[44px] min-w-[44px] flex items-center justify-center text-neutral-500 hover:text-rose-400 transition-colors"
                      title="Remove machine"
                      aria-label={`Remove ${machine.name}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="min-h-[44px] min-w-[28px] flex items-center justify-center text-neutral-500 group-hover:text-amber-400 transition-colors">
                      <ChevronRight className="w-5 h-5" />
                    </div>
                  </div>
                </div>

                {/* Bottom Row: 4 Current Parameter Readouts */}
                <div className="grid grid-cols-4 gap-2 pt-2.5 border-t border-neutral-800/80 text-[11px] font-mono">
                  <div className="bg-neutral-950/60 p-2 rounded border border-neutral-900">
                    <div className="text-neutral-500 text-[10px] uppercase">TEMP</div>
                    <div className="text-neutral-200 font-bold tabular-nums">
                      {machine.parameters.temperature}°C
                    </div>
                  </div>
                  <div className="bg-neutral-950/60 p-2 rounded border border-neutral-900">
                    <div className="text-neutral-500 text-[10px] uppercase">VIB</div>
                    <div className="text-neutral-200 font-bold tabular-nums">
                      {machine.parameters.vibration}
                    </div>
                  </div>
                  <div className="bg-neutral-950/60 p-2 rounded border border-neutral-900">
                    <div className="text-neutral-500 text-[10px] uppercase">RPM</div>
                    <div className="text-amber-400 font-bold tabular-nums">
                      {machine.parameters.rpm}
                    </div>
                  </div>
                  <div className="bg-neutral-950/60 p-2 rounded border border-neutral-900">
                    <div className="text-neutral-500 text-[10px] uppercase">PRESS</div>
                    <div className="text-neutral-200 font-bold tabular-nums">
                      {machine.parameters.pressure}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Machine Modal */}
      {isAdding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-neutral-900 border border-neutral-700 rounded-xl p-5 shadow-2xl space-y-4">
            <div className="font-mono text-xs font-bold text-neutral-100 uppercase tracking-wider">
              Register New Machine System
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-[11px] font-mono text-neutral-400 uppercase mb-1">
                  Machine Name
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Laser Marking Station"
                  className="w-full min-h-[44px] px-3 bg-neutral-950 border border-neutral-700 rounded-lg text-sm text-neutral-100 font-mono focus:border-amber-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-neutral-400 uppercase mb-1">
                  Blender Object ID / Name
                </label>
                <input
                  type="text"
                  value={newId}
                  onChange={(e) => setNewId(e.target.value)}
                  placeholder="e.g. laser_marker (auto-generated if empty)"
                  className="w-full min-h-[44px] px-3 bg-neutral-950 border border-neutral-700 rounded-lg text-sm text-neutral-100 font-mono focus:border-amber-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-neutral-400 uppercase mb-1">
                  System Type
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full min-h-[44px] px-3 bg-neutral-950 border border-neutral-700 rounded-lg text-sm text-neutral-100 font-mono focus:border-amber-400 focus:outline-none"
                >
                  <option value="Silo & Feeder Conveyor">Silo & Feeder Conveyor</option>
                  <option value="Thermal Reactor & Mill">Thermal Reactor & Mill</option>
                  <option value="6-Axis Articulated Arm">6-Axis Articulated Arm</option>
                  <option value="High-Speed Optical Scanner">High-Speed Optical Scanner</option>
                  <option value="Pneumatic Diverter Belt">Pneumatic Diverter Belt</option>
                  <option value="Form-Fill-Seal Packaging">Form-Fill-Seal Packaging</option>
                  <option value="Palletizer & Dispatch Buffer">Palletizer & Dispatch Buffer</option>
                  <option value="Centrifugal Motor">Centrifugal Motor</option>
                  <option value="Turbine Rotor">Turbine Rotor</option>
                  <option value="Hydraulic Press">Hydraulic Press</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  className="flex-1 min-h-[44px] px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-mono text-xs uppercase rounded-lg border border-neutral-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 min-h-[44px] px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-mono text-xs font-bold uppercase rounded-lg transition-transform active:scale-[0.98]"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
