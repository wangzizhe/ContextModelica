# ==========================================
# ContextModelica Simulation Framework
# © 2025 Zizhe Wang. All rights reserved.
# ==========================================

import shutil
import matplotlib.pyplot as plt
import re
from collections import defaultdict
from itertools import permutations
from snakes.nets import PetriNet, Place, Transition, Expression, Inhibitor, Value
from fmpy import read_model_description, extract
from fmpy.fmi3 import FMU3Slave

# ============================
# === 1) User Configuration
# ============================
context_cfg = {
    'places': {
        # NormalOperation+ExcessPower+ElectrolyzerActive+H2SafetyMonitor
        'H2SafetyMonitor':      {'initial': 0},
        # NormalOperation+ExcessPower+ElectrolyzerActive
        'ElectrolyzerActive':      {'initial': 0},
        'NormalOperation+ExcessPower':      {'initial': 0},
        'NormalOperation+DeficitPower':    {'initial': 0},
        'EmergencyMode+ExcessPower':      {'initial': 0},
        'EmergencyMode+DeficitPower':     {'initial': 1},
    },
    'globals': ['battery.SOC', 'h2Tank.mass', 'netPower'],
    'guards': {
        # If left undefined, the deactivation transition will be auto-generated as 'not Activation Transition'.
        'Activate_H2SafetyMonitor':     
            'battery.SOC > 0.3 and h2Tank.mass < 1 and netPower > 0',
        'Activate_ElectrolyzerActive':     
            'battery.SOC > 0.3 and h2Tank.mass < 1 and netPower > 0',
        'Activate_NormalOperation+ExcessPower':     
            'battery.SOC > 0.3 and netPower > 0',
        'Activate_NormalOperation+DeficitPower':     
            'battery.SOC > 0.3 and netPower < 0',
        'Activate_EmergencyMode+ExcessPower':     
            'battery.SOC < 0.3 and netPower > 0',
        'Activate_EmergencyMode+DeficitPower':     
            'battery.SOC <= 0.3 and netPower <= 0',
    },
    'auto_generate_deactivation': True,  # Enable auto-generation
    'relations': {
        'exclusion': [
            [],
        ],
        'requirements': [
            ['ElectrolyzerActive', 'NormalOperation+ExcessPower'],
            ['H2SafetyMonitor', 'NormalOperation+ExcessPower'],
        ],
        'weak_inclusions': [
            ['ElectrolyzerActive', 'H2SafetyMonitor']
        ],
        'strong_inclusions': []
    }
}

