# ==========================================
# ContextModelica Simulation Framework
# © 2025 Zizhe Wang. All rights reserved.
# ==========================================

import shutil
import matplotlib.pyplot as plt
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
        'greenSupply':      {'initial': 1},
        'hybridSupply':     {'initial': 0},
        'energySavingMode': {'initial': 1},
        'normalMode':       {'initial': 0},
        'highPerformanceMode': {'initial': 0},
    },
    'globals': ['hydrogenProduction', 'loadDemand'],
    'guards': {
        'Activate_greenSupply':   'hydrogenProduction >= loadDemand',
        'Deactivate_greenSupply': 'hydrogenProduction <  loadDemand',
        'Activate_hybridSupply':  'hydrogenProduction <  loadDemand',
        'Deactivate_hybridSupply':'hydrogenProduction >= loadDemand',
        'Activate_energySavingMode':'loadDemand <  150',
        'Deactivate_energySavingMode':'loadDemand >= 150',
        'Activate_normalMode':    'loadDemand >= 150 and loadDemand < 200',
        'Deactivate_normalMode':  'loadDemand < 150 or loadDemand >= 200',
        'Activate_highPerformanceMode':  'loadDemand >= 200',
        'Deactivate_highPerformanceMode':'loadDemand < 200'
    },
    'relations': {
        'exclusion': [
            ['greenSupply','hybridSupply'],
            ['energySavingMode','normalMode','highPerformanceMode']
        ],
        'requirements': [
            ['highPerformanceMode', 'hybridSupply'],
            ['energySavingMode', 'greenSupply']
        ],
        'weak_inclusions': [],
        'strong_inclusions': []
    }
}

sim_cfg = {
    'initial_time': 0.0,
    'stop_time':    86400.0,
    'step_size':    10.0,
    'modes': {
        'greenSupply': {
            'fmu':       'ITSystem_GreenSupply.fmu',
            'outputs':   ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8,'default':1},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0,'default':1.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] < g['loadDemand']
        },
        'hybridSupply': {
            'fmu':       'ITSystem_HybridSupply.fmu',
            'outputs':   ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8,'default':1},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0,'default':1.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] >= g['loadDemand']
        }
    },
    # Mode-specific variable mappings
    'variable_mapping': {
    }
}

