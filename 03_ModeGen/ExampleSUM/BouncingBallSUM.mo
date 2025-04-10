/*# 
  MODEL-METADATA:
    Modes: [ContactBall, FlyingBall]
    Shared: [r, g, v]
#*/

model BouncingBallSUM
    //# [ContactBall]
    import Modelica.Units.SI.*;

    //# [all]
    parameter Real r = 1;
    parameter Real g = 9.81;
    Real v;

    //# [ContactBall]
    parameter Real m = 1;
    parameter Real c = 1e3; // Translational spring constant
    parameter Real d = 0.6e1; // Translational damping constant
    Real h;
  
    //# [FlyingBall]
    Real h(start=20);

    //# [ContactBall]
    Modelica.Mechanics.Translational.Components.Fixed fixed
      annotation (Placement(transformation(extent={{-10,-86},{10,-66}})));
    Modelica.Mechanics.Translational.Components.Spring spring(s_rel0=r, c=c)
      annotation (Placement(transformation(extent={{-10,-10},{10,10}}, rotation=90,origin={-20,-50})));
    Modelica.Mechanics.Translational.Components.Mass mass(m=m)
      annotation (Placement(transformation(extent={{-10,-10},{10,10}}, rotation=90,origin={0,-10})));
    Modelica.Mechanics.Translational.Components.Damper damper(d=d)
      annotation (Placement(transformation(extent={{-10,-10},{10,10}}, rotation=90,origin={20,-50})));
    Modelica.Mechanics.Translational.Sources.Force force 
      annotation (Placement(transformation(extent={{-10,-10},{10,10}}, rotation=270,origin={0,28})));
    Modelica.Blocks.Sources.Constant const(k=-m*g)
      annotation (Placement(transformation(extent={{-60,60},{-40,80}})));

@#equation
    //# [ContactBall]
    h = damper.s_rel * 1;
    v = damper.v_rel * 1;

    //# [ContactBall]
    connect(const.y, force.f) annotation(
        Line(points = {{-38, 70}, {0, 70}, {0, 40}}, color = {0, 0, 127}));
    connect(force.flange, mass.flange_b) annotation(
        Line(points = {{0, 18}, {0, 0}}, color = {0, 127, 0}));
    connect(mass.flange_a, spring.flange_b) annotation(
        Line(points = {{0, -20}, {-20, -20}, {-20, -40}}, color = {0, 127, 0}));
    connect(spring.flange_a, fixed.flange) annotation(
        Line(points = {{-20, -60}, {0, -60}, {0, -76}}, color = {0, 127, 0}));
    connect(mass.flange_a, damper.flange_b) annotation(
        Line(points = {{0, -20}, {20, -20}, {20, -40}}, color = {0, 127, 0}));
    connect(damper.flange_a, fixed.flange) annotation(
        Line(points = {{20, -60}, {0, -60}, {0, -76}}, color = {0, 127, 0}));

    //# [FlyingBall]
    der(h) = v;
    der(v) = -g;

//# [all]
annotation (uses(Modelica(version="4.0.0")));