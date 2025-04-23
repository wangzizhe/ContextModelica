model ITSystem
  "A simple IT system that generates hydrogen based on hourly input, adjusting energy supply and CPU usage through various modes (hybrid, green, high-performance, normal, energy-saving) to meet varying load demands."

  // Hydrogen production
  Modelica.Blocks.Tables.CombiTable1Ds hydrogenTable(
    table = [
      0, 0.0; 3600, 0.0; 7200, 0.0; 10800, 0.0;
      14400, 0.0; 18000, 0.0; 21600, 0.0; 25200, 0.0;
      28800, 50.0; 32400, 70.0; 36000, 90.0; 39600, 120.0;
      43200, 150.0; 46800, 180.0; 50400, 250.0; 54000, 250.0;
      57600, 250.0; 61200, 250.0; 64800, 150.0; 68400, 100.0;
      72000, 0.0; 75600, 0.0; 79200, 0.0; 82800, 0.0],
    columns = {1,2});
    // smoothness = Modelica.Blocks.Types.Smoothness.ConstantSegments,
    // extrapolation = Modelica.Blocks.Types.Extrapolation.HoldLastPoint);

  // Load demand
  Modelica.Blocks.Tables.CombiTable1Ds loadTable(
    table = [
      0, 0.0; 3600, 0.0; 7200, 0.0; 10800, 0.0;
      14400, 0.0; 18000, 0.0; 21600, 0.0; 25200, 0.0;
      28800, 30.0; 32400, 50.0; 36000, 70.0; 39600, 100.0;
      43200, 120.0; 46800, 150.0; 50400, 200.0; 54000, 250.0;
      57600, 300.0; 61200, 350.0; 64800, 300.0; 68400, 200.0;
      72000, 0.0; 75600, 0.0; 79200, 0.0; 82800, 0.0],
    columns = {1,2});
    // smoothness = Modelica.Blocks.Types.Smoothness.ConstantSegments,
    // extrapolation = Modelica.Blocks.Types.Extrapolation.HoldLastPoint);

  // Energy & Performance Parameters
  parameter Real corePowerFactor = 10.0;
  parameter Real frequencyPowerFactor = 5.0;
  parameter Real gridPower = 100.0;
  
  // CPU mode-dependent parameters
  parameter Integer cores_high = 4;
  parameter Integer cores_balanced = 2;
  parameter Integer cores_saving = 1;
  parameter Real freq_high = 3.0;
  parameter Real freq_balanced = 2.0;
  parameter Real freq_saving = 1.0;

  // System state variables
  Real hydrogenProduction "Hydrogen supplied";
  Real loadDemand "Current system load demand";
  Real totalEnergySupply;

  // CPU control variables
  Integer activeCores;
  Real cpuFrequency;
  
  // hybridSupply state
  PNlib.Components.PD hybridSupply(nIn = 2, nOut = 4);
  PNlib.Components.T hybridSupply_activate(firingCon = (hydrogenProduction < loadDemand and hybridSupply.t == 0), nIn = 1, nOut = 1);
  PNlib.Components.T hybridSupply_deactivate(firingCon = (hydrogenProduction >= loadDemand), nIn = 2);
  
  // greenSupply state
  PNlib.Components.PD greenSupply(nIn = 1, nOut = 2, maxTokens = 1);
  PNlib.Components.T greenSupply_activate(firingCon = (hydrogenProduction >= loadDemand), nIn = 1, nOut = 1);
  PNlib.Components.T greenSupply_deactivate(firingCon = (hydrogenProduction < loadDemand), nIn = 1);

  // highPerformanceMode
  PNlib.Components.PD highPerformanceMode(nIn = 1, nOut = 5, maxTokens = 1);
  PNlib.Components.T highPerformanceMode_activate(firingCon = (loadDemand > 200), nIn = 3, nOut = 2);
  PNlib.Components.T highPerformanceMode_deactivate(firingCon = (loadDemand < 200), nIn = 1);

  // normalMode
  PNlib.Components.PD normalMode(nIn = 1, nOut = 3, maxTokens = 1);
  PNlib.Components.T normalMode_activate(firingCon = (loadDemand > 150 and loadDemand < 200), nIn = 2, nOut = 1);
  PNlib.Components.T normalMode_deactivate(firingCon = (loadDemand < 150 or loadDemand > 200), nIn = 1);

  // energySavingMode
  PNlib.Components.PD energySavingMode(nIn = 1, nOut = 3, maxTokens = 1);
  PNlib.Components.T energySavingMode_activate(firingCon = (loadDemand < 150), nIn = 2, nOut = 1);
  PNlib.Components.T energySavingMode_deactivate(firingCon = (loadDemand > 150), nIn = 1);

  // Context Petri Nets
  PNlib.Components.IA IA_highPerformanceMode_normalMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_highPerformanceMode_energySavingMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_normalMode_highPerformanceMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_normalMode_energySavingMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_energySavingMode_highPerformanceMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_energySavingMode_normalMode_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_hybridSupply_greenSupply_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_greenSupply_hybridSupply_exclusion_1 annotation(HideResult=true);
  PNlib.Components.IA IA_hybridSupply_highPerformanceMode_requirement_1 annotation(HideResult=true);
  PNlib.Components.T hybridSupply_deactivate_highPerformanceMode_1(firingCon = (hydrogenProduction >= loadDemand), nIn = 2, nOut = 0);

