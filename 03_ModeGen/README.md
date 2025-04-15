# ModeGen

**ModeGen** is a tool for generating mode-specific Modelica submodels (VSS models) from a **SUM** (Single Underlying Model), a supermodel that contains all components. It extracts relevant components based on **mode annotations** and creates separate submodels for each mode.

## Example (Pendulum - FreeFlying)

#### Step 1: Write VSS SUM with Metadata & Annotation
```modelica
/*# 
  MODEL-METADATA:
    Modes: [Pendulum, Freeflying]
    Shared: [m, g, y]
#*/

model PendulumFreeflyingSUM
  //# [All]
  parameter Real m = 1; // Bob mass
  parameter Real g = 9.81; // Gravity
  Real y;

  //# [Pendulum]
  parameter Real L = 2; // Pendulum length

  //# [Pendulum]
  Real phi(start=0);
  Real dphi(start=2);
  Real x(start=-2);
  Real dx;
  Real dy;
  Real F;
  
  //# [Freeflying]
  Real x;  
  Real vx;
  Real vy;

@#equation
  //# [Pendulum]
  x = L * sin(phi);
  y = -L * cos(phi);
  dx = der(x);
  dy = der(y);
  dphi = der(phi);
  der(dphi) = -g/L * sin(phi);
  F = m * g * cos(phi) + m * L * dphi^2;
  
  //# [Freeflying]
  vx = der(x);
  vy = der(y);
  m * der(vx) = 0;
  m * der(vy) = -m * g;
```

#### Step 2: Feed into VSSCompositor
```
python -m ModeGen.cli ./ModeGen/ExampleSUM/PendulumFreeflyingSUM.mo --check
```

-> Submodels are generated automatically
-> Submodels are automatically checked using the OpenModelica compiler

You can see the process in the terminal:

```
Processing PendulumFreeflyingSUM.mo
2 submodels are generated

Model checking results:
Calling OpenModelica compiler for model checking
Running command: omc ModeGen\SUM\generated\PendulumFreeflyingSUM_pendulum.mo
  ✓ PendulumFreeflyingSUM_pendulum.mo (PASS)
Calling OpenModelica compiler for model checking
Running command: omc ModeGen\SUM\generated\PendulumFreeflyingSUM_freeflying.mo
  ✓ PendulumFreeflyingSUM_freeflying.mo (PASS)

FINAL RESULT: ALL MODES PASS
```

The two submodels have been generated and successfully checked:

```modelica
model PendulumFreeflyingSUM_pendulum
  Real phi(start=0);
  Real dphi(start=-2);
  parameter Real m = 1;
  parameter Real g = 9.81;
  parameter Real L = 2;
  Real x, y, dx, dy;
equation 
  x = L * sin(phi); 
  y = -L * cos(phi); 
  dx = der(x); 
  dy = der(y); 
  dphi = der(phi); 
  der(dphi) = -g/L * sin(phi); 
end PendulumFreeflyingSUM_pendulum;
model PendulumFreeflyingSUM_freeflying
  Real x(start=2); 
  Real y(start=-2); 
  Real vx(start=1); 
  Real vy(start=0); 
  parameter Real m = 1; 
  parameter Real g = 9.81;
equation 
  vx = der(x); 
  vy = der(y);
  m * der(vx) = 0; 
  m * der(vy) = -m * g;
end PendulumFreeflyingSUM_freeflying; 
```

More examples: `ModeGen/SUM`
