# Using SNAKES for building Petri Net
from snakes.nets import PetriNet, Place, Transition, Value, Expression, Inhibitor
from pyfmi import load_fmu # type: ignore
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# --- Set up the Context Petri Net ---
net = PetriNet('ContextPetriNets')

# Define places
net.add_place(Place('greenSupply_ModeSwitch', [1]))
net.add_place(Place('greenSupply', [1])) 

net.add_place(Place('hybridSupply_ModeSwitch', [1]))
net.add_place(Place('hybridSupply', []))

net.add_place(Place('energySavingMode_ModeSwitch', []))
net.add_place(Place('energySavingMode', [1]))

net.add_place(Place('normalMode_ModeSwitch', [1]))
net.add_place(Place('normalMode', []))

net.add_place(Place('highPerformanceMode_ModeSwitch', [1]))
net.add_place(Place('highPerformanceMode', []))

# Globals for external variables used in guard expressions.
net.globals['hydrogenProduction'] = 0 
net.globals['loadDemand'] = 0  

# Define transitions with guard expressions.
net.add_transition(Transition('Activate_greenSupply', Expression('hydrogenProduction >= loadDemand')))
net.add_transition(Transition('Deactivate_greenSupply', Expression('hydrogenProduction < loadDemand')))

net.add_transition(Transition('Activate_hybridSupply', Expression('hydrogenProduction < loadDemand')))
net.add_transition(Transition('Deactivate_hybridSupply', Expression('hydrogenProduction >= loadDemand')))

net.add_transition(Transition('Activate_energySavingMode', Expression('loadDemand < 150')))
net.add_transition(Transition('Deactivate_energySavingMode', Expression('loadDemand >= 150')))

net.add_transition(Transition('Activate_normalMode', Expression('loadDemand >= 150 and loadDemand < 200')))
net.add_transition(Transition('Deactivate_normalMode', Expression('loadDemand < 150 or loadDemand >= 200')))

net.add_transition(Transition('Activate_highPerformanceMode', Expression('loadDemand >= 200')))
net.add_transition(Transition('Deactivate_highPerformanceMode', Expression('loadDemand < 200')))

# Define input/output arcs using a constant token.
# For energy supply modes:
net.add_input('greenSupply_ModeSwitch', 'Activate_greenSupply', Value(1))
net.add_output('greenSupply', 'Activate_greenSupply', Value(1))
net.add_input('greenSupply', 'Deactivate_greenSupply', Value(1))
net.add_output('greenSupply_ModeSwitch', 'Deactivate_greenSupply', Value(1))

net.add_input('hybridSupply_ModeSwitch', 'Activate_hybridSupply', Value(1))
net.add_output('hybridSupply', 'Activate_hybridSupply', Value(1))
net.add_input('hybridSupply', 'Deactivate_hybridSupply', Value(1))
net.add_output('hybridSupply_ModeSwitch', 'Deactivate_hybridSupply', Value(1))

# For IT operation modes:
net.add_input('energySavingMode_ModeSwitch', 'Activate_energySavingMode', Value(1))
net.add_output('energySavingMode', 'Activate_energySavingMode', Value(1))
net.add_input('energySavingMode', 'Deactivate_energySavingMode', Value(1))
net.add_output('energySavingMode_ModeSwitch', 'Deactivate_energySavingMode', Value(1))

net.add_input('normalMode_ModeSwitch', 'Activate_normalMode', Value(1))
net.add_output('normalMode', 'Activate_normalMode', Value(1))
net.add_input('normalMode', 'Deactivate_normalMode', Value(1))
net.add_output('normalMode_ModeSwitch', 'Deactivate_normalMode', Value(1))

net.add_input('highPerformanceMode_ModeSwitch', 'Activate_highPerformanceMode', Value(1))
net.add_output('highPerformanceMode', 'Activate_highPerformanceMode', Value(1))
net.add_input('highPerformanceMode', 'Deactivate_highPerformanceMode', Value(1))
net.add_output('highPerformanceMode_ModeSwitch', 'Deactivate_highPerformanceMode', Value(1))

# Supply modes - inhibitor arc for mutual exclusivity:
net.add_input('greenSupply', 'Activate_hybridSupply', Inhibitor(Value(1)))
net.add_input('hybridSupply', 'Activate_greenSupply', Inhibitor(Value(1)))

# Operation modes - inhibitor arcs for mutual exclusivity
net.add_input('normalMode', 'Activate_highPerformanceMode', Inhibitor(Value(1)))
net.add_input('energySavingMode', 'Activate_highPerformanceMode', Inhibitor(Value(1)))

net.add_input('highPerformanceMode', 'Activate_normalMode', Inhibitor(Value(1)))
net.add_input('energySavingMode', 'Activate_normalMode', Inhibitor(Value(1)))

