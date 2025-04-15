from snakes.nets import PetriNet, Place, Transition, Value, Expression
from pyfmi import load_fmu
import numpy as np
import matplotlib.pyplot as plt

# --- Petri Net Setup ---
net = PetriNet('ModeSwitch')
net.add_place(Place('Pendulum', [1])) 
net.add_place(Place('Freeflying', []))

net.globals['F'] = 0
net.globals['r'] = 0 

# Transitions based on guard expressions
net.add_transition(Transition('Deactivate_Pendulum', Expression('F < 0')))
net.add_transition(Transition('Activate_Freeflying', Expression('F < 0')))
net.add_transition(Transition('Deactivate_Freeflying', Expression('r > 2.0')))
net.add_transition(Transition('Activate_Pendulum', Expression('r > 2.0')))

# Input and output variables for transitions
net.add_input('Pendulum', 'Deactivate_Pendulum', Value(1))
net.add_output('Freeflying', 'Activate_Freeflying', Value(1))
net.add_input('Freeflying', 'Deactivate_Freeflying', Value(1))
net.add_output('Pendulum', 'Activate_Pendulum', Value(1))

# --- Load FMUs with Co-Simulation Mode ---
pendulum_fmu = load_fmu("PendulumFMI2.0.fmu")
freeflying_fmu = load_fmu("FreeflyingFMI2.0.fmu")

# Setup and initialize FMUs
pendulum_fmu.setup_experiment(start_time=0.0, stop_time=1.0)  # Set start and stop time
pendulum_fmu.initialize()  # Initialize the FMU for pendulum
freeflying_fmu.setup_experiment(start_time=0.0, stop_time=1.0)  # Set start and stop time
freeflying_fmu.initialize()  # Initialize the FMU for freeflying

step_size = 0.01

time_log = []
x_log = []
y_log = []
mode_log = []

# --- Mode Simulation Functions ---
def simulate_pendulum_mode():
    t = 0.0

    while net.place('Pendulum').tokens:
        # Set the pendulum input, e.g., force F (optional, adjust based on your model)
        pendulum_fmu.set('F', net.globals['F'])

        # Perform one simulation step using the low-level API (do_step)
        pendulum_fmu.do_step(current_t=t, step_size=step_size)

        # Get the state variables from the FMU after the simulation step
        x = pendulum_fmu.get('x')
        y = pendulum_fmu.get('y')
        dx = pendulum_fmu.get('dx')
        dy = pendulum_fmu.get('dy')
        F = pendulum_fmu.get('F')

        # Access the scalar values (e.g., x[0], F[0] if they are returned as arrays)
        x_value = x[0] if isinstance(x, np.ndarray) else x
        F_value = F[0] if isinstance(F, np.ndarray) else F

        # Update Petri Net global variables
        net.globals['F'] = F_value

        # Log simulation data
        time_log.append(t)
        x_log.append(x_value)
        y_log.append(y)
        mode_log.append('Pendulum')

        # Print variables for pendulum mode at each time step
        print(f"Pendulum Mode - Time: {t:.2f}, x: {x_value:.4f}, F: {F_value:.4f}")

        # Check for transition to Freeflying mode
        if net.transition('Deactivate_Pendulum').modes():
            binding = net.transition('Deactivate_Pendulum').modes()[0]
            net.transition('Deactivate_Pendulum').fire(binding)
            net.transition('Activate_Freeflying').fire(binding)
            break

        t += step_size

    return {'x': x_value, 'y': y, 'vx': dx, 'vy': dy, 'time': t}

def simulate_freeflying_mode(init_vals):
    # Debug: Print the initial values being set for Freeflying mode
    print(f"Initializing Freeflying Mode with: x={init_vals['x']}, y={init_vals['y']}, vx={init_vals['vx']}, vy={init_vals['vy']}")

    # Set the initial values from the Pendulum mode to Freeflying mode
    freeflying_fmu.set('x', init_vals['x'])
    freeflying_fmu.set('y', init_vals['y'])
    freeflying_fmu.set('vx', init_vals['vx'])
    freeflying_fmu.set('vy', init_vals['vy'])

    t = init_vals['time']

    while net.place('Freeflying').tokens:
        # Set the freeflying input (if any)
        freeflying_fmu.set('r', net.globals['r'])

        # Perform one simulation step using the low-level API (do_step)
        freeflying_fmu.do_step(current_t=t, step_size=step_size)

        # Get the state variables from the FMU after the simulation step
        x = freeflying_fmu.get('x')
        y = freeflying_fmu.get('y')
        vx = freeflying_fmu.get('vx')
        vy = freeflying_fmu.get('vy')
        r = round(freeflying_fmu.get('r').item(), 2)

        # Access the scalar values (e.g., x[0], r if they are returned as arrays)
        x_value = x[0] if isinstance(x, np.ndarray) else x
        r_value = r[0] if isinstance(r, np.ndarray) else r

        # Update Petri Net global variables
        net.globals['r'] = r_value

        # Log simulation data
        time_log.append(t)
        x_log.append(x_value)
        y_log.append(y)
        mode_log.append('Freeflying')

        # Print variables for freeflying mode at each time step
        print(f"Freeflying Mode - Time: {t:.2f}, x: {x_value:.2f}, r: {r_value:.2f}")
        
        # Check for transition to Pendulum mode
        if net.transition('Deactivate_Freeflying').modes():
            binding = net.transition('Deactivate_Freeflying').modes()[0]
            net.transition('Deactivate_Freeflying').fire(binding)
            break
    
        t += step_size

# --- Main Control Loop ---
while net.place('Pendulum').tokens or net.place('Freeflying').tokens:
    if net.place('Pendulum').tokens:
        pend_result = simulate_pendulum_mode()
    elif net.place('Freeflying').tokens:
        simulate_freeflying_mode(pend_result)

# --- Plot Results ---
time_log = np.array(time_log)
x_log = np.array(x_log)
y_log = np.array(y_log)
mode_log = np.array(mode_log)

# Plot each mode’s trajectory
plt.figure(figsize=(8, 6))
for mode in ['Pendulum', 'Freeflying']:
    mask = mode_log == mode
    plt.plot(x_log[mask], y_log[mask], label=mode)

plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid()
plt.title("Mode Switching Trajectory")
plt.axis('equal')
plt.show()

# Finalize FMUs
pendulum_fmu.terminate()
freeflying_fmu.terminate()
