# ContextModelica

Define your configurations in `ContextModelica.py`, then execute: `python ContextModelica.py`

## Example

`context_cfg` defines the contexts and their logic 
`sim_cfg` maps modes to FMUs and parameters

```python
context_cfg = {
    'places': {
        'greenSupply':  {'initial': 1},
        'hybridSupply': {'initial': 0},
        'energySavingMode': {'initial': 1},
        'normalMode':       {'initial': 0},
        'highPerformanceMode': {'initial': 0},
    },
    'globals': ['hydrogenProduction', 'loadDemand'],
    'guards': {
        # Supply switching
        'Activate_greenSupply':   'hydrogenProduction >= loadDemand',
        'Activate_hybridSupply':  'hydrogenProduction < loadDemand',
        # Performance mode switching
        'Activate_energySavingMode': 'loadDemand < 150',
        'Activate_normalMode':       '150 <= loadDemand < 200',
        'Activate_highPerformanceMode': 'loadDemand >= 200',
    },
    'relations': {
        'exclusion': [
            ['greenSupply','hybridSupply'],
            ['energySavingMode','normalMode','highPerformanceMode']
        ],
        'requirements': [
            ['highPerformanceMode', 'hybridSupply'],
            ['energySavingMode', 'greenSupply']
        ]
    }
}

sim_cfg = {
    'initial_time': 0.0,
    'stop_time': 86400.0,
    'step_size': 1.0,
    'modes': {
        'greenSupply': {
            'fmu': 'ITSystem_greenSupply.fmu',
            'outputs': ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] < g['loadDemand']
        },
        'hybridSupply': {
            'fmu': 'ITSystem_hybridSupply.fmu',
            'outputs': ['hydrogenProduction','loadDemand'],
            'parameters': {
                'cores': {'energySavingMode':2,'normalMode':4,'highPerformanceMode':8},
                'freq':  {'energySavingMode':2.0,'normalMode':3.0,'highPerformanceMode':4.0}
            },
            'stop_condition': lambda g: g['hydrogenProduction'] >= g['loadDemand']
        }
    }
}
```