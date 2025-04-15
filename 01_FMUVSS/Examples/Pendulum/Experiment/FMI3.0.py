from fmpy import simulate_fmu
import numpy as np
import matplotlib.pyplot as plt

# === Step 1: Simulate Pendulum ===
pendulum_fmu = 'PendulumFMI3.0.fmu'
freeflying_fmu = 'FreeflyingFMI3.0.fmu'
stop_time = 10.0
L = 2.001

print("🔄 Simulating Pendulum model...")

# Simulate pendulum until F < 0
result_pendulum = simulate_fmu(pendulum_fmu, stop_time=stop_time, output=['x', 'y', 'dx', 'dy', 'F'], step_size=0.01)

# Find switching point: F < 0
switch_index = None
for i, F_val in enumerate(result_pendulum['F']):
    if F_val < 0:
        switch_index = i
        break

if switch_index is None:
    print("❌ No switch point found. F never < 0.")
    exit()

# Get switch values
t_switch = result_pendulum['time'][switch_index]
x0 = result_pendulum['x'][switch_index]
y0 = result_pendulum['y'][switch_index]
vx0 = result_pendulum['dx'][switch_index]
vy0 = result_pendulum['dy'][switch_index]
F_val = result_pendulum['F'][switch_index]

print(f"✅ Pendulum stops at t = {t_switch:.3f} s with:")
print(f"    F = {F_val:.4f}")
print(f"    Position: x = {x0:.4f}, y = {y0:.4f}")
print(f"    Velocity: vx = {vx0:.4f}, vy = {vy0:.4f}")
print("🔁 Switching to FreeFlying...")

# === Step 2: Simulate FreeFlying until r > L ===
start_values = {
    'x': x0,
    'y': y0,
    'vx': vx0,
    'vy': vy0
}

result_free = simulate_fmu(
    freeflying_fmu,
    start_time=t_switch,
    stop_time=t_switch + 10.0,
    start_values=start_values,
    output=['x', 'y', 'vx', 'vy', 'r'],
    step_size=0.01
)

r_val = result_free['r']

cutoff_index = np.argmax(r_val > L)

if r_val[cutoff_index] <= L:
    print("⚠️  FreeFlying: r never exceeded L = 2.0.")
    cutoff_index = len(r_val)
    t_end = result_free['time'][-1]
else:
    t_end = result_free['time'][cutoff_index]
    r_exceeded = r_val[cutoff_index]
    print(f"✅ FreeFlying stops at t = {t_end:.3f} s when r = {r_exceeded:.4f} > L = 2.0")

# === Step 3: Stitch and Plot ===
merged_time = np.concatenate((result_pendulum['time'][:switch_index+1], result_free['time'][:cutoff_index+1]))
merged_x = np.concatenate((result_pendulum['x'][:switch_index+1], result_free['x'][:cutoff_index+1]))
merged_y = np.concatenate((result_pendulum['y'][:switch_index+1], result_free['y'][:cutoff_index+1]))

plt.figure(figsize=(6, 6))

# Plot Pendulum phase in blue
plt.plot(result_pendulum['x'][:switch_index+1],
         result_pendulum['y'][:switch_index+1],
         label='Pendulum', color='blue')

# Plot FreeFlying phase in green
plt.plot(result_free['x'][:cutoff_index+1],
         result_free['y'][:cutoff_index+1],
         label='FreeFlying', color='green')

# Mark the switch point
plt.scatter([x0], [y0], color='red', label='Switch Point (F < 0)', zorder=5)

plt.xlabel('x')
plt.ylabel('y')
plt.title('Pendulum → FreeFlying Trajectory')
plt.legend()
plt.axis('equal')
plt.grid()
plt.show()