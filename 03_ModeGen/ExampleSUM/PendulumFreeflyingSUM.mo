/*# 
  MODEL-METADATA:
    Modes: [pendulum, freeflying]
    Shared: [m, g]
#*/

model PendulumFreeflyingSUM
  //# [all]
  parameter Real m = 1; // Bob mass
  parameter Real g = 9.81; // Gravity
  Real y;

  //# [pendulum]
  parameter Real L = 2; // Pendulum length

  //# [pendulum]
  Real phi(start=0);
  Real dphi(start=2);
  Real x(start=-2);
  Real dx, dy;
  Real F; 
  
  //# [freeflying]
  Real x;  
  Real vx, vy;

@#equation
  //# [pendulum]
  x = L * sin(phi);
  y = -L * cos(phi);
  dx = der(x);
  dy = der(y);
  dphi = der(phi);
  der(dphi) = -g/L * sin(phi);
  F = m * g * cos(phi) + m * L * dphi^2;
  
  //# [freeflying]
  vx = der(x);
  vy = der(y);
  m * der(vx) = 0;
  m * der(vy) = -m * g;