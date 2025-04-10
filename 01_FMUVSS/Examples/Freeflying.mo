model FreeflyingFMI2
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

end FreeflyingFMI2;
