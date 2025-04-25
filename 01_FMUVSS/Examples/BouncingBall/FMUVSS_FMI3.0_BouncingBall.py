import matplotlib.pyplot as plt
from fmpy import read_model_description, extract
from fmpy.fmi3 import FMU3Slave
import shutil

# === Configuration ===
config = {
    'simulation': {
        'initial_time': 0.0,
        'global_stop_time': 10.0,
        'step_size': 1e-4,
        'initial_mode': 'SlidingBall'
    },
    'modes': {
        'SlidingBall': {
            'fmu_path': './model/BallFMI3.0.fmu',
            'monitored_vars': ['y'],  
            'outputs': ['x', 'y', 'der(x)', 'der(y)'],
            'stop_condition': lambda vars: vars['y'] < 10,
            'transition_mapping': {
                'FlyingBall': {'x' : 'x', 'y' : 'h', 'der(x)' : 'vx', 'der(y)' : 'vy'}
            },
            'next_mode': 'FlyingBall',
        },
        'FlyingBall': {
            'fmu_path': './model/FlyingBallFMI3.0.fmu',
            'monitored_vars': ['h', 'r'],
            'outputs': ['x', 'h', 'vx', 'vy'],
            'stop_condition': lambda vars: vars['h'] < vars['r'],
            'transition_mapping': {
                'BouncingBall': {'x' : 'x', 'h' : 'damper.s_rel', 'vx' : 'vx', 'vy' : 'damper.v_rel'}
            },
            'next_mode': 'BouncingBall',
        },
        'BouncingBall': {
            'fmu_path': './model/ContactBallFMI3.0.fmu',
            'monitored_vars': ['mass.s', 'r'],
            'outputs': ['x', 'damper.s_rel', 'vx', 'damper.v_rel'],
            'stop_condition': lambda vars: vars['mass.s'] > vars['r'],
            'transition_mapping': {
                'FlyingBall': {'x' : 'x', 'damper.s_rel' : 'h', 'vx' : 'vx', 'damper.v_rel' : 'vy'}
            },
            'next_mode': 'FlyingBall',
        }
    },
    'plot': {
        'x': 'x',
        'y': 'height',
        'variable_aliases': {
            'height': {
                'SlidingBall': 'y',
                'FlyingBall': 'h',
                'BouncingBall': 'damper.s_rel'
            }
        },
        'title': 'Trajectory',
        'xlabel': 'x',
        'ylabel': 'y',
        'figsize': (6, 6)
    }
}

