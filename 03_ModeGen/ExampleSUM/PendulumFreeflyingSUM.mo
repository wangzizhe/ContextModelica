/*# 
  MODEL-METADATA:
    Modes: [pendulum, freeflying]
    Shared: [m, g]
#*/

model PendulumFreeflyingSUM
  //# [all]
  parameter Real m = 1; // Bob mass
  parameter Real g = 9.81; // Gravity

  //# [pendulum]
  parameter Real L = 2; // Pendulum length

  //# [pendulum]
  Real phi(start=0); // Pendulum angle
  Real dphi(start=-2); // Angular velocity
  Real x; // Position
  Real y; // Position
  Real dx; // Velocity
  Real dy; // Velocity
  Real F; 
  
  //# [freeflying]
  Real x(start=2);  
  Real y(start=-2);
  Real vx(start=1);
  Real vy(start=0);

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
  vx = der(x); // Velocity = derivative of position
  vy = der(y); // Velocity in y
  m * der(vx) = 0; // No force in x
  m * der(vy) = -m * g; // Gravity in y