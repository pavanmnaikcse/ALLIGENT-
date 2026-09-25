# ALLIGENT Physics & Causal Digital Twin

**Product:** ALLIGENT — AI-Powered Industrial Investigation & Decision Support  
**Document:** Physics Formulation & Simulation Architecture  
**Version:** 1.0.0  

---

## 1. Physical Principles & Modeling Scope

The ALLIGENT Digital Twin simulates a high-performance **5-axis CNC machining center spindle** and rotating drive assembly. The simulator couples thermodynamics, mechanical friction, electrical drive dynamics, and regenerative cutting vibrations into a unified system of Ordinary Differential Equations (ODEs).

### 1.1 Spindle Drive Dynamics & Rotational Mechanics
The mechanical angular acceleration $\dot{\omega}$ of the spindle rotor is governed by the balance of electrical drive torque and opposing load torques:

$$J \frac{d\omega}{dt} = T_e - T_{friction}(\omega, T) - T_{cutting}(F_c, r) - B_{damping} \omega$$

Where:
* $J$: Rotor and tool assembly mass moment of inertia ($\text{kg}\cdot\text{m}^2$).
* $T_e$: Motor electromagnetic drive torque ($\text{N}\cdot\text{m}$).
* $T_{friction}$: Dynamic bearing and seal frictional torque ($\text{N}\cdot\text{m}$).
* $T_{cutting}$: Machining cutting resistance torque ($\text{N}\cdot\text{m}$), where $F_c$ is tangential cutting force.
* $B_{damping}$: Viscous aerodynamic and internal damping coefficient ($\text{N}\cdot\text{m}\cdot\text{s/rad}$).

---

## 2. Thermodynamic Formulation

The thermal state of the spindle bearings and housing is modeled as a two-node lumped capacitance thermal network accounting for frictional heat generation, resistive motor heating, and active cooling dissipation.

### 2.1 Heat Generation ($Q_{gen}$)
Frictional heat generated in the angular contact spindle bearings combines mechanical rolling friction and viscous lubricant shear:

$$Q_{gen} = \mu_{bearing} \cdot F_{preload} \cdot \omega \cdot r_{mean} + I_{rms}^2 R_{stator} + \eta_{cutting} F_c v_c$$

Where:
* $\mu_{bearing}$: Dynamic friction coefficient governed by the Stribeck curve.
* $F_{preload}$: Axial bearing preload force ($\text{N}$).
* $\omega$: Spindle rotational angular velocity ($\text{rad/s}$).
* $r_{mean}$: Bearing pitch diameter pitch radius ($\text{m}$).
* $I_{rms}^2 R_{stator}$: Joule heating generated within motor windings.

### 2.2 Thermal Dissipation ($Q_{diss}$)
Heat is dissipated to ambient air via natural convection and absorbed by circulating spindle coolant fluid:

$$Q_{diss} = h_{conv} A_{casing} (T_{casing} - T_{ambient}) + \dot{m}_{cool} c_p (T_{cool\_out} - T_{cool\_in})$$

Where:
* $h_{conv}$: Convective heat transfer coefficient ($\text{W}/(\text{m}^2\cdot\text{K})$).
* $A_{casing}$: Surface area of the outer spindle sleeve ($\text{m}^2$).
* $\dot{m}_{cool}$: Mass flow rate of coolant fluid ($\text{kg/s}$), directly modulated by coolant pump pressure.
* $c_p$: Specific heat capacity of the water-glycol coolant ($\approx 3800\text{ J}/(\text{kg}\cdot\text{K})$).

### 2.3 Thermal State ODE
Applying the first law of thermodynamics yields the rate of temperature change:

$$C_{thermal} \frac{dT}{dt} = Q_{gen} - Q_{diss}$$

Where $C_{thermal}$ is the effective thermal lumped capacitance of the bearing ring and spindle casing ($\text{J/K}$).

---

## 3. Vibration & Cutting Chatter Dynamics

The radial and axial vibration displacements ($x, y$) of the spindle tool point are modeled as a 2-degree-of-freedom mass-spring-damper oscillator subjected to regenerative chip thickness variations:

$$m \ddot{x} + c \dot{x} + k x = F_x(t) + F_{chatter}(x(t) - x(t - \tau))$$

