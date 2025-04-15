package PendulumFreeflying
model Pendulum
  parameter Real m = 1;  // Bob mass
  parameter Real g = 9.81; // Gravity
  parameter Real L = 2; // Pendulum length

  Real phi(start=0);  // Pendulum angle
  Real dphi(start=2); // Angular velocity
  Real x(start=-2, fixed=true);  // Position (output variable)
  Real y;  // Position (output variable)
  Real dx;  // Velocity in x (output variable)
  Real dy;  // Velocity in y (output variable)
  Real F;  // Force (output variable)

equation
  x = L * sin(phi);
  y = -L * cos(phi);
  dx = der(x);
  dy = der(y);
  dphi = der(phi);
  der(dphi) = -g/L * sin(phi);
  F = m * g * cos(phi) + m * L * dphi^2;

end Pendulum;
model Freeflying
  parameter Real m = 1;  // Bob mass
  parameter Real g = 9.81; // Gravity
  parameter Real L = 2;
  Real x;  // Position
  Real y; // Position
  Real vx;  // Velocity in x
  Real vy;  // Velocity in y
  Real r;

equation
  vx = der(x); // Velocity = derivative of position
  vy = der(y); // Velocity in y
  m * der(vx) = 0; // No force in x
  m * der(vy) = -m * g; // Gravity in y
  r = sqrt(x^2 + y^2);

end Freeflying;
end PendulumFreeflying;
