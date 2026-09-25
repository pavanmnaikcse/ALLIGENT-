import React, { useState, useEffect } from 'react';
import { MachineSystem, ParameterKey, ConnectionStatus, SyncLogEntry, PARAMETER_CONFIGS } from './types';
import { syncService } from './services/syncService';
import { TopBar } from './components/TopBar';
import { HomeScreen } from './components/HomeScreen';
import { MachineControlScreen } from './components/MachineControlScreen';
import { BlenderSyncDrawer } from './components/BlenderSyncDrawer';

const MACHINES_STORAGE_KEY = 'dt_machines_fleet_v2';

const INITIAL_MACHINES: MachineSystem[] = [
  {
    id: 'raw_material',
    name: 'Raw Material',
    code: 'RM-01',
    type: 'Silo & Feeder Conveyor',
    stageNumber: 1,
    parameters: {
      temperature: 24,
      vibration: 1.1,
      rpm: 650,
      pressure: 4.5,
    },
    createdAt: Date.now() - 7 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'processing_unit',
    name: 'Processing Unit',
    code: 'PU-02',
    type: 'Thermal Reactor & Mill',
    stageNumber: 2,
    parameters: {
      temperature: 82,
      vibration: 2.8,
      rpm: 2800,
      pressure: 28.0,
    },
    createdAt: Date.now() - 6 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'robot_pick_place',
    name: 'Robot Pick and Place',
    code: 'RP-03',
    type: '6-Axis Articulated Arm',
    stageNumber: 3,
    parameters: {
      temperature: 42,
      vibration: 1.4,
      rpm: 1800,
      pressure: 6.2,
    },
    createdAt: Date.now() - 5 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'ai_vision_inspection',
    name: 'AI Vision Inspection',
    code: 'VI-04',
    type: 'High-Speed Optical Scanner',
    stageNumber: 4,
    parameters: {
      temperature: 36,
      vibration: 0.4,
      rpm: 1200,
      pressure: 3.0,
    },
    createdAt: Date.now() - 4 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'automated_sorting',
    name: 'Automated Sorting',
    code: 'AS-05',
    type: 'Pneumatic Diverter Belt',
    stageNumber: 5,
    parameters: {
      temperature: 38,
      vibration: 1.9,
      rpm: 1650,
      pressure: 7.5,
    },
    createdAt: Date.now() - 3 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'automated_packaging',
    name: 'Automated Packaging',
    code: 'AP-06',
    type: 'Form-Fill-Seal Packaging',
    stageNumber: 6,
    parameters: {
      temperature: 110,
      vibration: 2.2,
      rpm: 2100,
      pressure: 15.0,
    },
    createdAt: Date.now() - 2 * 3600000,
    lastUpdated: Date.now(),
  },
  {
    id: 'finished_goods',
    name: 'Finished Goods',
    code: 'FG-07',
    type: 'Palletizer & Dispatch Buffer',
    stageNumber: 7,
    parameters: {
      temperature: 26,
      vibration: 0.6,
      rpm: 850,
      pressure: 5.5,
    },
    createdAt: Date.now() - 1 * 3600000,
    lastUpdated: Date.now(),
  },
];

