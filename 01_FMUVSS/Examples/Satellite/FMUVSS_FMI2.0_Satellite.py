from pyfmi import load_fmu # type: ignore
import numpy as np
import matplotlib.pyplot as plt

# === Configuration ===
config = {
    'simulation': {
        'initial_time': 0,
        'global_stop_time': 100000,
        'step_size': 0.01,
        'initial_mode': 'PlanetRocket'
    },
    'modes': {
        'PlanetRocket': {
            'fmu_path': './model/PlanetRocketFMI2.0.fmu',
            'monitored_vars': ['actualTime'],  
            'outputs': ['rocket.x', 'rocket.height', 'rocket.vx', 'rocket.vy', 'rocket.v'],
            'stop_condition': lambda vars: vars['actualTime'] > 480,
            'transition_mapping': {
                'PlanetSatellite': {
                    'rocket.height' : 'satellite.y', 
                    'rocket.x' : 'satellite.x', 
                    'rocket.vx' : 'satellite.vx', 
                    'rocket.vy' : 'satellite.vy'}
            },
            'next_mode': 'PlanetSatellite',
        },
        'PlanetSatellite': {
            'fmu_path': './model/PlanetSatelliteFMI2.0.fmu',
            'monitored_vars': ['satellite.loops'],
            'outputs': ['satellite.x', 'satellite.y', 'satellite.vx', 'satellite.vy', 'satellite.v'],
            'stop_condition': lambda vars: vars['satellite.loops'] == 5,
            'transition_mapping': {
                'PlanetSatelliteChange': {
                    'satellite.y':'satellite.y', 
                    'satellite.x': 'satellite.x', 
                    'satellite.vx': 'satellite.vx', 
                    'satellite.vy': 'satellite.vy'}
            },
            'next_mode': 'PlanetSatelliteChange',
        },
        'PlanetSatelliteChange': {
            'fmu_path': './model/PlanetSatelliteChangeFMI2.0.fmu',
            'monitored_vars': ['currentTime', 'initialTime'],
            'outputs': ['satellite.x', 'satellite.y', 'satellite.vx', 'satellite.vy', 'satellite.v'],
            'stop_condition': lambda vars: vars['currentTime'] - vars['initialTime'] >= 50,
            'transition_mapping': {
                'PlanetSatellite': {
                    'satellite.y':'satellite.y', 
                    'satellite.x': 'satellite.x', 
                    'satellite.vx': 'satellite.vx', 
                    'satellite.vy': 'satellite.vy'}
            },
            'next_mode': 'PlanetSatellite',
        }
    },
    'plot': {  
        'x': 'x',
        'y': 'h',
        'variable_aliases': {
            # 'time': {
            #     'PlanetRocket': 'actualTime',
            #     'PlanetSatellite': 'time',
            #     'PlanetSatelliteChange': 'currentTime'
            # },
            'x': {
                'PlanetRocket': 'rocket.x',
                'PlanetSatellite': 'satellite.x',
                'PlanetSatelliteChange': 'satellite.x'
            },
            'h': { 
                'PlanetRocket': 'rocket.height',
                'PlanetSatellite': 'satellite.y',
                'PlanetSatelliteChange': 'satellite.y'
            },
        },
        'title': 'Trajectory',
        'xlabel': 'X Position',
        'ylabel': 'Altitude',
        'figsize': (6, 6)
    }
}

