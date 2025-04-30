

# FMUVSS

This framework enables developers to realize VSS through a user-friendly interface.

Both FMI 2.0 and FMI 3.0 is supported.

## I. How To Use?

Modify the configuration section in `FMUVSS.py` according to your needs, and then run it.

```python
# === Configuration ===
config = {
    'simulation': {
        'initial_time': 0,
        'global_stop_time': 10,
        'step_size': 1e-5,
        'initial_mode': 'SlidingBall'
    },
    'modes': {
        'SlidingBall': {
            'fmu_path': './Ball.fmu',
            'monitored_vars': ['y'],  
            'outputs': ['x', 'y', 'vx', 'vy'],
            'stop_condition': lambda vars: vars['y'] < 10,
            'transition_mapping': {
                'FlyingBall': {'x' : 'x', 'y' : 'h', 'vx' : 'vx', 'vy' : 'vy'}
            },
            'next_mode': 'FlyingBall',
        },
        'FlyingBall': {
            'fmu_path': './FlyingBall.fmu',
            'monitored_vars': ['h', 'r'],
            'outputs': ['x', 'h', 'vx', 'vy'],
            'stop_condition': lambda vars: vars['h'] < vars['r'],
            'transition_mapping': {
                'BouncingBall': {'x' : 'x', 'h' : 'h', 'vx' : 'vx', 'vy' : 'v'}
            },
            'next_mode': 'BouncingBall',
        },
        'BouncingBall': {
            'fmu_path': './ContactBall.fmu',
            'monitored_vars': ['mass.s', 'r'],
            'outputs': ['x', 'h', 'vx', 'v'],
            'stop_condition': lambda vars: vars['mass.s'] > vars['r'],
            'transition_mapping': {
                'FlyingBall': {'x' : 'x', 'h' : 'h', 'vx' : 'vx', 'v' : 'vy'}
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
                'BouncingBall': 'h'
            }
        },
        'title': 'Trajectory',
        'xlabel': 'x',
        'ylabel': 'y',
        'figsize': (6, 6)
    }
}
```

## II. Examples

#### 1. Pendulum-Freeflying

![Trajectory](./Examples/Pendulum/Trajectory.png)

#### 2. SlidingBall-FlyingBall-BouncingBall

![Trajectory](./Examples/BouncingBall/result_BouncingBall_trajectory.png)

#### 3. Rocket-Satellite-SatelliteChange

![Trajectory](./Examples/Satellite/trajectory.png)

## III. Performance Evaluation: FMUVSS vs DySMo

### 1. Comparison

#### FMUVSS

| VSS Model   | Time (s) | Notes             |
| ----------- | -------- | ----------------- |
| Pendulum    | 0.75     | Pre-compiled FMUs |
| SlidingBall | 4.29     | Pre-compiled FMUs |
| Clutch      | 2.43     | Pre-compiled FMUs |

#### DySMo

| VSS Model   | Time (s) | Compilation Time (s)                                         | Time Excl. Compilation (s) |
| ----------- | -------- | ------------------------------------------------------------ | -------------------------- |
| Pendulum    | 72.3     | Mode 1: 4.99, Mode 2: 4.93 \| **Total: 9.92**                | 62.38                      |
| SlidingBall | 440.8    | Mode 1: 4.99, Mode 2: 4.86, Mode 3: 4.93 \| **Total: 14.78** | 426.02                     |
| Clutch      | 349.92   | Mode 1: 5.22, Mode 2: 5.30 \| **Total: 10.52**               | 339.4                      |

#### Summary

| VSS Model   | Framework | Time  (s) | Speed Gain |
| ----------- | --------- | --------- | ---------- |
| Pendulum    | FMUVSS    | 0.75      | 98.80%     |
|             | DySMo     | 62.38     |            |
| SlidingBall | FMUVSS    | 4.29      | 99.03%     |
|             | DySMo     | 440.8     |            |
| Clutch      | FMUVSS    | 2.43      | 99.28%     |
|             | DySMo     | 339.4     |            |

### 2. Profiling using cProfile