export default function App() {
  const [machines, setMachines] = useState<MachineSystem[]>(() => {
    try {
      const saved = localStorage.getItem(MACHINES_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && parsed.some((m: MachineSystem) => m.id === 'raw_material')) {
          return parsed;
        }
      }
    } catch {
      // Fallback
    }
    return INITIAL_MACHINES;
  });

  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('simulated');
  const [syncLogs, setSyncLogs] = useState<SyncLogEntry[]>([]);
  const [isSyncDrawerOpen, setIsSyncDrawerOpen] = useState(false);

  // Sync service subscription
  useEffect(() => {
    const unsubscribe = syncService.subscribe((status, logs) => {
      setConnectionStatus(status);
      setSyncLogs(logs);
    });
    // Auto-connect on load
    syncService.pingListener();
    return unsubscribe;
  }, []);

  // Save machines to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(MACHINES_STORAGE_KEY, JSON.stringify(machines));
    } catch {
      // Ignore
    }
  }, [machines]);

  const selectedMachine = machines.find((m) => m.id === selectedMachineId) || null;

  // Parameter change handler
  const handleUpdateParameter = (machineId: string, param: ParameterKey, value: number) => {
    setMachines((prev) =>
      prev.map((m) => {
        if (m.id === machineId) {
          return {
            ...m,
            parameters: {
              ...m.parameters,
              [param]: value,
            },
            lastUpdated: Date.now(),
          };
        }
        return m;
      })
    );

    // Stream live to Blender listener via local network
    syncService.sendUpdate(machineId, param, value);
  };

  // Reset to nominal values
  const handleResetNominal = (machineId: string) => {
    const nominals = {
      temperature: PARAMETER_CONFIGS.temperature.defaultValue,
      vibration: PARAMETER_CONFIGS.vibration.defaultValue,
      rpm: PARAMETER_CONFIGS.rpm.defaultValue,
      pressure: PARAMETER_CONFIGS.pressure.defaultValue,
    };

    setMachines((prev) =>
      prev.map((m) => {
        if (m.id === machineId) {
          return {
            ...m,
            parameters: nominals,
            lastUpdated: Date.now(),
          };
        }
        return m;
      })
    );

    // Send reset values to Blender
    (['temperature', 'vibration', 'rpm', 'pressure'] as ParameterKey[]).forEach((param) => {
      syncService.sendUpdate(machineId, param, nominals[param], true);
    });
  };

  // Add new machine system
  const handleAddMachine = (name: string, id: string, type: string) => {
    const count = machines.length + 1;
    const code = `SYS-${count.toString().padStart(2, '0')}`;
    const newMachine: MachineSystem = {
      id,
      name,
      code,
      type,
      parameters: {
        temperature: PARAMETER_CONFIGS.temperature.defaultValue,
        vibration: PARAMETER_CONFIGS.vibration.defaultValue,
        rpm: PARAMETER_CONFIGS.rpm.defaultValue,
        pressure: PARAMETER_CONFIGS.pressure.defaultValue,
      },
      createdAt: Date.now(),
      lastUpdated: Date.now(),
    };

    setMachines((prev) => [...prev, newMachine]);
    setSelectedMachineId(id);
  };

  // Delete machine system
  const handleDeleteMachine = (machineId: string) => {
    setMachines((prev) => {
      const filtered = prev.filter((m) => m.id !== machineId);
      if (selectedMachineId === machineId) {
        setSelectedMachineId(filtered[0]?.id || null);
      }
      return filtered;
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-neutral-950 text-neutral-100 selection:bg-amber-500/20">
      {/* Universal Industrial Top Bar */}
      <TopBar
        currentView={selectedMachineId ? 'control' : 'home'}
        machineName={selectedMachine?.name}
        machineCode={selectedMachine?.code}
        connectionStatus={connectionStatus}
        onOpenSyncDrawer={() => setIsSyncDrawerOpen(true)}
        onNavigateHome={() => setSelectedMachineId(null)}
      />

      {/* Main View Area */}
      <main className="flex-1 flex flex-col">
        {selectedMachineId && selectedMachine ? (
          <MachineControlScreen
            machine={selectedMachine}
            onUpdateParameter={handleUpdateParameter}
            onResetNominal={handleResetNominal}
            connectionStatus={connectionStatus}
            onOpenSyncDrawer={() => setIsSyncDrawerOpen(true)}
          />
        ) : (
          <HomeScreen
            machines={machines}
            onSelectMachine={(id) => setSelectedMachineId(id)}
            onAddMachine={handleAddMachine}
            onDeleteMachine={handleDeleteMachine}
            connectionStatus={connectionStatus}
            onOpenSyncDrawer={() => setIsSyncDrawerOpen(true)}
          />
        )}
      </main>

      {/* Blender Sync Configuration & Python Script Drawer */}
      <BlenderSyncDrawer
        isOpen={isSyncDrawerOpen}
        onClose={() => setIsSyncDrawerOpen(false)}
        config={syncService.getConfig()}
        status={connectionStatus}
        logs={syncLogs}
        onSaveConfig={(newConfig) => syncService.saveConfig(newConfig)}
        onPing={() => syncService.pingListener()}
      />
    </div>
  );
}
