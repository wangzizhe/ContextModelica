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
    'step_size':    1.0,
    'modes': {
        'greenSupply': {
            'fmu':       'ITSystem_greenSupply.fmu',
            'outputs':   ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8,'default':1},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0,'default':1.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] < g['loadDemand']
        },
        'hybridSupply': {
            'fmu':       'ITSystem_hybridSupply.fmu',
            'outputs':   ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8,'default':1},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0,'default':1.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] >= g['loadDemand']
        }
    }
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
            self.net.add_place(Place(name, [init]))
            self.net.add_place(Place(f"{name}_ModeSwitch", [1-init]))

    def _build_transitions(self, places, guards):
        for name in places:
            act, deact = f"Activate_{name}", f"Deactivate_{name}"
            self.net.add_transition(Transition(act,   Expression(guards[act])))
            self.net.add_transition(Transition(deact, Expression(guards[deact])))
            # wire mode-switch arcs
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
        for t in self.net.transition():
            if t.firable():
                t.fire()

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
    def __init__(self, context_cfg, sim_cfg):
        self.petri = ContextPetriNet(context_cfg)
        self.config = sim_cfg
        self.time = sim_cfg['initial_time']
        self.logs = defaultdict(list)

    def run(self):
        while self.time < self.config['stop_time']:
            mode = next((p.name for p in self.petri.net.place()
                         if p.tokens and p.name in self.config['modes']), None)
            if not mode:
                break
            cfg = self.config['modes'][mode]
            fmu = FMUInstance(cfg['fmu'], mode)
            fmu.initialize(self.time, self.config['stop_time'])
            cond = cfg['stop_condition']
            while self.time<self.config['stop_time'] and not cond(self.petri.globals):
                fmu.write_params(cfg['parameters'], self.petri)
                fmu.do_step(self.time, self.config['step_size'])
                vals = fmu.read(cfg['outputs'])
                for n,v in zip(cfg['outputs'], vals):
                    self.petri.globals[n]=v
                    self.logs[n].append((self.time, v))
                self.logs['mode'].append((self.time, mode))
                self.petri.fire()
                self.time += self.config['step_size']
            fmu.terminate()
        self._plot()

    def _plot(self):
        plt.figure(figsize=(10,6))
        for k,series in self.logs.items():
            if k=='mode': continue
            times = [t/3600 for t,_ in series]
            vals  = [v    for _,v in series]
            plt.plot(times, vals, label=k)
        for t,m in self.logs['mode']:
            plt.axvline(t/3600, color='k', linestyle='--', alpha=0.3)
        plt.legend(); plt.xlabel('Time (h)'); plt.ylabel('Value'); plt.grid(True); plt.tight_layout(); plt.show()

# ============================
# === 5) Main Execution
# ============================
if __name__=='__main__':
    engine = SimulationEngine(context_cfg, sim_cfg)
    engine.run()