# === Framework ===
class FMUVSS:
    def __init__(self, config):
        self.sim_cfg = config['simulation']
        self.modes = config['modes']
        self.plot_config = config['plot']
        self.step_size = self.sim_cfg['step_size']
        self.global_stop = self.sim_cfg['global_stop_time']
        self.current_time = self.sim_cfg['initial_time']
        self.current_mode = self.sim_cfg['initial_mode']
        self.results = []  # Each entry is a dictionary for a simulation mode instance.

    def setup_fmu(self, fmu_path, name):
        """Initialize FMU instance and extract model description"""
        md = read_model_description(fmu_path)
        unzip = extract(fmu_path)
        fmu = FMU3Slave(
            guid=md.guid,
            unzipDirectory=unzip,
            modelIdentifier=md.coSimulation.modelIdentifier,
            instanceName=name
        )
        return fmu, unzip, md

    def cleanup_fmu(self, fmu, unzip):
        """Properly terminate and cleanup FMU instance"""
        fmu.terminate()
        fmu.freeInstance()
        shutil.rmtree(unzip)

    def run(self):
        """Main simulation loop with FMI3-specific updates"""
        prev_vals = {}
        while self.current_time < self.global_stop and self.current_mode:
            mode_cfg = self.modes[self.current_mode]
            print(f"Entering mode {self.current_mode} at t={self.current_time:.5f}")
            fmu, unzip, md = self.setup_fmu(mode_cfg['fmu_path'], self.current_mode)
            
            # FMI3 Instantiation with proper parameters
            fmu.instantiate()

            # Create variable reference map with safety checks
            all_names = list(set(
                mode_cfg.get('outputs', []) + 
                mode_cfg.get('monitored_vars', []) +
                list(mode_cfg.get('initial_values', {}).keys()) + 
                list(prev_vals.keys())
            ))
            
            # Create dictionary of all available variables
            var_refs = {v.name: v.valueReference for v in md.modelVariables}
            
            # Map only existing variables
            vr_map = {n: var_refs[n] for n in all_names if n in var_refs}

            # Set initial values and parameters
            for var, val in mode_cfg.get('initial_values', {}).items():
                fmu.setFloat64([vr_map[var]], [val])
            for var, val in prev_vals.items():
                if var in vr_map:
                    fmu.setFloat64([vr_map[var]], [val])

            # FMI3 Initialization sequence
            fmu.enterInitializationMode(
                startTime=self.current_time,
                stopTime=self.global_stop
            )
            fmu.exitInitializationMode()

            # Simulation loop with FMI3 step handling
            mode_time, mode_data = [], {o: [] for o in mode_cfg.get('outputs', [])}
            stop_met = False
            while self.current_time < self.global_stop:
                h = min(self.step_size, self.global_stop - self.current_time)
                fmu.doStep(
                    currentCommunicationPoint=self.current_time,
                    communicationStepSize=h,
                    noSetFMUStatePriorToCurrentPoint=False  # New FMI3 parameter
                )
                self.current_time += h
                mode_time.append(self.current_time)

                # Read outputs
                vals = fmu.getFloat64([vr_map[o] for o in mode_cfg['outputs']])
                for i,o in enumerate(mode_cfg['outputs']):
                    mode_data[o].append(vals[i])

                # Check stop condition
                mon = {v: fmu.getFloat64([vr_map[v]])[0] for v in mode_cfg['monitored_vars']}
                if mode_cfg['stop_condition'](mon):
                    print(f"Exit {self.current_mode} at t={self.current_time:.5f}")
                    stop_met = True
                    break

            # Store results and prepare transition 
            self.results.append({
                'mode': self.current_mode,
                'time': mode_time,
                'data': mode_data,
                'stop_reason': 'condition' if stop_met else 'global'
            })

            # Cleanup and mode transition
            prev_vals = {o: mode_data[o][-1] for o in mode_cfg['outputs']}
            if mode_cfg.get('transition_mapping') and mode_cfg.get('next_mode'):
                mapping = mode_cfg['transition_mapping'].get(mode_cfg['next_mode'], {})
                prev_vals = {mapping.get(k,k): v for k,v in prev_vals.items()}

            self.cleanup_fmu(fmu, unzip)
            self.current_mode = mode_cfg.get('next_mode')

        print(f"Simulation finished at t={self.current_time:.5f}")

    def plot(self):
        """Plot based on config."""
        spec = self.plot_config

        plt.figure(figsize=spec.get('figsize', (8, 6)))
        ax = plt.gca()

        # Assign consistent colors to modes
        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
        unique_modes = list({result['mode'] for result in self.results})
        mode_colors = {mode: color_cycle[i % len(color_cycle)] for i, mode in enumerate(unique_modes)}

        # Resolve variable aliases
        x_concept = spec['x']
        y_concept = spec['y']
        x_aliases = spec.get('variable_aliases', {}).get(x_concept, {})
        y_aliases = spec.get('variable_aliases', {}).get(y_concept, {})

        legend_added = set()

        for mode_result in self.results:
            mode_name = mode_result['mode']
            x_var = x_aliases.get(mode_name, x_concept)
            y_var = y_aliases.get(mode_name, y_concept)

            x_data = mode_result['time'] if x_var == 'time' else mode_result['data'].get(x_var)
            y_data = mode_result['data'].get(y_var)

            if not x_data or not y_data or len(x_data) != len(y_data):
                continue

            label = mode_name if mode_name not in legend_added else None
            ax.plot(x_data, y_data,
                    color=mode_colors[mode_name],
                    label=label)
            if label:
                legend_added.add(mode_name)

        ax.set_xlabel(spec.get('xlabel', x_concept))
        ax.set_ylabel(spec.get('ylabel', y_concept))
        ax.set_title(spec.get('title', ''))
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    simulator = FMUVSS(config)
    simulator.run()
    simulator.plot()