plot_cfg = {
    'figure': {
        'figsize': (12, 10),
        'height_ratios': [1, 0.3, 0.3]  # Relative heights of the 3 subplots
    },
    'subplots': [
        {
            'title': 'Hydrogen Production vs Load Demand',
            'ylabel': 'Power (W)',
            'variables': ['hydrogenProduction', 'loadDemand'],  # Variables to plot from logs
            'labels': ['Hydrogen Produced Power', 'Load Demand'],  # Custom labels
            'colors': ['green', 'blue'],
            'linestyles': ['-', '--'],
            'linewidth': 2
        },
        {
            'title': 'Energy Supply Modes',
            'ylabel': 'Active? (Yes=1)',
            'xlabel': None,  # No xlabel for middle subplot
            'type': 'context_states',  # Special type for binary context states
            'contexts': ['greenSupply', 'hybridSupply'],  # Context places to plot
            'labels': ['Green Supply', 'Hybrid Supply'],
            'colors': ['green', 'orange'],
            'linewidth': 2,
            'ylim': (-0.1, 1.1),
            'yticks': [0, 1]
        },
        {
            'title': 'IT Operation Modes',
            'ylabel': 'Active? (Yes=1)',
            'xlabel': 'Time (h)',
            'type': 'context_states',
            'contexts': ['energySavingMode', 'normalMode', 'highPerformanceMode'],
            'labels': ['Energy Saving', 'Normal', 'High Performance'],
            'colors': ['green', 'brown', 'red'],
            'linewidth': 2,
            'ylim': (-0.1, 1.1),
            'yticks': [0, 1]
        }
    ],
    'mode_switches': {
        'show': True,
        'color': 'red',
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
        self.globals = {g:0 for g in cfg['globals']}
        self._build_places(cfg['places'])
        self._build_transitions(cfg['places'], cfg['guards'])
        self._apply_relations(cfg['relations'], cfg['guards'])

    def _build_places(self, places):
        for name, params in places.items():
            init = params['initial']
            self.net.add_place(Place(name, [1] if init == 1 else []))
            self.net.add_place(Place(f"{name}_ModeSwitch", [1] if init == 0 else []))

    def _build_transitions(self, places, guards):
        for name in places:
            act, deact = f"Activate_{name}", f"Deactivate_{name}"
            self.net.add_transition(Transition(act,   Expression(guards[act])))
            self.net.add_transition(Transition(deact, Expression(guards[deact])))
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
            # 1) source activation -> target place
            self.net.add_output(tgt, f"Activate_{src}", Value(1))
            # 2) duplicate source deactivation
            dup = f"Deactivate_{src}_weak_{tgt}"
            guard = guards[f"Deactivate_{src}"]
            self.net.add_transition(Transition(dup, Expression(guard)))
            # 3) source place -> duplicated deactivation
            self.net.add_input(src, dup, Value(1))
            # 4) inhibitor from target place -> duplicated deactivation
            self.net.add_input(tgt, dup, Inhibitor(Value(1)))
            # 5) target place -> original source deactivation
            self.net.add_input(tgt, f"Deactivate_{src}", Value(1))

        # strong inclusions: source strongly includes target
        for src, tgt in rel.get('strong_inclusions', []):
            # 1) target activation -> source place
            self.net.add_output(src, f"Activate_{tgt}", Value(1))
            # 2) duplicate target deactivation
            dup = f"Deactivate_{tgt}_strong_{src}"
            guard = guards[f"Deactivate_{tgt}"]
            self.net.add_transition(Transition(dup, Expression(guard)))
            # 3) inhibitor from source place -> duplicated deactivation
            self.net.add_input(src, dup, Inhibitor(Value(1)))
            # 4) target place -> duplicated deactivation
            self.net.add_input(tgt, dup, Value(1))
            # 5) source place -> original target deactivation
            self.net.add_input(src, f"Deactivate_{tgt}", Value(1))

        # requirements: dependent requires required
        for dep, req in rel.get('requirements', []):
            # 1) req place -> dep activation
            self.net.add_input(req, f"Activate_{dep}", Value(1))
            # 2) dep activation -> req place
            self.net.add_output(req, f"Activate_{dep}", Value(1))
            # 3) duplicate req deactivation
            dup = f"Deactivate_{req}_req_{dep}"
            guard = guards[f"Deactivate_{req}"]
            self.net.add_transition(Transition(dup, Expression(guard)))
            # 4) req place -> duplicated deactivation
            self.net.add_input(req, dup, Value(1))
            # 5) dep place -> duplicated deactivation
            self.net.add_input(dep, dup, Value(1))
            # 6) inhibitor from dep place -> original req deactivation
            self.net.add_input(dep, f"Deactivate_{req}", Inhibitor(Value(1)))

    def fire(self):
        # Update the net's globals with current values
        for key, value in self.globals.items():
            self.net.globals[key] = value
        
        # Keep firing until no more transitions can fire
        fired_any = True
        iteration = 0
        max_iterations = 10
        
        while fired_any and iteration < max_iterations:  # Safety limit
            fired_any = False
            iteration += 1
            
            for t in self.net.transition():
                try:
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
# === 3) FMU Wrapper
# ============================
class FMUInstance:
    def __init__(self, fmu_path, name):
        md = read_model_description(fmu_path)
        unzip = extract(fmu_path)
        self.fmu = FMU3Slave(
            guid=md.guid,
            unzipDirectory=unzip,
            modelIdentifier=md.coSimulation.modelIdentifier,
            instanceName=name
        )
        self.refs = {v.name:v.valueReference for v in md.modelVariables}
        self._unzip = unzip

    def initialize(self, t0, tf):
        self.fmu.instantiate()
        self.fmu.enterInitializationMode(startTime=t0, stopTime=tf)
        self.fmu.exitInitializationMode()

    def do_step(self, t, h):
        self.fmu.doStep(
            currentCommunicationPoint=t,
            communicationStepSize=h,
            noSetFMUStatePriorToCurrentPoint=False
        )

    def read(self, names):
        return self.fmu.getFloat64([self.refs[n] for n in names])

    def write_params(self, rules, petri):
        for pname, rule in rules.items():
            val = rule.get('default')
            for place, v in rule.items():
                if place!='default' and petri.net.place(place).tokens:
                    val = v
                    break
            if val is not None:
                self.fmu.setFloat64([self.refs[pname]], [val])

    def terminate(self):
        self.fmu.terminate()
        self.fmu.freeInstance()
        shutil.rmtree(self._unzip)

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
        self.persistent_vars = {}

    def run(self):
        print(f"Starting simulation: t={self.time}s to t={self.config['stop_time']}s")
        iteration = 0
        current_logged_mode = None
        
        try:
            while self.time < self.config['stop_time']:
                iteration += 1
                
                # Determine the current mode
                mode = next((p.name for p in self.petri.net.place()
                            if p.tokens and p.name in self.config['modes']), None)
                
                if not mode:
                    print("No active mode found. Simulation complete.")
                    break
                
                # Log mode switch only when it changes
                if mode != current_logged_mode:
                    self.logs['mode'].append((self.time, mode))
                    current_logged_mode = mode
                    
                cfg = self.config['modes'][mode]
                fmu = None
                
                try:
                    fmu = FMUInstance(cfg['fmu'], mode)
                    fmu.initialize(self.time, self.config['stop_time'])

                    # Restore persistent variables
                    for var, value in self.persistent_vars.items():
                        mapped_var = self._map_variable(var, mode)
                        if mapped_var in cfg['parameters']:
                            fmu.write_params({mapped_var: {'default': value}}, self.petri)

                    # Run the simulation for the current mode
                    cond = cfg['stop_condition']
                    while self.time < self.config['stop_time'] and not cond(self.petri.globals):
                        fmu.write_params(cfg['parameters'], self.petri)
                        fmu.do_step(self.time, self.config['step_size'])
                        vals = fmu.read(cfg['outputs'])

                        for n,v in zip(cfg['outputs'], vals):
                            self.petri.globals[n]=v
                            self.logs[n].append((self.time, v))
                        
                        self._log_context_states()
                        self.petri.fire()
                        self.time += self.config['step_size']

                    # Save persistent vars
                    for var in cfg['outputs']:
                        mapped_var = self._map_variable(var, mode, reverse=True)
                        self.persistent_vars[mapped_var] = self.petri.globals[var]
                        
                except Exception as e:
                    print(f"Error in mode {mode}: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                finally:
                    if fmu is not None:
                        try:
                            fmu.terminate()
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
        """Log token state (1 or 0) of all context places."""
        plot_cfg = self.config.get('plot_cfg', {})
        subplot_cfgs = plot_cfg.get('subplots', [])

        # Extract all contexts from all subplots that have type 'context_states'
        for sub_cfg in subplot_cfgs:
            if sub_cfg.get('type') == 'context_states':
                contexts = sub_cfg.get('contexts', [])
                for ctx in contexts:
                    state_key = f'{ctx}_state'
                    self.logs[state_key].append(
                        (self.time, 1 if self.petri.net.place(ctx).tokens else 0)
                    )

    def _map_variable(self, var, mode, reverse=False):
        """Map a variable name based on the variable_mapping configuration."""
        mapping = self.config.get('variable_mapping', {})
        if reverse:
            # Reverse mapping: map mode-specific variable back to global variable
            for (src_mode, src_var), (tgt_mode, tgt_var) in mapping.items():
                if tgt_mode == mode and tgt_var == var:
                    return src_var
        else:
            # Forward mapping: map global variable to mode-specific variable
            for (src_mode, src_var), (tgt_mode, tgt_var) in mapping.items():
                if src_mode == mode and src_var == var:
                    return tgt_var
        return var

    def _plot(self):
        if not self.logs:
            print("No data to plot")
            return
        
        plot_cfg = self.config.get('plot_cfg', {})
        if not plot_cfg:
            print("No plot configuration found")
            return
        
        # Get figure settings
        fig_cfg = plot_cfg.get('figure', {})
        figsize = fig_cfg.get('figsize', (12, 10))
        height_ratios = fig_cfg.get('height_ratios', [1, 0.3, 0.3])
        
        # Get subplot configurations
        subplot_cfgs = plot_cfg.get('subplots', [])
        n_subplots = len(subplot_cfgs)
        
        if n_subplots == 0:
            print("[PLOT] No subplots configured")
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(
            n_subplots, 1, 
            figsize=figsize, 
            sharex=True,
            gridspec_kw={'height_ratios': height_ratios[:n_subplots]}
        )
        
        # Make axes iterable even if only one subplot
        if n_subplots == 1:
            axes = [axes]
        
        # Plot each subplot
        for ax, sub_cfg in zip(axes, subplot_cfgs):
            subplot_type = sub_cfg.get('type', 'variables')
            
            if subplot_type == 'context_states':
                # Plot context states (binary token values)
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
                
                # Set y-axis limits and ticks for binary states
                ylim = sub_cfg.get('ylim', (-0.1, 1.1))
                yticks = sub_cfg.get('yticks', [0, 1])
                ax.set_ylim(ylim)
                ax.set_yticks(yticks)
            
            else:
                # Plot regular variables
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
            
            # Set subplot properties
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
        
        # Add mode switch vertical lines
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