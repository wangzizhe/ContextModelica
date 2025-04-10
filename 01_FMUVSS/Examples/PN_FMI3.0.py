from snakes.nets import PetriNet, Place, Transition, Value, Expression
from fmpy import simulate_fmu
import numpy as np
import matplotlib.pyplot as plt

# --- Step 1: Set up the Context Petri Net ---
net = PetriNet('ModeSwitch')

# Define places: Only one token in Pendulum means it's active; Freeflying starts empty.
net.add_place(Place('Pendulum', [1]))   # Active initially
net.add_place(Place('Freeflying', []))   # Inactive initially

# Globals for external variables used in guard expressions.
net.globals['F'] = 0   # For Pendulum
net.globals['r'] = 0   # For Freeflying

# Define transitions with guard expressions.
# When F < 0, deactivate Pendulum and activate Freeflying.
net.add_transition(Transition('Deactivate_Pendulum', Expression('F < 0')))
net.add_transition(Transition('Activate_Freeflying', Expression('F < 0')))
# When r > 2.0, deactivate Freeflying.
net.add_transition(Transition('Deactivate_Freeflying', Expression('r > 2.0')))
# (No activation of Pendulum is needed once Freeflying stops.)

# Define input/output arcs using a variable token.
net.add_input('Pendulum', 'Deactivate_Pendulum', Value(1))
net.add_output('Freeflying', 'Activate_Freeflying', Value(1))
net.add_input('Freeflying', 'Deactivate_Freeflying', Value(1))
# (No output arc for reactivating Pendulum.)

# --- Simulation Setup ---
pendulum_fmu = 'PendulumFMI3.0.fmu'
freeflying_fmu = 'FreeflyingFMI3.0.fmu'
dt = 0.01
stop_time = 10.0   # Maximum simulation time for Pendulum mode
t_switch = None    # To record the switching time

# --- Step 2: Simulate Pendulum Mode ---
print("Simulating Pendulum mode until F < 0 is reached...")
result_pendulum = simulate_fmu(pendulum_fmu,
                               stop_time=stop_time,
                               output=['x', 'y', 'dx', 'dy', 'F'],
                               step_size=dt)

# Loop through Pendulum simulation results.
idx_switch = None
for t, x, y, dx, dy, F in zip(result_pendulum['time'], result_pendulum['x'], result_pendulum['y'],
                               result_pendulum['dx'], result_pendulum['dy'], result_pendulum['F']):
    # Update global F so that guard expressions use it.
    net.globals['F'] = F

    # Print state and token counts.
    pendulum_tokens = len(net.place('Pendulum').tokens)
    freeflying_tokens = len(net.place('Freeflying').tokens)
    print(f"Pendulum Mode: t = {t:.2f}, x = {x:.4f}, F = {F:.4f}, Pendulum Tokens = {pendulum_tokens}, Freeflying Tokens = {freeflying_tokens}")

    # When F < 0, trigger the mode switch.
    if F < 0:
        t_switch = t
        idx_switch = np.argmin(np.abs(result_pendulum['time'] - t_switch))
        trans = net.transition('Deactivate_Pendulum')
        if trans.modes():
            binding = trans.modes()[0]
            trans.fire(binding)  # This should remove the token from Pendulum.
            net.transition('Activate_Freeflying').fire(binding)  # This adds a token to Freeflying.
            print(f"Switching to Freeflying at t = {t_switch:.3f}")
        break

if idx_switch is None:
    print("No switch occurred in Pendulum mode.")
    exit()

# --- Step 3: Simulate Freeflying Mode in Chunks ---
# Freeflying should run only while its place has a token.
freeflying_place = net.place('Freeflying')
if len(freeflying_place.tokens) > 0:
    print("Simulating Freeflying mode until its token is removed (deactivation transition fires)...")
    
    # Get initial conditions for Freeflying from the Pendulum result at the switch.
    x0 = result_pendulum['x'][idx_switch]
    y0 = result_pendulum['y'][idx_switch]
    vx0 = result_pendulum['dx'][idx_switch]
    vy0 = result_pendulum['dy'][idx_switch]

    free_times = []
    free_x = []
    free_y = []
    
    time_current = t_switch
    stop_time_freeflying = stop_time + 10.0  # overall freeflying simulation period

    # Run simulation in small chunks.
    while time_current < stop_time_freeflying:
        result_step = simulate_fmu(freeflying_fmu,
                                   start_time=time_current,
                                   stop_time=time_current + dt,
                                   start_values={'x': x0, 'y': y0, 'vx': vx0, 'vy': vy0},
                                   output=['x', 'y', 'vx', 'vy', 'r'],
                                   step_size=dt)
        # Update current state from the step:
        time_current = result_step['time'][-1]
        x0 = result_step['x'][-1]
        y0 = result_step['y'][-1]
        vx0 = result_step['vx'][-1]
        vy0 = result_step['vy'][-1]
        r = result_step['r'][-1]
        net.globals['r'] = r

        free_times.append(time_current)
        free_x.append(x0)
        free_y.append(y0)
        
        # Print the current state and token counts.
        print(f"Freeflying Mode: t = {time_current:.2f}, x = {x0:.4f}, y = {y0:.4f}, r = {r:.4f}, Freeflying Tokens = {len(freeflying_place.tokens)}")
        
        # Use the Petri net to check if deactivation should occur.
        trans_free = net.transition('Deactivate_Freeflying')
        if trans_free.modes():
            binding2 = trans_free.modes()[0]
            trans_free.fire(binding2)  # This should remove the token from Freeflying.
            print(f"Deactivating Freeflying mode at t = {time_current:.3f}")
            break

    # Convert Freeflying data to numpy arrays for merging.
    free_times = np.array(free_times)
    free_x = np.array(free_x)
    free_y = np.array(free_y)
else:
    print("Freeflying mode was never activated.")
    exit()

# --- Step 4: Merge the Data and Plot ---
merged_time = np.concatenate((result_pendulum['time'][:idx_switch + 1], free_times))
merged_x = np.concatenate((result_pendulum['x'][:idx_switch + 1], free_x))
merged_y = np.concatenate((result_pendulum['y'][:idx_switch + 1], free_y))

plt.figure(figsize=(6, 6))

# Plot Pendulum trajectory in blue
plt.plot(result_pendulum['x'][:idx_switch + 1],
         result_pendulum['y'][:idx_switch + 1],
         label='Pendulum', color='blue')

# Plot Freeflying trajectory in green
plt.plot(free_x, free_y, label='Freeflying', color='green')

# Mark the switch point in red
plt.scatter(result_pendulum['x'][idx_switch],
            result_pendulum['y'][idx_switch],
            color='red', label='Switch Point (F < 0)', zorder=5)

# Labels and formatting
plt.xlabel('x')
plt.ylabel('y')
plt.title('Pendulum → Freeflying Trajectory')
plt.legend()
plt.axis('equal')
plt.grid()
plt.tight_layout()
plt.show()