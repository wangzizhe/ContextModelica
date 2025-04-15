from pyfmi import load_fmu
import numpy as np
import matplotlib.pyplot as plt

# === Simulation Settings ===
pendulum_fmu_path = "PendulumFMI2.0.fmu"      # Replace with your actual FMU path
freeflying_fmu_path = "FreeflyingFMI2.0.fmu"     # Replace with your actual FMU path

step_size = 0.01
stop_time = 10.0
L = 2.001

# === Step 1: Simulate Pendulum ===
print("🔄 Simulating Pendulum model...")
pendulum_fmu = load_fmu(pendulum_fmu_path)
pendulum_fmu.setup_experiment(start_time=0.0)
pendulum_fmu.initialize()

time_p = []
x_p = []
y_p = []
dx_p = []
dy_p = []
F_p = []

t = 0.0
switch_found = False

# Simulate the pendulum until t reaches pendulum_stop_time or until F becomes negative.
while t <= stop_time:
    pendulum_fmu.do_step(current_t=t, step_size=step_size)
    
    # Get outputs from the pendulum FMU
    x_val = pendulum_fmu.get("x")
    y_val = pendulum_fmu.get("y")
    dx_val = pendulum_fmu.get("dx")
    dy_val = pendulum_fmu.get("dy")
    F_val = pendulum_fmu.get("F")
    
    # For compatibility, if the FMU returns arrays, take the first element.
    x_val = x_val[0] if isinstance(x_val, np.ndarray) else x_val
    y_val = y_val[0] if isinstance(y_val, np.ndarray) else y_val
    dx_val = dx_val[0] if isinstance(dx_val, np.ndarray) else dx_val
    dy_val = dy_val[0] if isinstance(dy_val, np.ndarray) else dy_val
    F_val  = F_val[0]  if isinstance(F_val, np.ndarray)  else F_val
    
    time_p.append(t)
    x_p.append(x_val)
    y_p.append(y_val)
    dx_p.append(dx_val)
    dy_p.append(dy_val)
    F_p.append(F_val)
    
    # Check switching condition: F becomes negative.
    if F_val < 0:
        switch_found = True
        break
    
    t += step_size

if not switch_found:
    print("❌ No switching point found; F never dropped below 0 during pendulum phase.")
    pendulum_fmu.terminate()
    exit()

t_switch = t
print(f"✅ Pendulum stops at t = {t_switch:.3f}s with F = {F_val:.4f}")
print(f"    Position: x = {x_val:.4f}, y = {y_val:.4f}")
print(f"    Velocity: dx = {dx_val:.4f}, dy = {dy_val:.4f}")
pendulum_fmu.terminate()

# === Step 2: Simulate Free-Flying ===
print("🔁 Switching to FreeFlying model...")
freeflying_fmu = load_fmu(freeflying_fmu_path)
freeflying_fmu.setup_experiment(start_time=t_switch)

# Set initial state from pendulum switch point.
start_vals = {
    "x": x_val,
    "y": y_val,
    "vx": dx_val,
    "vy": dy_val
}
for var, val in start_vals.items():
    freeflying_fmu.set(var, val)

freeflying_fmu.initialize()

time_f = [t_switch]
x_f = [x_val]
y_f = [y_val]

t_free = t_switch
cutoff_found = False

while t_free < stop_time:
    freeflying_fmu.do_step(current_t=t_free, step_size=step_size)
    
    x_val_free = freeflying_fmu.get("x")
    y_val_free = freeflying_fmu.get("y")
    r = freeflying_fmu.get("r")
    
    x_val_free = x_val_free[0] if isinstance(x_val_free, np.ndarray) else x_val_free
    y_val_free = y_val_free[0] if isinstance(y_val_free, np.ndarray) else y_val_free
    r = r[0] if isinstance(r, np.ndarray) else r
    
    t_free += step_size
    time_f.append(t_free)
    x_f.append(x_val_free)
    y_f.append(y_val_free)
    
    if r > L:
        print(f"✅ FreeFlying stops at t = {t_free:.3f}s when r = {r:.4f} > L = {L}")
        cutoff_found = True
        break

if not cutoff_found:
    print("⚠️ FreeFlying phase finished but r never exceeded L.")
freeflying_fmu.terminate()

# === Step 3: Stitch and Plot Trajectory ===
# Combine time and trajectories from both phases.
merged_time = np.concatenate((np.array(time_p[:len(time_p)]), np.array(time_f)))
merged_x = np.concatenate((np.array(x_p[:len(time_p)]), np.array(x_f)))
merged_y = np.concatenate((np.array(y_p[:len(time_p)]), np.array(y_f)))

plt.figure(figsize=(6, 6))
# Pendulum Phase: plot in blue
plt.plot(x_p, y_p, label='Pendulum', color='blue')
# FreeFlying Phase: plot in green
plt.plot(x_f, y_f, label='FreeFlying', color='green')
# Mark the switch point with a red dot
plt.scatter([x_val], [y_val], color='red', label='Switch Point (F < 0)', zorder=5)

plt.xlabel('x')
plt.ylabel('y')
plt.title('Pendulum → FreeFlying Trajectory')
plt.legend()
plt.axis('equal')
plt.grid(True)
plt.tight_layout()
plt.show()