sim_cfg = {
    'initial_time': 0.0,
    'stop_time':    72000.0,
    'step_size':    10.0,
    'modes': {
        'H2SafetyMonitor': {
            'fmu':     'EnergySystem_Variant2.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
        'ElectrolyzerActive': {
            'fmu':     'EnergySystem_Variant2.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
        'NormalOperation+ExcessPower': {
            'fmu':     'EnergySystem_Variant3.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
        'NormalOperation+DeficitPower': {
            'fmu':     'EnergySystem_Variant1.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
        'EmergencyMode+ExcessPower': {
            'fmu':     'EnergySystem_Variant3.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
        'EmergencyMode+DeficitPower': {
            'fmu':     'EnergySystem.fmu',
            'outputs': ['battery.SOC', 'h2Tank.mass', 'netPower'],
            'parameters': {},
        },
    },
    'variable_mapping': {}
}

plot_cfg = {
    # Context groups definition
    'context_groups': {
        'NormalOperation': [
            'H2SafetyMonitor',
            'ElectrolyzerActive',
            'NormalOperation+ExcessPower',
            'NormalOperation+DeficitPower'
        ],
        'EmergencyMode': [
            'EmergencyMode+ExcessPower',
            'EmergencyMode+DeficitPower'
        ]
    },
    
    'figure': {
        'figsize': (10, 15),
        'height_ratios': [1, 1, 0.3, 0.3]  # 4 subplots
    },
    'subplots': [
        # Subplot 1: Battery SOC and H2 Tank Mass
        {
            'title': 'Battery and Hydrogen Storage',
            'ylabel': 'Storage Level',
            'variables': ['battery.SOC', 'h2Tank.mass'],
            'labels': ['Battery SOC (%)', 'H2 Tank Mass (kg)'],
            'colors': ['green', 'orange'],
            'linestyles': ['-', '--'],
            'linewidth': 2
        },
        # Subplot 2: Net Power
        {
            'title': 'Net Power',
            'ylabel': 'Power (kW)',
            'variables': ['netPower'],
            'labels': ['Net Power'],
            'colors': ['blue'],
            'linestyles': ['-'],
            'linewidth': 2
        },
        # Subplot 3: Normal Operation vs Emergency Mode (AGGREGATED)
        {
            'title': 'Context: Operation Modes',
            'ylabel': 'Active? (Yes=1)',
            'xlabel': None,
            'type': 'context_states',
            'aggregate': True, 
            'contexts': [
                'NormalOperation',    # Parent names (not the full context names)
                'EmergencyMode'
            ],
            'labels': [
                'Normal Operation',
                'Emergency Mode'
            ],
            'colors': [
                'green',
                'red'
            ],
            'linewidth': 2,
            'ylim': (-0.1, 1.1),
            'yticks': [0, 1]
        },
        # Subplot 4: Electrolyzer Active and H2 Safety Monitor
        {
            'title': 'Context: Electrolyzer and H2 Safety Monitor',
            'ylabel': 'Active? (Yes=1)',
            'xlabel': 'Time (h)',
            'type': 'context_states',
            'aggregate': False,  # Individual contexts
            'contexts': [
                'ElectrolyzerActive',
                'H2SafetyMonitor'
            ],
            'labels': [
                'Electrolyzer Active',
                'H2 Safety Monitor Active'
            ],
            'colors': [
                'purple',
                'magenta'
            ],
            'linewidth': 2,
            'ylim': (-0.1, 1.1),
            'yticks': [0, 1]
        }
    ],
    'mode_switches': {
        'show': True,
        'color': 'gray',
        'linestyle': '--',
        'alpha': 0.3,
        'linewidth': 1
    },
    'grid': True,
    'legend_loc': 'best'
}

# ============================
# === 2) Petri Net Builder
# ============================
class ContextPetriNet:
    def __init__(self, cfg):
        self.net = PetriNet('ContextPetriNet')
        self.globals = {g: 0 for g in cfg['globals']}
        
        # Auto-generate deactivation guards if enabled
        self.guards = cfg['guards'].copy()
        if cfg.get('auto_generate_deactivation', False):
            self._auto_generate_deactivation_guards(cfg['guards'])
        
        self._build_places(cfg['places'])
        self._build_transitions(cfg['places'], self.guards)
        self._apply_relations(cfg['relations'], self.guards)
    
    def _auto_generate_deactivation_guards(self, guards):
        """Auto-generate deactivation guards as negations of activation guards."""
        for guard_name, guard_expr in guards.items():
            if guard_name.startswith('Activate_'):
                context_name = guard_name[9:]
                deactivate_name = f'Deactivate_{context_name}'
                
                if deactivate_name not in guards:
                    negated_expr = negate_guard_expression(guard_expr)
                    self.guards[deactivate_name] = negated_expr
                    print(f"Auto-generated: {deactivate_name} = {negated_expr}")

    def _preprocess_guard(self, guard_str):
        """
        Convert variable names with dots to dictionary access.
        Example: 'battery.SOC > 0.2' -> 'globals["battery.SOC"] > 0.2'
        """
        # Match variable names: letters, numbers, dots, underscores
        # But not numeric literals like '0.2'
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_.]*)\b'
        
        def replace_var(match):
            var_name = match.group(1)
            # Don't replace Python keywords
            keywords = ('and', 'or', 'not', 'True', 'False', 'None', 'in', 'is')
            if var_name in keywords:
                return var_name
            # If it's in our globals or contains a dot, replace with dictionary access
            if var_name in self.globals or '.' in var_name:
                return f'__globals__["{var_name}"]'
            return var_name
        
        preprocessed = re.sub(pattern, replace_var, guard_str)
        return preprocessed

    def _build_places(self, places):
        for name, params in places.items():
            init = params['initial']
            self.net.add_place(Place(name, [1] if init == 1 else []))
            self.net.add_place(Place(f"{name}_ModeSwitch", [1] if init == 0 else []))

    def _build_transitions(self, places, guards):
        for name in places:
            act, deact = f"Activate_{name}", f"Deactivate_{name}"
            # Preprocess guard expressions to handle dots
            act_guard = self._preprocess_guard(guards[act])
            deact_guard = self._preprocess_guard(guards[deact])
            
            self.net.add_transition(Transition(act, Expression(act_guard)))
            self.net.add_transition(Transition(deact, Expression(deact_guard)))
            self.net.add_input(f"{name}_ModeSwitch", act, Value(1))
            self.net.add_output(name, act, Value(1))
            self.net.add_input(name, deact, Value(1))
            self.net.add_output(f"{name}_ModeSwitch", deact, Value(1))

    def _apply_relations(self, rel, guards):
        # exclusion via mutual exclusion inhibitor arcs
        for group in rel.get('exclusion', []):
            for a, b in permutations(group, 2):
                self.net.add_input(b, f"Activate_{a}", Inhibitor(Value(1)))

        # weak inclusions: source weakly includes target
        for src, tgt in rel.get('weak_inclusions', []):
            self.net.add_output(tgt, f"Activate_{src}", Value(1))
            dup = f"Deactivate_{src}_weak_{tgt}"
            guard = self._preprocess_guard(guards[f"Deactivate_{src}"])
            self.net.add_transition(Transition(dup, Expression(guard)))
            self.net.add_input(src, dup, Value(1))
            self.net.add_input(tgt, dup, Inhibitor(Value(1)))
            self.net.add_input(tgt, f"Deactivate_{src}", Value(1))

        # strong inclusions: source strongly includes target
        for src, tgt in rel.get('strong_inclusions', []):
            self.net.add_output(src, f"Activate_{tgt}", Value(1))
            dup = f"Deactivate_{tgt}_strong_{src}"
            guard = self._preprocess_guard(guards[f"Deactivate_{tgt}"])
            self.net.add_transition(Transition(dup, Expression(guard)))
            self.net.add_input(src, dup, Inhibitor(Value(1)))
            self.net.add_input(tgt, dup, Value(1))
            self.net.add_input(src, f"Deactivate_{tgt}", Value(1))

        # requirements: dependent requires required
        for dep, req in rel.get('requirements', []):
            self.net.add_input(req, f"Activate_{dep}", Value(1))
            self.net.add_output(req, f"Activate_{dep}", Value(1))
            dup = f"Deactivate_{req}_req_{dep}"
            guard = self._preprocess_guard(guards[f"Deactivate_{req}"])
            self.net.add_transition(Transition(dup, Expression(guard)))
            self.net.add_input(req, dup, Value(1))
            self.net.add_input(dep, dup, Value(1))
            self.net.add_input(dep, f"Deactivate_{req}", Inhibitor(Value(1)))

    def fire(self):
        # Update the net's global namespace
        # SNAKES accesses globals through the net.globals dictionary
        for key, value in self.globals.items():
            self.net.globals[key] = value
        
        # Also create __globals__ for the preprocessed guards
        self.net.globals['__globals__'] = dict(self.globals)
        
        # Keep firing until no more transitions can fire
        fired_any = True
        iteration = 0
        max_iterations = 10
        
        while fired_any and iteration < max_iterations:
            fired_any = False
            iteration += 1
            
            for t in self.net.transition():
                try:
                    # modes() will use net.globals automatically
                    modes = t.modes()
                    modes_list = list(modes)
                    
                    if modes_list:
                        t.fire(modes_list[0])
                        fired_any = True
                        break
                except Exception:
                    continue

        if iteration >= max_iterations:
            print(f"Warning: fire() reached maximum iterations ({max_iterations})")

# ============================
# === 3.1) FMU Instance Helper
# ============================
class FMUInstance:
    def __init__(self, fmu_path, mode_name):
        self._unzip = extract(fmu_path)
        self._desc = read_model_description(self._unzip)
        self.fmu = FMU3Slave(
            guid=self._desc.guid,
            unzipDirectory=self._unzip,
            modelIdentifier=self._desc.coSimulation.modelIdentifier,
            instanceName=f"FMU_{mode_name}"
        )
        
        # Build value reference map
        self.refs = {}
        for var in self._desc.modelVariables:
            self.refs[var.name] = var.valueReference

# ============================
# === 3.2) Helper Functions for Auto-Generation
# ============================
def negate_guard_expression(expr):
    """Convert a guard expression to its logical negation."""
    def parse_expression(expr):
        expr = expr.strip()
        if expr.startswith('(') and expr.endswith(')'):
            depth = 0
            for i, char in enumerate(expr):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                if depth == 0 and i < len(expr) - 1:
                    break
            if i == len(expr) - 1:
                return parse_expression(expr[1:-1])
        
        depth = 0
        for op in [' or ', ' and ']:
            for i in range(len(expr)):
                if expr[i] == '(':
                    depth += 1
                elif expr[i] == ')':
                    depth -= 1
                elif depth == 0 and expr[i:i+len(op)] == op:
                    left = expr[:i]
                    right = expr[i+len(op):]
                    return ('or' if op == ' or ' else 'and', 
                           parse_expression(left), 
                           parse_expression(right))
        return ('atom', expr)
    
    def negate_tree(tree):
        if tree[0] == 'atom':
            atom = tree[1].strip()
            for op, neg_op in [('>=', '<'), ('>', '<='), ('<=', '>'), ('<', '>='), ('==', '!='), ('!=', '==')]:
                if op in atom:
                    parts = atom.split(op, 1)
                    if len(parts) == 2:
                        return ('atom', f'{parts[0].strip()} {neg_op} {parts[1].strip()}')
            return ('atom', f'not ({atom})')
        elif tree[0] == 'and':
            return ('or', negate_tree(tree[1]), negate_tree(tree[2]))
        elif tree[0] == 'or':
            return ('and', negate_tree(tree[1]), negate_tree(tree[2]))
    
    def tree_to_string(tree, parent_op=None):
        if tree[0] == 'atom':
            return tree[1]
        elif tree[0] in ('and', 'or'):
            left = tree_to_string(tree[1], tree[0])
            right = tree_to_string(tree[2], tree[0])
            result = f'{left} {tree[0]} {right}'
            if parent_op is not None and parent_op != tree[0]:
                result = f'({result})'
            return result
    
    tree = parse_expression(expr)
    negated_tree = negate_tree(tree)
    result = tree_to_string(negated_tree)
    return result

def guard_to_lambda(guard_expr, global_vars):
    """Convert a guard expression string to a lambda function."""
    modified_expr = guard_expr
    # Use the actual global variables defined in config
    for var in global_vars:
        modified_expr = modified_expr.replace(var, f"g['{var}']")
    return eval(f"lambda g: {modified_expr}")

# ============================
# === 4) Simulation Engine
# ============================
class SimulationEngine:
    def __init__(self, context_cfg, sim_cfg, plot_cfg):
        self.petri = ContextPetriNet(context_cfg)
        self.config = sim_cfg
        self.config['plot_cfg'] = plot_cfg
        self.time = sim_cfg['initial_time']
        self.logs = defaultdict(list)
        self.prev_vals = {}
        
        # Auto-generate stop conditions from deactivation guards
        for mode_name in sim_cfg['modes'].keys():
            if 'stop_condition' not in sim_cfg['modes'][mode_name]:
                deactivate_guard_name = f'Deactivate_{mode_name}'
                if deactivate_guard_name in self.petri.guards:
                    guard_expr = self.petri.guards[deactivate_guard_name]
                    # Pass the global variables from config
                    sim_cfg['modes'][mode_name]['stop_condition'] = guard_to_lambda(
                        guard_expr, 
                        context_cfg['globals']
                    )
                    print(f"Auto-generated stop_condition for {mode_name}: {guard_expr}")

    def run(self):
        print(f"Starting simulation: t={self.time}s to t={self.config['stop_time']}s")
        iteration = 0
        current_logged_mode = None

        # Safety parameters
        MAX_ITER = 5_000_000
        STUCK_LIMIT = 1
        last_globals_snapshot = dict(self.petri.globals)
        last_token_snapshot = {p.name: bool(p.tokens) for p in self.petri.net.place()}
        stuck_counter = 0

        try:
            while self.time < self.config['stop_time']:
                iteration += 1
                if iteration > MAX_ITER:
                    print(f"Aborting: reached MAX_ITER = {MAX_ITER}")
                    break

                # Determine the current mode
                mode = next((p.name for p in self.petri.net.place()
                            if p.tokens and p.name in self.config['modes']), None)

                if not mode:
                    print("No active mode found. Simulation complete.")
                    break

                # Mode change logging
                if mode != current_logged_mode:
                    print(f"[{iteration}] Mode switched to: {mode} at t={self.time:.1f}s")
                    self.logs['mode'].append((self.time, mode))
                    current_logged_mode = mode

                cfg = self.config['modes'][mode]

                # Check stop_condition before creating FMU
                cond = cfg['stop_condition']
                try:
                    cond_now = bool(cond(self.petri.globals))
                except Exception as e:
                    print(f"Error evaluating stop_condition for mode {mode}: {e}")
                    cond_now = False

                if cond_now:
                    # Mode should end immediately - save values and fire Petri net
                    for var in cfg.get('outputs', []):
                        self.prev_vals[var] = self.petri.globals.get(var)
                    
                    prev_tokens = {p.name: bool(p.tokens) for p in self.petri.net.place()}
                    self.petri.fire()
                    new_tokens = {p.name: bool(p.tokens) for p in self.petri.net.place()}
                    
                    if prev_tokens == new_tokens:
                        stuck_counter += 1
                        if stuck_counter >= STUCK_LIMIT:
                            raise RuntimeError(f"Stuck trying to exit mode '{mode}' at t={self.time}: no token changes.")
                    else:
                        stuck_counter = 0
                    continue

                # Create and initialize FMU
                fmu = None
                try:
                    fmu = FMUInstance(cfg['fmu'], mode)
                    fmu.fmu.instantiate()

                    # Set initial values from previous mode (before initialization)
                    if self.prev_vals:
                        print(f"  Restoring {len(self.prev_vals)} variable(s) from previous mode")
                        for var in cfg.get('outputs', []):
                            if var in self.prev_vals and var in fmu.refs:
                                fmu.fmu.setFloat64([fmu.refs[var]], [self.prev_vals[var]])

                    # Initialize FMU
                    fmu.fmu.enterInitializationMode(
                        startTime=self.time,
                        stopTime=self.config['stop_time']
                    )
                    fmu.fmu.exitInitializationMode()

                    # Simulation loop
                    inner_iter = 0
                    while self.time < self.config['stop_time'] and not cond(self.petri.globals):
                        inner_iter += 1

                        # Execute simulation step
                        step = self.config['step_size']
                        if step <= 0:
                            raise ValueError("step_size must be > 0")
                        
                        fmu.fmu.doStep(
                            currentCommunicationPoint=self.time,
                            communicationStepSize=step,
                            noSetFMUStatePriorToCurrentPoint=False
                        )
                        
                        # Read and log outputs
                        vals = fmu.fmu.getFloat64([fmu.refs[n] for n in cfg.get('outputs', [])])
                        for n, v in zip(cfg.get('outputs', []), vals):
                            self.petri.globals[n] = v
                            self.logs[n].append((self.time, v))

                        # Periodic progress logging
                        if inner_iter % 100 == 0:
                            status = ', '.join([f"{k}={v:.4f}" for k, v in self.petri.globals.items()])
                            print(f"  [t={self.time:.1f}s] {status}")

                        # Log context states and fire Petri net transitions
                        self._log_context_states()
                        prev_tokens = {p.name: bool(p.tokens) for p in self.petri.net.place()}
                        self.petri.fire()
                        new_tokens = {p.name: bool(p.tokens) for p in self.petri.net.place()}

                        # Advance time
                        prev_time = self.time
                        self.time += step

                        # Progress detection (prevent infinite loops)
                        globals_changed = any(self.petri.globals.get(k) != last_globals_snapshot.get(k)
                                            for k in self.petri.globals)
                        tokens_changed = (new_tokens != last_token_snapshot) or (prev_tokens != new_tokens)

                        if globals_changed or tokens_changed or (self.time != prev_time):
                            stuck_counter = 0
                            last_globals_snapshot = dict(self.petri.globals)
                            last_token_snapshot = new_tokens
                        else:
                            stuck_counter += 1
                            if stuck_counter >= STUCK_LIMIT:
                                raise RuntimeError(f"Simulation appears stuck at t={self.time}: no changes detected.")

                    # Save values on normal exit from mode
                    for var in cfg.get('outputs', []):
                        self.prev_vals[var] = self.petri.globals.get(var)

                except Exception as e:
                    print(f"Error in mode {mode}: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                finally:
                    # Cleanup FMU resources
                    if fmu is not None:
                        try:
                            fmu.fmu.terminate()
                            fmu.fmu.freeInstance()
                            shutil.rmtree(fmu._unzip)
                        except Exception as e:
                            print(f"Error terminating FMU: {e}")

        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        except Exception as e:
            print(f"Simulation error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"Simulation finished at t={self.time/3600:.2f}h")
            self._plot()

    def _log_context_states(self):
        """Log token state (1 or 0) of all context places, including aggregated states."""
        plot_cfg = self.config.get('plot_cfg', {})
        subplot_cfgs = plot_cfg.get('subplots', [])
        context_groups = plot_cfg.get('context_groups', {})

        for sub_cfg in subplot_cfgs:
            if sub_cfg.get('type') == 'context_states':
                # Check if this subplot uses aggregation
                if sub_cfg.get('aggregate', False):
                    # For aggregated subplots, log parent context states
                    contexts = sub_cfg.get('contexts', [])
                    for parent_ctx in contexts:
                        # Get children from context_groups
                        children = context_groups.get(parent_ctx, [])
                        # Check if ANY child context is active
                        is_any_child_active = any(
                            self.petri.net.place(child).tokens 
                            for child in children 
                            if child in [p.name for p in self.petri.net.place()]
                        )
                        state_key = f'{parent_ctx}_state'
                        self.logs[state_key].append((self.time, 1 if is_any_child_active else 0))
                else:
                    # For non-aggregated subplots, log individual context states
                    contexts = sub_cfg.get('contexts', [])
                    for ctx in contexts:
                        state_key = f'{ctx}_state'
                        try:
                            self.logs[state_key].append(
                                (self.time, 1 if self.petri.net.place(ctx).tokens else 0)
                            )
                        except Exception:
                            # Context doesn't exist, skip
                            pass
                    
    def _plot(self):
        if not self.logs:
            print("No data to plot")
            return
        
        plot_cfg = self.config.get('plot_cfg', {})
        if not plot_cfg:
            print("No plot configuration found")
            return
        
        fig_cfg = plot_cfg.get('figure', {})
        figsize = fig_cfg.get('figsize', (12, 10))
        height_ratios = fig_cfg.get('height_ratios', [1, 0.3, 0.3])
        
        subplot_cfgs = plot_cfg.get('subplots', [])
        n_subplots = len(subplot_cfgs)
        
        if n_subplots == 0:
            print("[PLOT] No subplots configured")
            return
        
        fig, axes = plt.subplots(
            n_subplots, 1, 
            figsize=figsize, 
            sharex=True,
            gridspec_kw={'height_ratios': height_ratios[:n_subplots]}
        )
        
        if n_subplots == 1:
            axes = [axes]
        
        for ax, sub_cfg in zip(axes, subplot_cfgs):
            subplot_type = sub_cfg.get('type', 'variables')
            
            if subplot_type == 'context_states':
                contexts = sub_cfg.get('contexts', [])
                labels = sub_cfg.get('labels', contexts)
                colors = sub_cfg.get('colors', ['blue'] * len(contexts))
                linewidth = sub_cfg.get('linewidth', 2)
                
                for ctx, label, color in zip(contexts, labels, colors):
                    state_key = f'{ctx}_state'
                    if state_key in self.logs and self.logs[state_key]:
                        times = [t/3600 for t, _ in self.logs[state_key]]
                        states = [s for _, s in self.logs[state_key]]
                        ax.plot(times, states, label=label, linewidth=linewidth, 
                            color=color, drawstyle='steps-post')
                
                ylim = sub_cfg.get('ylim', (-0.1, 1.1))
                yticks = sub_cfg.get('yticks', [0, 1])
                ax.set_ylim(ylim)
                ax.set_yticks(yticks)
            
            else:
                variables = sub_cfg.get('variables', [])
                labels = sub_cfg.get('labels', variables)
                colors = sub_cfg.get('colors', ['blue'] * len(variables))
                linestyles = sub_cfg.get('linestyles', ['-'] * len(variables))
                linewidth = sub_cfg.get('linewidth', 2)
                
                for var, label, color, linestyle in zip(variables, labels, colors, linestyles):
                    if var in self.logs and self.logs[var]:
                        times = [t/3600 for t, _ in self.logs[var]]
                        vals = [v for _, v in self.logs[var]]
                        ax.plot(times, vals, label=label, linewidth=linewidth,
                            color=color, linestyle=linestyle)
            
            title = sub_cfg.get('title', '')
            ylabel = sub_cfg.get('ylabel', '')
            xlabel = sub_cfg.get('xlabel', None)
            
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=10)
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=10)
            
            legend_loc = plot_cfg.get('legend_loc', 'best')
            ax.legend(loc=legend_loc)
            
            if plot_cfg.get('grid', True):
                ax.grid(True, alpha=0.3)
        
        mode_switch_cfg = plot_cfg.get('mode_switches', {})
        if mode_switch_cfg.get('show', True):
            mode_data = self.logs.get('mode', [])
            for t, _ in mode_data:
                for ax in axes:
                    ax.axvline(
                        t/3600,
                        color=mode_switch_cfg.get('color', 'red'),
                        linestyle=mode_switch_cfg.get('linestyle', '--'),
                        alpha=mode_switch_cfg.get('alpha', 0.3),
                        linewidth=mode_switch_cfg.get('linewidth', 1)
                    )
        
        plt.tight_layout()
        print("Displaying plot...")
        plt.show()

# ============================
# === 5) Main Execution
# ============================
if __name__=='__main__':
    engine = SimulationEngine(context_cfg, sim_cfg, plot_cfg)
    engine.run()