#### Pendulum VSS

FMUVSS:

```
558267 function calls (557966 primitive calls) in 0.750 seconds

Ordered by: cumulative time
List reduced from 420 to 10 due to restriction <10>

ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1    0.084    0.084    0.750    0.750 FMUVSS_FMI3.0_Pendulum.py:71(run)
     2    0.000    0.000    0.318    0.159 FMUVSS_FMI3.0_Pendulum.py:53(setup_fmu)
 51157    0.118    0.000    0.210    0.000 fmi3.py:612(getFloat64)
     2    0.000    0.000    0.176    0.088 fmi3.py:950(__init__)
     2    0.000    0.000    0.176    0.088 fmi3.py:84(__init__)
     2    0.000    0.000    0.173    0.087 fmi1.py:126(__init__)
     2    0.000    0.000    0.173    0.087 __init__.py:459(LoadLibrary)
     2    0.000    0.000    0.173    0.087 __init__.py:343(__init__)
     2    0.173    0.086    0.173    0.086 {built-in method _ctypes.LoadLibrary}
 72219    0.132    0.000    0.132    0.000 fmi3.py:494(w)
```

DySMo:

```
199185644 function calls (199162744 primitive calls) in 72.304 seconds

Ordered by: cumulative time
List reduced from 3401 to 20 due to restriction <20>

  ncalls  tottime  percall  cumtime  percall filename:lineno(function)
   413/1    0.004    0.000   72.305   72.305 {built-in method builtins.exec}
       1    0.065    0.065   72.305   72.305 DySMo.py:1(<module>)
       1    0.079    0.079   71.250   71.250 VSM.py:248(simulate)
       2    0.000    0.000   57.832   28.916 Mode.py:148(read_last_result)
       2    0.388    0.194   57.832   28.916 Mode.py:151(read_result)
       2   10.133    5.067   57.444   28.722 ModelicaTool.py:46(ReadResult)
       2    0.000    0.000   39.448   19.724 Mat.py:129(Load)
      12    0.000    0.000   39.436    3.286 Mat.py:46(__ReadMatrix)
      12    9.980    0.832   32.108    2.676 Mat.py:70(__ReadMatrixData)
28269516   10.972    0.000   19.362    0.000 Mat.py:75(__ReadMatrixDataEntry)
       4    0.001    0.000   12.170    3.042 Platform.py:33(Execute)
       4    0.000    0.000   12.149    3.037 subprocess.py:1259(wait)
       4    0.000    0.000   12.149    3.037 subprocess.py:1580(_wait)
       4   12.148    3.037   12.148    3.037 {built-in method _winapi.WaitForSingleObject}
       2    0.000    0.000    9.992    4.996 VSM.py:54(__compileMode)
       2    0.000    0.000    9.924    4.962 Mode.py:45(compile)
       2    0.001    0.000    9.924    4.962 OpenModelica.py:153(Compile)
       8    3.966    0.496    7.327    0.916 Matrix.py:28(__init__)
       6    0.000    0.000    7.327    1.221 Mat.py:113(AddMatrix)
56596834    6.934    0.000    6.934    0.000 {method 'append' of 'list' objects}
```

| **Factor**            | FMUVSS                           | DySMo                                 |
| --------------------- | -------------------------------- | ------------------------------------- |
| **Total Runtime**     | 0.75 seconds                     | 62.38 seconds (**83× slower**)        |
| **Function Calls**    | 558267 calls                     | 199185644 calls (**356× more calls**) |
| **Data Handling**     | Zero-copy via FMI binary buffers | **19.36s** text parsing (`Mat.py:75`) |
| **Memory Management** | Preallocated native arrays       | **6.93s** list growth (`list.append`) |
| **Tool Integration**  | Direct C API calls               | **12.15s** subprocess/IPC latency     |

#### SlidingBall

FMUVSS:

```
2702075 function calls (2701761 primitive calls) in 4.285 seconds

Ordered by: cumulative time
List reduced from 422 to 10 due to restriction <10>

ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1    0.394    0.394    4.285    4.285 FMUVSS_FMI3.0_BouncingBall.py:94(run)
    15    0.004    0.000    2.191    0.146 FMUVSS_FMI3.0_BouncingBall.py:76(setup_fmu)
    15    0.000    0.000    1.383    0.092 fmi3.py:950(__init__)
    15    0.001    0.000    1.383    0.092 fmi3.py:84(__init__)
    15    0.000    0.000    1.364    0.091 fmi1.py:126(__init__)
    15    0.000    0.000    1.362    0.091 __init__.py:459(LoadLibrary)
    15    0.000    0.000    1.361    0.091 __init__.py:343(__init__)
    15    1.361    0.091    1.361    0.091 {built-in method _ctypes.LoadLibrary}
255030    0.576    0.000    1.011    0.000 fmi3.py:612(getFloat64)
    15    0.001    0.000    0.658    0.044 __init__.py:178(extract)
```

DySMo:

```
1197226277 function calls (1197194994 primitive calls) in 440.795 seconds

Ordered by: cumulative time
List reduced from 3417 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    413/1    0.004    0.000  440.797  440.797 {built-in method builtins.exec}
        1    0.048    0.048  440.797  440.797 DySMo.py:1(<module>)
        1    1.191    1.191  439.721  439.721 VSM.py:248(simulate)
       15    0.000    0.000  258.298   17.220 Mode.py:148(read_last_result)
       15    2.000    0.133  258.298   17.220 Mode.py:151(read_result)
       15   48.368    3.225  256.298   17.087 ModelicaTool.py:46(ReadResult)
       15    0.000    0.000  172.517   11.501 Mat.py:129(Load)
       90    0.001    0.000  172.426    1.916 Mat.py:46(__ReadMatrix)
        1   54.570   54.570  153.680  153.680 VSM.py:151(__save_observer)
       90   44.451    0.494  141.235    1.569 Mat.py:70(__ReadMatrixData)
125639400   48.000    0.000   83.836    0.000 Mat.py:75(__ReadMatrixDataEntry)
       61   28.618    0.469   47.429    0.778 Matrix.py:28(__init__)
       46    0.000    0.000   47.428    1.031 Mat.py:113(AddMatrix)
        1    0.000    0.000   45.923   45.923 Mat.py:140(Write)
        1    9.189    9.189   45.923   45.923 Matrix.py:88(Write)
329385536   41.082    0.000   41.082    0.000 {method 'append' of 'list' objects}
 30000150    9.608    0.000   36.734    0.000 Matrix.py:43(__WriteValue)
 30000150   14.138    0.000   27.125    0.000 OutputStream.py:47(WriteFloat64)
       18    0.001    0.000   24.389    1.355 Platform.py:33(Execute)
       18    0.000    0.000   24.332    1.352 subprocess.py:1259(wait)
```

### 3. Summary

| Factor               | **FMUVSS**                     | **DySMo**                                   |
| -------------------- | ------------------------------ | ------------------------------------------- |
| **Model Format**     | FMU (compiled C/C++ binary)    | Compiled Modelica binary                    |
| **Model Execution**  | Direct via FMI C API           | Indirect via subprocess                     |
| **Data Handling**    | Zero-copy binary buffers       | Text-based `.mat` file parsing              |
| **Function Calls**   | Fewer, via native interface    | Many, with Python overhead                  |
| **Matrix Access**    | Binary memory access           | Parsed from text files                      |
| **Memory Use**       | Preallocated arrays            | Dynamic list growth                         |
| **Process Overhead** | Low (in-memory/shared library) | High (file I/O + IPC latency)               |
| **Python’s Role**    | Lightweight coordinator        | Heavyweight orchestrator & data transformer |

> ✅ FMUVSS leverages FMI binary protocols and native memory handling.  
> ❌ DySMo incurs overhead from interpreted logic and text-based I/O.

* DySMo is slow because it relies heavily on Python interpretation, text-based file parsing, and high-overhead interprocess communication instead of direct binary access and native execution.

* FMUVSS outperforms DySMo by minimizing Python overhead and file I/O through direct binary access via the FMI standard.