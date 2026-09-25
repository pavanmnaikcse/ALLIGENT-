export type ParameterKey = 'temperature' | 'vibration' | 'rpm' | 'pressure';

export interface ParameterConfig {
  key: ParameterKey;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  description: string;
  blenderDriver: string;
}

export interface MachineParameters {
  temperature: number; // 0 - 150 °C
  vibration: number;   // 0.0 - 10.0 mm/s
  rpm: number;         // 0 - 6000 RPM
  pressure: number;    // 0.0 - 50.0 bar
}

export interface MachineSystem {
  id: string; // e.g. "raw_material"
  name: string; // e.g. "Raw Material"
  code: string; // short tactical ID e.g. "RM-01"
  type: string; // e.g. "Silo & Feeder Conveyor"
  stageNumber?: number; // 1 to 7 sequence in manufacturing line
  parameters: MachineParameters;
  createdAt: number;
  lastUpdated: number;
}

export type ConnectionStatus = 'simulated' | 'connected' | 'error' | 'connecting';

export interface SyncConfig {
  host: string;
  port: number;
  protocol: 'http' | 'ws';
  autoSync: boolean;
}

export interface SyncPayload {
  machine_id: string;
  parameter: ParameterKey;
  value: number;
  timestamp?: number;
}

export interface SyncLogEntry {
  id: string;
  timestamp: string;
  machine_id: string;
  parameter: ParameterKey;
  value: number;
  success: boolean;
  statusText?: string;
}

export const PARAMETER_CONFIGS: Record<ParameterKey, ParameterConfig> = {
  temperature: {
    key: 'temperature',
    label: 'Temperature',
    unit: '°C',
    min: 0,
    max: 150,
    step: 1,
    defaultValue: 45,
    description: 'Thermal core value. In Blender: drives material emission color & heat haze shader.',
    blenderDriver: 'obj["temperature"] -> Emission Shader Strength/Color',
  },
  vibration: {
    key: 'vibration',
    label: 'Vibration',
    unit: 'mm/s',
    min: 0.0,
    max: 10.0,
    step: 0.1,
    defaultValue: 1.2,
    description: 'Dynamic oscillation amplitude. In Blender: drives procedural location noise micro-jitter.',
    blenderDriver: 'obj["vibration"] -> Location Noise Displace / Jitter',
  },
  rpm: {
    key: 'rpm',
    label: 'RPM',
    unit: 'RPM',
    min: 0,
    max: 6000,
    step: 50,
    defaultValue: 1450,
    description: 'Rotation speed. In Blender: drives continuous Z-axis angular velocity.',
    blenderDriver: 'obj["rpm"] -> Continuous Z Rotation (deg/frame)',
  },
  pressure: {
    key: 'pressure',
    label: 'Pressure',
    unit: 'bar',
    min: 0.0,
    max: 50.0,
    step: 0.5,
    defaultValue: 12.5,
    description: 'Chamber pressure. In Blender: drives gauge needle rotation or hydraulic cylinder scale.',
    blenderDriver: 'obj["pressure"] -> Gauge Needle / Piston Z-Scale',
  },
};
