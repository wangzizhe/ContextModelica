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