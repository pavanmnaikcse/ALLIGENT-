import React, { useEffect, useRef } from 'react';
import { MachineParameters } from '../types';

interface SimulatedTwinVisualizerProps {
  parameters: MachineParameters;
  machineName: string;
  machineId: string;
}

export const SimulatedTwinVisualizer: React.FC<SimulatedTwinVisualizerProps> = ({
  parameters,
  machineName,
  machineId,
}) => {
  const { temperature, vibration, rpm, pressure } = parameters;
  const rotorRef = useRef<SVGGElement | null>(null);
  const secondaryRotorRef = useRef<SVGGElement | null>(null);
  const angleRef = useRef(0);
  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef(performance.now());

  // Continuous animation loop for RPM-driven rotating assembly
  useEffect(() => {
    const tick = (now: number) => {
      const dt = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;

      if (rpm > 0) {
        const degPerSec = (rpm / 60) * 360;
        angleRef.current = (angleRef.current + degPerSec * dt) % 360;

        if (rotorRef.current) {
          rotorRef.current.setAttribute('transform', `rotate(${angleRef.current} 120 85)`);
        }
        if (secondaryRotorRef.current) {
          secondaryRotorRef.current.setAttribute('transform', `rotate(${-angleRef.current * 1.2} 120 85)`);
        }
      }

      animFrameRef.current = requestAnimationFrame(tick);
    };

    lastTimeRef.current = performance.now();
    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [rpm]);

  // Color calculation for Temperature (0C - 150C)
  const normTemp = Math.min(Math.max((temperature - 20) / 100, 0), 1);
  let coreGlowColor = '#38bdf8'; // cool cyan
  let coreFillColor = '#0369a1';
  let tempLabel = 'NORMAL';

  if (normTemp > 0.65) {
    coreGlowColor = '#ef4444'; // hot red
    coreFillColor = '#991b1b';
    tempLabel = 'HIGH HEAT';
  } else if (normTemp > 0.35) {
    coreGlowColor = '#f59e0b'; // warm amber
    coreFillColor = '#b45309';
    tempLabel = 'ELEVATED';
  }

  // Pressure angle: 0 bar = -120deg, 50 bar = +120deg
  const pressureAngle = -120 + (Math.min(pressure, 50) / 50) * 240;

  // Vibration shake amplitude (0 - 10 mm/s)
  const vibAmplitude = Math.min(vibration, 10);
  const isVibrating = vibAmplitude > 0.15;

  // Render machine-specific schematic inside SVG
  const renderMachineSchematic = () => {
    switch (machineId) {
      case 'raw_material':
        // Conical silo hopper + rotating feed auger screw
        return (
          <g>
            {/* Silo body & hopper */}
            <path
              d="M 90 28 L 150 28 L 150 65 L 132 105 L 108 105 L 90 65 Z"
              fill="#161c26"
              stroke="#334155"
              strokeWidth="1.5"
            />
            {/* Level bars */}
            <line x1="96" y1="42" x2="144" y2="42" stroke="#252f3e" strokeWidth="1.5" strokeDasharray="3 3" />
            <line x1="98" y1="56" x2="142" y2="56" stroke="#252f3e" strokeWidth="1.5" strokeDasharray="3 3" />
            {/* Rotating feed auger rotor */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="18" fill="#1e293b" stroke="#475569" strokeWidth="1.5" />
              <path d="M 120 70 L 120 100" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
              <path d="M 105 85 L 135 85" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
              <path d="M 109 74 L 131 96" stroke="#64748b" strokeWidth="2" strokeLinecap="round" />
              <circle cx="120" cy="85" r="5" fill={coreGlowColor} />
            </g>
            {/* Feeder chute */}
            <rect x="112" y="105" width="16" height="20" fill="#0f172a" stroke="#334155" strokeWidth="1" />
          </g>
        );

      case 'processing_unit':
        // Reaction milling vessel with dual counter-rotating cutters
        return (
          <g>
            {/* Heavy vessel casing */}
            <rect x="74" y="38" width="92" height="84" rx="10" fill="#141923" stroke="#334155" strokeWidth="1.5" />
            {/* Cooling mantle ribs */}
            <line x1="74" y1="52" x2="166" y2="52" stroke="#232b3b" strokeWidth="1.5" />
            <line x1="74" y1="70" x2="166" y2="70" stroke="#232b3b" strokeWidth="1.5" />
            <line x1="74" y1="88" x2="166" y2="88" stroke="#232b3b" strokeWidth="1.5" />
            <line x1="74" y1="106" x2="166" y2="106" stroke="#232b3b" strokeWidth="1.5" />
            {/* Primary rotating cutter rotor */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="26" fill="#18202d" stroke="#475569" strokeWidth="1.5" />
              <path d="M 120 62 L 120 108" stroke="#f59e0b" strokeWidth="3.5" strokeLinecap="round" />
              <path d="M 97 85 L 143 85" stroke="#f59e0b" strokeWidth="3.5" strokeLinecap="round" />
              <path d="M 104 69 L 136 101" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
              <path d="M 104 101 L 136 69" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
              <circle cx="120" cy="85" r="7" fill={coreGlowColor} />
            </g>
          </g>
        );

      case 'robot_pick_place':
        // Articulated robotic arm with rotating wrist / gripper
        return (
          <g>
            {/* Robot base pedestal */}
            <path d="M 96 122 L 144 122 L 138 98 L 102 98 Z" fill="#161c26" stroke="#334155" strokeWidth="1.5" />
            {/* Arm linkage */}
            <line x1="120" y1="98" x2="100" y2="60" stroke="#475569" strokeWidth="5" strokeLinecap="round" />
            <line x1="100" y1="60" x2="120" y2="85" stroke="#64748b" strokeWidth="4" strokeLinecap="round" />
            {/* Joint hubs */}
            <circle cx="100" cy="60" r="5" fill="#334155" stroke="#94a3b8" strokeWidth="1" />
            {/* Rotating wrist / end-effector tool */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="16" fill="#1b2432" stroke="#475569" strokeWidth="1.5" />
              <path d="M 112 73 L 128 73 L 124 85 L 116 85 Z" fill="#f59e0b" />
              <path d="M 112 97 L 128 97 L 124 85 L 116 85 Z" fill="#f59e0b" />
              <circle cx="120" cy="85" r="4" fill={coreGlowColor} />
            </g>
          </g>
        );

      case 'ai_vision_inspection':
        // Optical scan tunnel with rotating strobe disc and camera lens
        return (
          <g>
            {/* Arch portal */}
            <path
              d="M 80 120 L 80 50 Q 120 22 160 50 L 160 120"
              fill="none"
              stroke="#334155"
              strokeWidth="2"
            />
            {/* Scanner beam projection */}
            <polygon
              points="102,52 138,52 155,118 85,118"
              fill={coreGlowColor}
              fillOpacity={0.12}
            />
            {/* Camera lens barrel */}
            <rect x="108" y="44" width="24" height="14" rx="2" fill="#1e293b" stroke="#475569" strokeWidth="1.2" />
            {/* Rotating optical encoder / strobe disc */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="22" fill="#141c28" stroke="#38bdf8" strokeWidth="1.2" strokeDasharray="4 2" />
              <line x1="120" y1="67" x2="120" y2="103" stroke="#38bdf8" strokeWidth="2" />
              <line x1="102" y1="85" x2="138" y2="85" stroke="#38bdf8" strokeWidth="2" />
              <circle cx="120" cy="85" r="6" fill={coreGlowColor} />
            </g>
          </g>
        );

      case 'automated_sorting':
        // Dual conveyor belt and high-speed sorting paddle/diverter
        return (
          <g>
            {/* Conveyor bed */}
            <rect x="70" y="75" width="100" height="20" rx="3" fill="#151b24" stroke="#334155" strokeWidth="1.5" />
            <line x1="72" y1="85" x2="168" y2="85" stroke="#293344" strokeWidth="1.5" strokeDasharray="4 4" />
            {/* Diverter gate arm */}
            <line x1="100" y1="65" x2="135" y2="85" stroke="#f59e0b" strokeWidth="3.5" strokeLinecap="round" />
            {/* High-speed drive roller drum (RPM driven) */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="20" fill="#1b2432" stroke="#475569" strokeWidth="1.5" />
              <circle cx="120" cy="85" r="14" fill="#0f172a" stroke="#334155" strokeWidth="1" />
              <line x1="120" y1="68" x2="120" y2="102" stroke="#e2e8f0" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="103" y1="85" x2="137" y2="85" stroke="#e2e8f0" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="120" cy="85" r="5" fill={coreGlowColor} />
            </g>
          </g>
        );

      case 'automated_packaging':
        // Packaging tower, heated sealing bars, and rotating film spindle
        return (
          <g>
            {/* Tower frame */}
            <rect x="85" y="32" width="70" height="92" rx="4" fill="#141922" stroke="#334155" strokeWidth="1.5" />
            {/* Film supply reel (RPM driven) */}
            <g ref={rotorRef}>
              <circle cx="120" cy="65" r="20" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
              <path d="M 120 48 L 120 82" stroke="#94a3b8" strokeWidth="2.5" />
              <path d="M 103 65 L 137 65" stroke="#94a3b8" strokeWidth="2.5" />
              <circle cx="120" cy="65" r="6" fill={coreGlowColor} />
            </g>
            {/* Heated horizontal sealing jaws */}
            <rect x="92" y="98" width="56" height="10" rx="2" fill="#2d1515" stroke={coreGlowColor} strokeWidth="1.5" />
            <line x1="96" y1="103" x2="144" y2="103" stroke="#fca5a5" strokeWidth="1.5" />
          </g>
        );

      case 'finished_goods':
      default:
        // Pallet buffer platform & rotating turntable carousel
        return (
          <g>
            {/* Dispatch buffer base */}
            <rect x="74" y="96" width="92" height="26" rx="4" fill="#151b24" stroke="#334155" strokeWidth="1.5" />
            {/* Pallet boxes */}
            <rect x="92" y="58" width="24" height="24" rx="2" fill="#262f3e" stroke="#475569" strokeWidth="1.2" />
            <rect x="122" y="58" width="24" height="24" rx="2" fill="#262f3e" stroke="#475569" strokeWidth="1.2" />
            {/* Rotating carousel turntable (RPM driven) */}
            <g ref={rotorRef}>
              <circle cx="120" cy="85" r="22" fill="#171f2b" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="120" y1="65" x2="120" y2="105" stroke="#94a3b8" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="100" y1="85" x2="140" y2="85" stroke="#94a3b8" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="120" cy="85" r="6" fill={coreGlowColor} />
            </g>
          </g>
        );
    }
  };

  return (
    <div className="w-full bg-neutral-900/90 border border-neutral-800 rounded-xl p-3.5 relative overflow-hidden">
      {/* Visualizer header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
          <span className="font-mono text-xs font-semibold text-neutral-300 tracking-wider uppercase">
            Simulated Twin View
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
            {tempLabel}
          </span>
        </div>
        <div className="text-[11px] font-mono text-neutral-500">
          ID: {machineId}
        </div>
      </div>

      {/* 2D Interactive Digital Twin Schematic */}
      <div
        className={`relative w-full aspect-[240/130] flex items-center justify-center bg-neutral-950/80 rounded-lg border border-neutral-900 overflow-hidden ${
          isVibrating ? 'animate-[pulse_0.1s_infinite]' : ''
        }`}
        style={
          isVibrating
            ? {
                animation: `vibrateMotion ${Math.max(0.04, 0.2 - vibAmplitude * 0.015)}s infinite linear`,
              }
            : undefined
        }
      >
        <style>{`
          @keyframes vibrateMotion {
            0% { transform: translate(0, 0); }
            25% { transform: translate(${vibAmplitude * 0.4}px, -${vibAmplitude * 0.3}px); }
            50% { transform: translate(-${vibAmplitude * 0.3}px, ${vibAmplitude * 0.4}px); }
            75% { transform: translate(${vibAmplitude * 0.2}px, ${vibAmplitude * 0.2}px); }
            100% { transform: translate(0, 0); }
          }
        `}</style>

        {/* SVG Schematic */}
        <svg
          viewBox="0 0 240 140"
          className="w-full h-full max-h-[170px]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <radialGradient id={`core-glow-${machineId}`} cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor={coreGlowColor} stopOpacity={0.9 * normTemp + 0.3} />
              <stop offset="60%" stopColor={coreFillColor} stopOpacity={0.4} />
              <stop offset="100%" stopColor="#0b0d10" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Grid Background */}
          <line x1="20" y1="70" x2="220" y2="70" stroke="#1f242d" strokeWidth="0.75" strokeDasharray="2 3" />
          <line x1="120" y1="10" x2="120" y2="130" stroke="#1f242d" strokeWidth="0.75" strokeDasharray="2 3" />

          {/* Thermal Radiation Aura */}
          <circle
            cx="120"
            cy="85"
            r={34 + normTemp * 18}
            fill={`url(#core-glow-${machineId})`}
            className="transition-all duration-300"
          />

          {/* Machine-Specific Architecture & Rotating Component */}
          {renderMachineSchematic()}

          {/* Thermal Core Center Indicator */}
          <circle
            cx="120"
            cy="85"
            r="3"
            fill="#ffffff"
            className="animate-pulse"
          />

          {/* Calibrated Pressure Gauge Housing (Left) */}
          <g transform="translate(40, 48)">
            <circle cx="0" cy="0" r="18" fill="#141820" stroke="#3b4455" strokeWidth="1.2" />
            <path
              d="M -12 8 A 14 14 0 1 1 12 8"
              fill="none"
              stroke="#2f3747"
              strokeWidth="2"
              strokeDasharray="2 3"
            />
            {/* Calibrated Gauge Needle */}
            <g transform={`rotate(${pressureAngle} 0 0)`} className="transition-transform duration-150 ease-out">
              <line x1="0" y1="3" x2="0" y2="-13" stroke="#f59e0b" strokeWidth="1.75" strokeLinecap="round" />
              <circle cx="0" cy="0" r="2.5" fill="#e5e7eb" />
            </g>
            <text x="0" y="24" fill="#94a3b8" fontSize="6" fontFamily="JetBrains Mono" textAnchor="middle">
              PRESS
            </text>
          </g>

          {/* Vibration Sensor Indicator (Right) */}
          <g transform="translate(200, 48)">
            <rect x="-14" y="-12" width="28" height="24" rx="3" fill="#141820" stroke="#3b4455" strokeWidth="1.2" />
            {/* Waveform graphic responding to vibration */}
            <path
              d={`M -10 0 Q -5 -${vibAmplitude * 1.4} 0 0 T 10 0`}
              fill="none"
              stroke={vibration > 4 ? '#ef4444' : '#38bdf8'}
              strokeWidth="1.5"
              className="transition-all duration-150"
            />
            <text x="0" y="20" fill="#94a3b8" fontSize="6" fontFamily="JetBrains Mono" textAnchor="middle">
              VIB SENS
            </text>
          </g>
        </svg>

        {/* Live Reaction Summary Overlay */}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between text-[11px] font-mono text-neutral-400 bg-neutral-950/70 px-2.5 py-1 rounded backdrop-blur-sm border border-neutral-900">
          <span className="truncate">Rotor: {rpm} RPM</span>
          <span className="truncate text-amber-300">Temp: {temperature}°C</span>
          <span className="truncate">Vib: {vibration} mm/s</span>
          <span className="truncate">P: {pressure} bar</span>
        </div>
      </div>
    </div>
  );
};