net.add_input('highPerformanceMode', 'Activate_energySavingMode', Inhibitor(Value(1)))
net.add_input('normalMode', 'Activate_energySavingMode', Inhibitor(Value(1)))

# reate the additional arcs and transitions for the "requirement" relation
net.add_input('hybridSupply', 'Activate_highPerformanceMode', Value(1))
net.add_output('hybridSupply', 'Activate_highPerformanceMode', Value(1))
net.add_transition(Transition('Deactivate_hybridSupply_duplicate', Expression('hydrogenProduction >= loadDemand')))
net.add_input('hybridSupply', 'Deactivate_hybridSupply_duplicate', Value(1))
net.add_input('highPerformanceMode', 'Deactivate_hybridSupply_duplicate', Value(1))
net.add_input('highPerformanceMode', 'Deactivate_hybridSupply', Inhibitor(Value(1)))

net.add_input('greenSupply', 'Activate_energySavingMode', Value(1))
net.add_output('greenSupply', 'Activate_energySavingMode', Value(1))
net.add_transition(Transition('Deactivate_greenSupply_duplicate', Expression('hydrogenProduction < loadDemand')))
net.add_input('greenSupply', 'Deactivate_greenSupply_duplicate', Value(1))
net.add_input('energySavingMode', 'Deactivate_greenSupply_duplicate', Value(1))
net.add_input('energySavingMode', 'Deactivate_greenSupply', Inhibitor(Value(1)))

# --- Set up the VSS simulation ---
hybridSupply_fmu = load_fmu("ITSystem_hybridSupply.fmu")
greenSupply_fmu = load_fmu("ITSystem_greenSupply.fmu")

hybridSupply_fmu.setup_experiment(start_time=0.0)
hybridSupply_fmu.initialize()
greenSupply_fmu.setup_experiment(start_time=0.0)
greenSupply_fmu.initialize()

# Simulation parameters
step_size = 1
t = 0
t_end = 86400

# Logging Lists
time_log = []
production_log = []
demand_log = []
mode_log = []
supply_log = []
energy_modes_log = []

# --- Helper Function: Safely fire a transition if enabled ---
def safe_fire(transition_name):
    transition = net.transition(transition_name)
    modes = transition.modes()
    if modes:
        binding = modes[0]
        transition.fire(binding)
        print(f"[DEBUG] Fired {transition_name} with binding {binding}")
        return True
    else:
        print(f"[DEBUG] Transition {transition_name} NOT enabled")
    return False

# --- Function to update FMU parameters based on operation mode ---
def apply_operation_mode(fmu):
    if net.place('energySavingMode').tokens:
        fmu.set('cores', 2)
        fmu.set('freq', 2.0)
    elif net.place('normalMode').tokens:
        fmu.set('cores', 4)
        fmu.set('freq', 3.0)
    elif net.place('highPerformanceMode').tokens:
        fmu.set('cores', 8)
        fmu.set('freq', 4.0)
    else:
        fmu.set('cores', 1)
        fmu.set('freq', 1.0)

# --- Function to record supply and energy mode states ---
def record_mode_states():
    # Record supply mode statuses: 1 if tokens exist in corresponding state place.
    green_status = 1 if net.place('greenSupply').tokens else 0
    hybrid_status = 1 if net.place('hybridSupply').tokens else 0
    supply_log.append([green_status, hybrid_status])
    
    # Record IT (energy) mode statuses: 1 if token exists in that place, 0 otherwise.
    saving = 1 if net.place('energySavingMode').tokens else 0
    normal = 1 if net.place('normalMode').tokens else 0
    high   = 1 if net.place('highPerformanceMode').tokens else 0
    energy_modes_log.append([saving, normal, high])