equation
  // Assign hydrogen production and load demand from tables
  hydrogenTable.u = time;
  hydrogenProduction = hydrogenTable.y[2];
  
  loadTable.u = time;
  loadDemand = loadTable.y[2];
  
  // Compute total available energy supply
  totalEnergySupply = if hybridSupply.t > 0 then (hydrogenProduction + gridPower) else hydrogenProduction;
  
  // Determine active CPU cores and frequency based on performance mode
  activeCores = if highPerformanceMode.t > 0 then cores_high elseif normalMode.t > 0 then cores_balanced else cores_saving;
  cpuFrequency = if highPerformanceMode.t > 0 then freq_high elseif normalMode.t > 0 then freq_balanced else freq_saving;
  
  // Petri Nets connections  
  connect(hybridSupply_activate.outPlaces[1], hybridSupply.inTransition[1]);
  connect(hybridSupply.outTransition[1], hybridSupply_deactivate.inPlaces[1]);
  connect(greenSupply_activate.outPlaces[1], greenSupply.inTransition[1]);
  connect(greenSupply.outTransition[1], greenSupply_deactivate.inPlaces[1]);
  connect(highPerformanceMode_activate.outPlaces[1], highPerformanceMode.inTransition[1]);
  connect(highPerformanceMode.outTransition[1], highPerformanceMode_deactivate.inPlaces[1]);
  connect(normalMode_activate.outPlaces[1], normalMode.inTransition[1]);
  connect(normalMode.outTransition[1], normalMode_deactivate.inPlaces[1]);
  connect(energySavingMode_activate.outPlaces[1], energySavingMode.inTransition[1]);
  connect(energySavingMode.outTransition[1], energySavingMode_deactivate.inPlaces[1]);
  connect(highPerformanceMode.outTransition[2], IA_highPerformanceMode_normalMode_exclusion_1.inPlace);
  connect(IA_highPerformanceMode_normalMode_exclusion_1.outTransition, normalMode_activate.inPlaces[1]);
  connect(highPerformanceMode.outTransition[3], IA_highPerformanceMode_energySavingMode_exclusion_1.inPlace);
  connect(IA_highPerformanceMode_energySavingMode_exclusion_1.outTransition, energySavingMode_activate.inPlaces[1]);
  connect(normalMode.outTransition[2], IA_normalMode_highPerformanceMode_exclusion_1.inPlace);
  connect(IA_normalMode_highPerformanceMode_exclusion_1.outTransition, highPerformanceMode_activate.inPlaces[1]);
  connect(normalMode.outTransition[3], IA_normalMode_energySavingMode_exclusion_1.inPlace);
  connect(IA_normalMode_energySavingMode_exclusion_1.outTransition, energySavingMode_activate.inPlaces[2]);
  connect(energySavingMode.outTransition[2], IA_energySavingMode_highPerformanceMode_exclusion_1.inPlace);
  connect(IA_energySavingMode_highPerformanceMode_exclusion_1.outTransition, highPerformanceMode_activate.inPlaces[2]);
  connect(energySavingMode.outTransition[3], IA_energySavingMode_normalMode_exclusion_1.inPlace);
  connect(IA_energySavingMode_normalMode_exclusion_1.outTransition, normalMode_activate.inPlaces[2]);
  connect(hybridSupply.outTransition[2], IA_hybridSupply_greenSupply_exclusion_1.inPlace);
  connect(IA_hybridSupply_greenSupply_exclusion_1.outTransition, greenSupply_activate.inPlaces[1]);
  connect(greenSupply.outTransition[2], IA_greenSupply_hybridSupply_exclusion_1.inPlace);
  connect(IA_greenSupply_hybridSupply_exclusion_1.outTransition, hybridSupply_activate.inPlaces[1]);
  connect(hybridSupply.outTransition[3], highPerformanceMode_activate.inPlaces[3]);
  connect(hybridSupply.outTransition[4], hybridSupply_deactivate_highPerformanceMode_1.inPlaces[1]);
  connect(highPerformanceMode_activate.outPlaces[2], hybridSupply.inTransition[2]);
  connect(highPerformanceMode.outTransition[4], hybridSupply_deactivate_highPerformanceMode_1.inPlaces[2]);
  connect(highPerformanceMode.outTransition[5], IA_hybridSupply_highPerformanceMode_requirement_1.inPlace);
  connect(IA_hybridSupply_highPerformanceMode_requirement_1.outTransition, hybridSupply_deactivate.inPlaces[2]);

annotation (
  uses(PNlib(version = "3.0.0"))
);

end ITSystem;
