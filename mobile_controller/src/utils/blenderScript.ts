/**
 * Blender Companion Python Listener Script
 *
 * This script runs directly inside Blender (Scripting Workspace -> Text Editor -> Run Script).
 * It listens on local network (Wi-Fi or localhost:8080) for parameter updates sent from the
 * mobile "Digital Twin Controller" app and applies them live to 3D scene objects in real time.
 */

export const BLENDER_LISTENER_PYTHON_SCRIPT = `"""
=============================================================================
DIGITAL TWIN CONTROLLER — LIVE BLENDER COMPANION SCRIPT (bpy)
=============================================================================
Real-time listener for the mobile "Digital Twin Controller" app.
Supports 7 complete manufacturing pipeline digital twin machines:
  1. raw_material           (Raw Material Silo & Feeder, RM-01)
  2. processing_unit        (Thermal Reactor & Milling Unit, PU-02)
  3. robot_pick_place       (6-Axis Articulated Robot Arm, RP-03)
  4. ai_vision_inspection   (High-Speed Optical Scanner, VI-04)
  5. automated_sorting      (Pneumatic Diverter Sorting Belt, AS-05)
  6. automated_packaging    (Form-Fill-Seal Packaging Machine, AP-06)
  7. finished_goods         (Palletizer & Dispatch Buffer, FG-07)

LIVE 3D MODEL EFFECTS IN BLENDER (per machine):
  1. Temperature change -> Dynamic material emission & base color shifts
                           (cool industrial blue -> warm amber -> glowing red/orange).
  2. Vibration change   -> Continuous high-frequency mesh shake/jitter animation
                           driven by runtime timer (intensity scales with value).
  3. RPM change         -> Rotating rotor/spindle/arm/drum spins at the exact
                           angular velocity proportional to RPM in real time.
  4. Pressure change    -> Pressure gauge needle rotates across calibrated dial
                           AND pressure vessel chamber/actuator scales live.

KEY FEATURES:
  - Thread-safe HTTP daemon server (port 8080) with CORS support.
  - Safe execution on Blender main event loop via bpy.app.timers.
  - Forces continuous 3D Viewport redraws (area.tag_redraw()) for instant feedback.
  - Per-machine isolation: Only the object matching "machine_id" reacts.
  - Self-bootstrapping: Auto-creates all 7 digital twin machines aligned
    along a factory assembly line with materials, rotating rotors, shaking chassis,
    and sweeping gauge needles!
=============================================================================
"""

import bpy
import json
import queue
import threading
import time
import math
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# NETWORK CONFIGURATION
# ---------------------------------------------------------------------------
HOST = "0.0.0.0"       # Listen on all network interfaces (Wi-Fi & localhost)
PORT = 8080            # Match the port in the mobile app
TIMER_INTERVAL = 0.033 # ~30-60 FPS live animation loop

# Thread-safe message queue for incoming mobile payloads
update_queue = queue.Queue()
server_instance = None
server_thread = None
is_running = False

# Machine runtime states for continuous animations
machine_states = {}
last_timer_time = time.time()

# Production line configuration for the 7 manufacturing units
FLEET_SPEC = [
    {
        "id": "raw_material",
        "name": "Raw Material",
        "code": "RM-01",
        "type": "Silo & Feeder Conveyor",
        "loc": (-15.0, 0.0, 0.0),
        "nominal": {"temperature": 24.0, "vibration": 1.1, "rpm": 650.0, "pressure": 4.5}
    },
    {
        "id": "processing_unit",
        "name": "Processing Unit",
        "code": "PU-02",
        "type": "Thermal Reactor & Mill",
        "loc": (-10.0, 0.0, 0.0),
        "nominal": {"temperature": 82.0, "vibration": 2.8, "rpm": 2800.0, "pressure": 28.0}
    },
    {
        "id": "robot_pick_place",
        "name": "Robot Pick and Place",
        "code": "RP-03",
        "type": "6-Axis Articulated Arm",
        "loc": (-5.0, 0.0, 0.0),
        "nominal": {"temperature": 42.0, "vibration": 1.4, "rpm": 1800.0, "pressure": 6.2}
    },
    {
        "id": "ai_vision_inspection",
        "name": "AI Vision Inspection",
        "code": "VI-04",
        "type": "High-Speed Optical Scanner",
        "loc": (0.0, 0.0, 0.0),
        "nominal": {"temperature": 36.0, "vibration": 0.4, "rpm": 1200.0, "pressure": 3.0}
    },
    {
        "id": "automated_sorting",
        "name": "Automated Sorting",
        "code": "AS-05",
        "type": "Pneumatic Diverter Belt",
        "loc": (5.0, 0.0, 0.0),
        "nominal": {"temperature": 38.0, "vibration": 1.9, "rpm": 1650.0, "pressure": 7.5}
    },
    {
        "id": "automated_packaging",
        "name": "Automated Packaging",
        "code": "AP-06",
        "type": "Form-Fill-Seal Packaging",
        "loc": (10.0, 0.0, 0.0),
        "nominal": {"temperature": 110.0, "vibration": 2.2, "rpm": 2100.0, "pressure": 15.0}
    },
    {
        "id": "finished_goods",
        "name": "Finished Goods",
        "code": "FG-07",
        "type": "Palletizer & Dispatch Buffer",
        "loc": (15.0, 0.0, 0.0),
        "nominal": {"temperature": 26.0, "vibration": 0.6, "rpm": 850.0, "pressure": 5.5}
    }
]


# ---------------------------------------------------------------------------
# HTTP REQUEST HANDLER (THREAD-SAFE WITH CORS)
# ---------------------------------------------------------------------------
class DigitalTwinHTTPHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Enable cross-origin requests from mobile browser
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cache-Control')
        self.end_headers()

    def do_GET(self):
        # Health check ping endpoint
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        res = {
            "status": "online",
            "blender_version": bpy.app.version_string,
            "connected_machines": list(machine_states.keys()),
            "total_machines": len(machine_states),
            "message": "Blender 7-Machine Manufacturing Line Listener is active and listening!"
        }
        self.wfile.write(json.dumps(res).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode('utf-8'))
            update_queue.put(payload)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "received"}')
        except Exception as err:
            self.send_response(400)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(err)}).encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress spammy HTTP access logs in Blender system console
        return


# ---------------------------------------------------------------------------
# 3D MODEL RIGGING & PROCEDURAL GENERATION (FOR ALL 7 MACHINES)
# ---------------------------------------------------------------------------
def get_or_create_machine_rig(machine_id, machine_name=None, position=(0, 0, 0)):
    """Finds an existing 3D model object matching machine_id, or builds one."""
    # 1. Search existing objects by custom property or object name
    for obj in bpy.data.objects:
        if obj.get("machine_id") == machine_id or obj.name == f"Twin_{machine_id}":
            return obj

    print(f"[Digital Twin] Generating 3D digital twin model for '{machine_id}' at {position}...")

    # Look up nominal values if defined
    spec = next((item for item in FLEET_SPEC if item["id"] == machine_id), None)
    initial_temp = spec["nominal"]["temperature"] if spec else 45.0
    initial_vib = spec["nominal"]["vibration"] if spec else 1.2
    initial_rpm = spec["nominal"]["rpm"] if spec else 1450.0
    initial_press = spec["nominal"]["pressure"] if spec else 12.5

    # A. Base Chassis (Mounting Pedestal)
    bpy.ops.mesh.primitive_cube_add(size=1.6, location=(position[0], position[1], position[2] + 0.8))
    base = bpy.context.active_object
    base.name = f"Twin_{machine_id}"
    base["machine_id"] = machine_id
    base["temperature"] = float(initial_temp)
    base["vibration"] = float(initial_vib)
    base["rpm"] = float(initial_rpm)
    base["pressure"] = float(initial_press)

    # B. Dynamic Thermal Material (Principled BSDF with Emission)
    mat = bpy.data.materials.new(name=f"Mat_Thermal_{machine_id}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Roughness"].default_value = 0.25
        bsdf.inputs["Metallic"].default_value = 0.85
        bsdf.inputs["Base Color"].default_value = (0.2, 0.25, 0.35, 1.0)
        # Handle emission across Blender versions
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (0.1, 0.4, 0.9, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.0
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = (0.1, 0.4, 0.9, 1.0)
    base.data.materials.append(mat)

    # C. Dynamic Rotating Rotor/Assembly (for RPM visualization)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.75,
        depth=0.25,
        location=(position[0], position[1], position[2] + 1.85)
    )
    rotor = bpy.context.active_object
    rotor.name = f"{base.name}_Rotor"
    rotor.parent = base

    # Rotor blades/vanes for clear visual spin
    rotor_mat = bpy.data.materials.new(name=f"Mat_Rotor_{machine_id}")
    rotor_mat.use_nodes = True
    r_bsdf = rotor_mat.node_tree.nodes.get("Principled BSDF")
    if r_bsdf:
        r_bsdf.inputs["Base Color"].default_value = (0.9, 0.65, 0.2, 1.0)
        r_bsdf.inputs["Metallic"].default_value = 0.9
    rotor.data.materials.append(rotor_mat)

    # Crossbar vanes on rotor for obvious rotation
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(position[0], position[1], position[2] + 2.0)
    )
    vane1 = bpy.context.active_object
    vane1.scale = (0.12, 1.3, 0.08)
    vane1.parent = rotor
    vane1.name = f"{rotor.name}_Vane1"

    # D. Pressure Vessel Chamber / Cylinder (scales/deforms with pressure)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.35,
        location=(position[0] - 0.7, position[1], position[2] + 0.9)
    )
    chamber = bpy.context.active_object
    chamber.name = f"{base.name}_Chamber"
    chamber.parent = base

    # E. Pressure Gauge Housing & Rotating Needle
    # Dial Face
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.3,
        depth=0.08,
        location=(position[0] + 0.85, position[1], position[2] + 0.95),
        rotation=(0, math.pi / 2, 0)
    )
    gauge_body = bpy.context.active_object
    gauge_body.name = f"{base.name}_GaugeBody"
    gauge_body.parent = base

    # Gauge Needle (rotates live)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.025,
        depth=0.28,
        location=(position[0] + 0.91, position[1], position[2] + 0.95),
        rotation=(0, math.pi / 2, 0)
    )
    needle = bpy.context.active_object
    needle.name = f"{base.name}_GaugeNeedle"
    needle.parent = base

    # Color needle in bright warning orange
    needle_mat = bpy.data.materials.new(name=f"Mat_Needle_{machine_id}")
    needle_mat.use_nodes = True
    n_bsdf = needle_mat.node_tree.nodes.get("Principled BSDF")
    if n_bsdf:
        n_bsdf.inputs["Base Color"].default_value = (1.0, 0.4, 0.0, 1.0)
    needle.data.materials.append(needle_mat)

    # F. Machine-specific Architectural Accent
    if machine_id == "raw_material":
        # Silo Funnel Hopper on top
        bpy.ops.mesh.primitive_cone_add(radius1=0.8, radius2=0.3, depth=0.8, location=(position[0], position[1], position[2] + 2.6))
        hopper = bpy.context.active_object
        hopper.name = f"{base.name}_SiloHopper"
        hopper.parent = base
    elif machine_id == "robot_pick_place":
        # Articulated Arm Mast
        bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=1.2, location=(position[0], position[1] - 0.4, position[2] + 2.2))
        arm = bpy.context.active_object
        arm.name = f"{base.name}_ArmMast"
        arm.parent = base
    elif machine_id == "ai_vision_inspection":
        # Inspection Gantry Arch / Lens Dome
        bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.1, location=(position[0], position[1], position[2] + 2.2))
        gantry = bpy.context.active_object
        gantry.name = f"{base.name}_ScanArch"
        gantry.parent = base
    elif machine_id == "automated_packaging":
        # Packaging Tower Mast
        bpy.ops.mesh.primitive_cube_add(size=0.6, location=(position[0], position[1], position[2] + 2.5))
        tower = bpy.context.active_object
        tower.scale = (0.7, 0.7, 1.6)
        tower.name = f"{base.name}_PackagingTower"
        tower.parent = base

    # G. Floating 3D Text Label
    try:
        bpy.ops.object.text_add(location=(position[0] - 0.9, position[1] - 1.2, position[2] + 2.4))
        text_obj = bpy.context.active_object
        text_obj.name = f"{base.name}_Label"
        label_text = machine_name or (spec["name"] if spec else machine_id)
        if spec:
            label_text = f"{spec['code']} {spec['name']}"
        text_obj.data.body = label_text
        text_obj.scale = (0.24, 0.24, 0.24)
        text_obj.rotation_euler = (math.pi / 2, 0, 0)
        text_obj.parent = base
    except Exception:
        pass

    # Initialize machine state tracking
    machine_states[machine_id] = {
        "temperature": float(initial_temp),
        "vibration": float(initial_vib),
        "rpm": float(initial_rpm),
        "pressure": float(initial_press),
        "base_location": position,
        "rotor_angle": 0.0,
        "target_needle_angle": 0.0
    }

    return base


# ---------------------------------------------------------------------------
# APPLY LIVE PARAMETER UPDATES TO BLENDER MODEL
# ---------------------------------------------------------------------------
def apply_parameter_update(payload):
    """Applies incoming payload to the targeted Blender 3D model."""
    machine_id = payload.get("machine_id", "raw_material")
    param = payload.get("parameter")
    value = float(payload.get("value", 0))

    # Retrieve or generate 3D model
    obj = get_or_create_machine_rig(machine_id)
    if not obj:
        return

    # Update Blender custom property on target object
    obj[param] = value

    if machine_id not in machine_states:
        machine_states[machine_id] = {
            "temperature": 45.0,
            "vibration": 1.2,
            "rpm": 1450.0,
            "pressure": 12.5,
            "base_location": tuple(obj.location),
            "rotor_angle": 0.0,
            "target_needle_angle": 0.0
        }

    machine_states[machine_id][param] = value

    # -----------------------------------------------------------------------
    # EFFECT 1: TEMPERATURE (Material Color & Emission Shift)
    # Cooler = Cool blue glow -> Warm Amber -> Hot Glowing Red/Orange
    # -----------------------------------------------------------------------
    if param == "temperature":
        norm = min(max((value - 20.0) / 100.0, 0.0), 1.0)
        r = 0.1 + norm * 0.9
        g = 0.4 + (1.0 - abs(norm - 0.5) * 2.0) * 0.3 - (norm * 0.2)
        b = max(0.9 * (1.0 - norm * 1.5), 0.05)
        emission_strength = 0.5 + norm * 6.0

        if obj.data.materials:
            mat = obj.data.materials[0]
            if mat.use_nodes:
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Base Color"].default_value = (r * 0.7, g * 0.7, b * 0.7, 1.0)
                    if "Emission Color" in bsdf.inputs:
                        bsdf.inputs["Emission Color"].default_value = (r, g, b, 1.0)
                        bsdf.inputs["Emission Strength"].default_value = emission_strength
                    elif "Emission" in bsdf.inputs:
                        bsdf.inputs["Emission"].default_value = (r * emission_strength, g * emission_strength, b * emission_strength, 1.0)

    # -----------------------------------------------------------------------
    # EFFECT 4: PRESSURE (Gauge Needle Rotation & Chamber Deformation)
    # Needle sweeps -120 to +120 degrees; chamber expands slightly
    # -----------------------------------------------------------------------
    elif param == "pressure":
        norm_p = min(max(value / 50.0, 0.0), 1.0)
        needle_angle = math.radians(-120.0 + norm_p * 240.0)
        
        needle = bpy.data.objects.get(f"{obj.name}_GaugeNeedle")
        if needle:
            needle.rotation_euler[0] = needle_angle

        chamber = bpy.data.objects.get(f"{obj.name}_Chamber")
        if chamber:
            scale_factor = 1.0 + norm_p * 0.25
            chamber.scale = (scale_factor, scale_factor, scale_factor)


# ---------------------------------------------------------------------------
# BLENDER MAIN-THREAD ANIMATION LOOP (30-60 FPS)
# ---------------------------------------------------------------------------
def live_timer_tick():
    """Executed by bpy.app.timers on Blender's main event thread."""
    global last_timer_time
    now = time.time()
    dt = min(max(now - last_timer_time, 0.001), 0.1)
    last_timer_time = now

    # 1. Drain incoming network updates
    while not update_queue.empty():
        try:
            payload = update_queue.get_nowait()
            apply_parameter_update(payload)
        except queue.Empty:
            break

    # 2. Continuous real-time visual animation drivers for all machines
    for machine_id, state in machine_states.items():
        obj = bpy.data.objects.get(f"Twin_{machine_id}") or bpy.data.objects.get(machine_id)
        if not obj:
            continue

        # -------------------------------------------------------------------
        # EFFECT 3: RPM ROTATION (Continuously spins rotor at exact speed)
        # -------------------------------------------------------------------
        rpm = state.get("rpm", 0.0)
        if rpm > 0:
            rotor = bpy.data.objects.get(f"{obj.name}_Rotor") or obj
            ang_vel = (rpm / 60.0) * (2.0 * math.pi)
            rotor.rotation_euler[2] += ang_vel * dt

        # -------------------------------------------------------------------
        # EFFECT 2: VIBRATION SHAKE (High-frequency chassis micro-jitter)
        # -------------------------------------------------------------------
        vib = state.get("vibration", 0.0)
        base_loc = state.get("base_location", (0, 0, 0))
        if vib > 0.05:
            amp = (vib / 10.0) * 0.08
            freq = 45.0
            phase = now * freq
            jx = math.sin(phase) * amp + (random.random() - 0.5) * (amp * 0.5)
            jy = math.cos(phase * 1.2) * amp + (random.random() - 0.5) * (amp * 0.5)
            jz = (random.random() - 0.5) * (amp * 0.4)
            obj.location = (base_loc[0] + jx, base_loc[1] + jy, base_loc[2] + jz)
        else:
            obj.location = base_loc

    # -----------------------------------------------------------------------
    # CRITICAL: Force Blender's 3D Viewport to redraw continuously
    # -----------------------------------------------------------------------
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    return TIMER_INTERVAL if is_running else None


# ---------------------------------------------------------------------------
# LISTENER LIFECYCLE (START / STOP)
# ---------------------------------------------------------------------------
def start_listener():
    global server_instance, server_thread, is_running, last_timer_time

    if is_running:
        print("[Digital Twin] Listener is already running.")
        return

    stop_listener()

    try:
        server_instance = HTTPServer((HOST, PORT), DigitalTwinHTTPHandler)
        server_thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
        server_thread.start()
        is_running = True
        last_timer_time = time.time()

        # Register persistent Blender timer
        bpy.app.timers.register(live_timer_tick, persistent=True)

        print("\\n" + "=" * 65)
        print("DIGITAL TWIN CONTROLLER — 7-MACHINE BLENDER LISTENER ONLINE")
        print(f"Listening on: http://0.0.0.0:{PORT}")
        print("Supporting: Raw Material, Processing Unit, Robot Pick & Place,")
        print("            AI Vision, Sorting, Packaging, and Finished Goods")
        print("Ready to receive live parameter updates from your mobile app!")
        print("Tip: In Blender 3D Viewport, press 'Z' and choose 'Material Preview'")
        print("     or 'Rendered' to see thermal emission glow effects.")
        print("=" * 65 + "\\n")

    except Exception as e:
        print(f"[Digital Twin Error] Failed to start listener: {e}")


def stop_listener():
    global server_instance, is_running
    is_running = False
    if server_instance:
        try:
            server_instance.shutdown()
            server_instance.server_close()
            print("[Digital Twin] Listener stopped.")
        except Exception as e:
            print(f"[Digital Twin] Error closing listener: {e}")
        server_instance = None


# ---------------------------------------------------------------------------
# AUTO-BOOTSTRAP COMPLETE 7-MACHINE DEMO SCENE
# ---------------------------------------------------------------------------
def setup_demo_scene():
    """Generates all 7 digital twin machines along an automated factory production line."""
    print("[Digital Twin] Bootstrapping 7-machine manufacturing digital twin line...")

    for spec in FLEET_SPEC:
        m_id = spec["id"]
        m_name = f"{spec['name']} ({spec['code']})"
        loc = spec["loc"]
        obj = get_or_create_machine_rig(m_id, m_name, loc)
        obj.location = loc
        if m_id in machine_states:
            machine_states[m_id]["base_location"] = loc

    # Connecting Conveyor Guide Bed along the entire factory floor
    conveyor_name = "Factory_Conveyor_Track"
    if conveyor_name not in bpy.data.objects:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.1))
        conv = bpy.context.active_object
        conv.name = conveyor_name
        conv.scale = (34.0, 1.2, 0.2)
        conv_mat = bpy.data.materials.new(name="Mat_Conveyor_Bed")
        conv_mat.use_nodes = True
        c_bsdf = conv_mat.node_tree.nodes.get("Principled BSDF")
        if c_bsdf:
            c_bsdf.inputs["Base Color"].default_value = (0.1, 0.12, 0.15, 1.0)
            c_bsdf.inputs["Metallic"].default_value = 0.7
        conv.data.materials.append(conv_mat)

    # Setup studio sun light if none exists
    if not any(o.type == 'LIGHT' for o in bpy.data.objects):
        bpy.ops.object.light_add(type='SUN', location=(5, -8, 15))
        sun = bpy.context.active_object
        sun.data.energy = 3.5

    print("[Digital Twin] 7-machine digital twin line fully initialized in Blender!")


# Run automatically on execution
if __name__ == "__main__":
    setup_demo_scene()
    start_listener()
`;