# --- Unified Simulation Function ---
def simulate_mode(fmu, supply_label):
    global t
    # supply_label is either 'greenSupply' or 'hybridSupply'
    while net.place(supply_label).tokens and t < t_end:
        apply_operation_mode(fmu)
        fmu.do_step(current_t=t, step_size=step_size)
        
        # Update globals with FMU values
        hp = fmu.get('hydrogenProduction')
        ld = fmu.get('loadDemand')
        hp_val = hp[0] if isinstance(hp, np.ndarray) else hp
        ld_val = ld[0] if isinstance(ld, np.ndarray) else ld
        net.globals['hydrogenProduction'] = hp_val
        net.globals['loadDemand'] = ld_val
        
        # Log simulation data
        time_log.append(t)
        production_log.append(hp_val)
        demand_log.append(ld_val)
        mode_log.append(supply_label)
        record_mode_states()  # record the supply and energy mode states
        
        print(f"[{t:.2f}] {supply_label} - Prod: {hp_val:.2f}, Demand: {ld_val:.2f}")
        print(f"[STATE] hydrogenProduction: {net.globals['hydrogenProduction']}, loadDemand: {net.globals['loadDemand']}")
        print(f"[DEBUG] Tokens - hybridSupply: {len(net.place('hybridSupply').tokens)}, greenSupply: {len(net.place('greenSupply').tokens)}")
        
        # --- Supply mode switching logic ---
        current_supply = supply_label  # the one whose tokens are active
        other_supply = 'greenSupply' if current_supply == 'hybridSupply' else 'hybridSupply'
        
        # Try deactivating current supply mode, then activating the other supply mode
        if safe_fire(f'Deactivate_{current_supply}'):
            safe_fire(f'Activate_{other_supply}')
        
        # --- Operation mode transitions (for IT/energy modes) ---
        for name in ['Deactivate_energySavingMode', 'Deactivate_normalMode', 'Deactivate_highPerformanceMode']:
            safe_fire(name)
        for name in ['Activate_energySavingMode', 'Activate_normalMode', 'Activate_highPerformanceMode']:
            safe_fire(name)
        
        t += step_size
        print(f"[DEBUG] After cycle: hybridSupply: {net.place('hybridSupply').tokens}, greenSupply: {net.place('greenSupply').tokens}")
    
    if t >= t_end:
        print(f"[STOP] Simulation reached t = {t_end} seconds. Exiting.")

# --- Main Control Loop ---
while (net.place('hybridSupply').tokens or net.place('greenSupply').tokens) and t < t_end:
    if net.place('hybridSupply').tokens:
        simulate_mode(hybridSupply_fmu, 'hybridSupply')
    elif net.place('greenSupply').tokens:
        simulate_mode(greenSupply_fmu, 'greenSupply')
    if not net.place('hybridSupply').tokens and not net.place('greenSupply').tokens:
        print("[STOP] No tokens in either supply state place. Exiting simulation loop.")
        break

# --- Plotting ---
time_log = np.array(time_log)
production_log = np.array(production_log)
demand_log = np.array(demand_log)
mode_log = np.array(mode_log)
supply_log = np.array(supply_log)         # shape: (n_steps, 2)
energy_modes_log = np.array(energy_modes_log)  # shape: (n_steps, 3)

# Combine the five signals: columns 0-1 for supply modes and columns 2-4 for energy modes.
all_modes_log = np.column_stack((
    supply_log[:, 0],
    supply_log[:, 1],
    energy_modes_log[:, 0],
    energy_modes_log[:, 1],
    energy_modes_log[:, 2]
))

time_log_hours = time_log / 3600

# Create a figure with three vertically-stacked subplots.
fig, (ax1, ax2, ax3) = plt.subplots(
    3, 1,
    figsize=(10, 8),
    sharex=True,
    gridspec_kw={'height_ratios': [1, 0.3, 0.3]}
)

# -------------------
# Diagram 1: Hydrogen Production vs Load Demand
ax1.plot(time_log_hours, production_log, label='Hydrogen Production', color='green')
ax1.plot(time_log_hours, demand_log, label='Load Demand', linestyle='--', color='blue')
ax1.set_title('Hydrogen Production vs Load Demand')
ax1.set_ylabel('Values')
ax1.legend()
ax1.grid(True)

# -------------------
# Diagram 2: Energy Supply Modes
ax2.plot(time_log_hours, supply_log[:, 0], label='Green Supply', color='green')
ax2.plot(time_log_hours, supply_log[:, 1], label='Hybrid Supply', color='orange')
ax2.set_title('Energy Supply Modes')
ax2.set_ylabel('Active? (Yes = 1)')
ax2.legend(loc='upper right')
ax2.grid(True)

# -------------------
# Diagram 3: IT Operation Modes
ax3.plot(time_log_hours, energy_modes_log[:, 0], label='Energy Saving', color='green')
ax3.plot(time_log_hours, energy_modes_log[:, 1], label='Normal', color='brown')
ax3.plot(time_log_hours, energy_modes_log[:, 2], label='High Performance', color='red')
ax3.set_title('IT Operation Modes')
ax3.set_ylabel('Active? (Yes = 1)')
ax3.set_xlabel('Time (hours)')
ax3.legend(loc='upper right')
ax3.grid(True)

# Set x-axis to display only integer hours for all subplots
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

# Set only 0 and 1 as y-ticks with integer formatting for ax2 and ax3
for ax in [ax2, ax3]:
    ax.set_yticks([0, 1])
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

plt.tight_layout()
plt.show()

# --- Cleanup ---
hybridSupply_fmu.terminate()
greenSupply_fmu.terminate()