# === Framework ===
class FMUVSS:
    def __init__(self, config):
        self.sim_config = config['simulation']
        self.modes = config['modes']
        self.plot_config = config['plot']
        self.step_size = self.sim_config.get('step_size')
        self.global_stop_time = self.sim_config.get('global_stop_time')
        self.current_time = self.sim_config.get('initial_time')
        self.current_mode_key = self.sim_config.get('initial_mode')
        self.results = []  # Each entry is a dictionary for a simulation mode instance.

    def _get_parameters(self, fmu):
        """Returns a dictionary of parameter values from the FMU."""
        params = {}
        model_vars = fmu.get_model_variables()
        for name, var in model_vars.items():
            if var.causality == 'parameter':
                val = fmu.get(name)
                params[name] = val[0] if isinstance(val, np.ndarray) else val
        return params

    def run(self):
        """Run the simulation based on the state machine until global stop time is reached."""
        print(f"Starting simulation. Global stop time = {self.global_stop_time}s")
        previous_final_vals = {}

        while self.current_time < self.global_stop_time and self.current_mode_key is not None:
            mode_config = self.modes[self.current_mode_key]
            print(f"Entering mode '{self.current_mode_key}' at t = {self.current_time:.2f}s")
            fmu = load_fmu(mode_config['fmu_path'])
            fmu.setup_experiment(start_time=self.current_time)
            
            # Retrieve FMU parameters (if any)
            mode_params = self._get_parameters(fmu)
            
            # Set any initial values from config for this mode.
            for var, value in mode_config.get('initial_values', {}).items():
                fmu.set(var, value)
            
            # If coming from a previous mode, use the previously remapped outputs.
            if previous_final_vals:
                for var, value in previous_final_vals.items():
                    fmu.set(var, value)
            
            fmu.initialize()

            mode_time = []
            mode_data = {var: [] for var in mode_config.get('outputs', [])}
            stop_met = False

            # Run simulation for this mode until stop condition is met or until global time is reached.
            while self.current_time < self.global_stop_time:
                current_step = min(self.step_size, self.global_stop_time - self.current_time)
                fmu.do_step(current_t=self.current_time, step_size=current_step)
                self.current_time += current_step
                mode_time.append(self.current_time)

                # Collect outputs for this mode at *every* step
                for var in mode_config.get('outputs', []):
                    val = fmu.get(var)
                    mode_data[var].append(val[0] if isinstance(val, np.ndarray) else val)

                # Collect monitored vars to check stop condition
                current_vars = dict(mode_params)
                for var in mode_config.get('monitored_vars', []):
                    val = fmu.get(var)
                    current_vars[var] = val[0] if isinstance(val, np.ndarray) else val

                if mode_config['stop_condition'](current_vars):
                    stop_met = True
                    print(f"Mode '{self.current_mode_key}' stop condition met at t = {self.current_time:.3f}s")
                    break

            # After finishing the mode, retrieve final outputs (and parameter values) for transition.
            previous_final_vals = {}
            for var in mode_config.get('outputs', []):
                val = fmu.get(var)
                previous_final_vals[var] = val[0] if isinstance(val, np.ndarray) else val
            previous_final_vals.update(mode_params)
            
            # Save the mode results.
            self.results.append({
                'mode': self.current_mode_key,
                'time': mode_time,
                'data': mode_data,
                'stop_time': self.current_time,
                'stop_reason': 'condition_met' if stop_met else 'global_stop'
            })
            fmu.terminate()

            # Determine the next mode.
            next_mode = mode_config.get('next_mode')

            # Apply the transition mapping from the leaving mode if defined.
            if next_mode and 'transition_mapping' in mode_config:
                mapping_dict = mode_config['transition_mapping'].get(next_mode)
                if mapping_dict is not None:
                    mapped_vals = {}
                    # If the mapping_dict is empty, pass variables as is.
                    if mapping_dict == {}:
                        mapped_vals = previous_final_vals
                    else:
                        for curr_var, next_var in mapping_dict.items():
                            if curr_var in previous_final_vals:
                                mapped_vals[next_var] = previous_final_vals[curr_var]
                            else:
                                raise ValueError(f"Expected variable '{curr_var}' not found for transition from '{self.current_mode_key}' to '{next_mode}'")
                    previous_final_vals = mapped_vals

            # If next_mode is callable, invoke it to determine the next mode key.
            if callable(next_mode):
                self.current_mode_key = next_mode(previous_final_vals)
            else:
                self.current_mode_key = next_mode

            if self.current_mode_key is None:
                print("No next mode defined. Stopping simulation.")
                break

        print(f"Simulation finished at t = {self.current_time:.3f}s")

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

# === Launch Simulation ===
if __name__ == '__main__':
    simulator = FMUVSS(config)
    simulator.run()
    simulator.plot()