Where:
* $m, c, k$: Modal mass, damping ratio, and dynamic stiffness of the spindle-tool assembly.
* $\tau = \frac{60}{N \cdot Z}$: Time delay between successive tooth passages (where $N$ is RPM and $Z$ is the number of cutter flutes).
* $F_{chatter}$: Regenerative cutting force perturbation proportional to dynamic chip thickness variation:
  $$F_{chatter}(t) = K_t b (x(t) - x(t - \tau))$$
  with $K_t$ representing the specific cutting force of the workpiece material ($\text{N/mm}^2$) and $b$ the axial depth of cut ($\text{mm}$).

---

## 4. Complete State Vector Specification

The simulation maintains a 10-dimensional physical state vector $\mathbf{X}(t)$ updated every $100\text{ms}$ ($\Delta t = 0.1\text{s}$):

| State Variable | Symbol | Python Key | Units | Nominal Range | Critical Alarm Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Spindle Speed** | $\omega$ | `spindle_speed` | RPM | $8,000 - 15,000$ | $> 18,500\text{ RPM}$ |
| **Spindle Power** | $P_{elec}$ | `spindle_power` | kW | $3.5 - 12.0$ | $> 22.0\text{ kW}$ |
| **Bearing Temperature** | $T_{bearing}$ | `temperature` | $^\circ\text{C}$ | $35.0 - 55.0$ | $> 78.0^\circ\text{C}$ |
| **Ambient Temperature** | $T_{amb}$ | `ambient_temp` | $^\circ\text{C}$ | $20.0 - 25.0$ | $> 40.0^\circ\text{C}$ |
| **Vibration Velocity RMS**| $v_{rms}$ | `vibration` | mm/s | $0.8 - 2.2$ | $> 4.5\text{ mm/s}$ |
| **Cutting Force** | $F_c$ | `cutting_force` | N | $200 - 750$ | $> 1,800\text{ N}$ |
| **Feed Rate** | $v_f$ | `feed_rate` | mm/min | $800 - 2,400$ | $> 3,600\text{ mm/min}$ |
| **Coolant Flow Pressure**| $P_{cool}$ | `coolant_pressure` | bar | $4.5 - 6.5$ | $< 2.0\text{ bar}$ |
| **Lubrication Film Ratio**| $\Lambda$ | `lubrication_ratio`| ratio | $1.8 - 3.5$ | $< 1.0\text{ (Boundary lubrication)}$ |
| **Tool Wear Flank** | $VB$ | `tool_wear` | $\mu\text{m}$ | $0 - 120$ | $> 300\mu\text{m}\text{ (Severe Wear)}$ |

---

## 5. Numerical Integration Scheme: Runge-Kutta 4th Order (RK4)

To prevent numerical instability and artificial energy injection during high-speed transitions, the differential equations are solved using classical **Runge-Kutta 4th Order**:

$$\mathbf{X}_{n+1} = \mathbf{X}_n + \frac{\Delta t}{6} (k_1 + 2k_2 + 2k_3 + k_4)$$

Where:
* $k_1 = f(t_n, \mathbf{X}_n)$
* $k_2 = f(t_n + \frac{\Delta t}{2}, \mathbf{X}_n + \frac{\Delta t}{2} k_1)$
* $k_3 = f(t_n + \frac{\Delta t}{2}, \mathbf{X}_n + \frac{\Delta t}{2} k_2)$
* $k_4 = f(t_n + \Delta t, \mathbf{X}_n + \Delta t k_3)$

---

## 6. Manual Modulation & Override Persistence

In industrial testing and mobile operator scenarios, users modulate parameters via the REST endpoint `POST /parameters/batch`.

To guarantee that manual overrides (such as forced coolant starvation or cutting load surges) are not overwritten by background steady-state simulation physics, `simulator/factory_sim.py` maintains an internal dictionary:

```python
# Thread-safe persistent override dictionary
self._manual_overrides: Dict[str, float] = {}

def set_override(self, parameter: str, value: float) -> None:
    with self._lock:
        self._manual_overrides[parameter] = value

def tick(self, dt: float) -> TelemetryRecord:
    # 1. Integrate physical equations
    state = self._rk4_step(dt)
    
    # 2. Enforce active operator overrides across all 10Hz ticks
    for param, value in self._manual_overrides.items():
        state[param] = value
        
    return state
```
This architecture ensures that operator inputs from the Mobile Gateway immediately propagate into the 10Hz stream and persist until explicitly cleared.
