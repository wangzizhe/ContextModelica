model ITSystem_HybridSupply

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

  // Energy & Performance Parameters
  parameter Real corePowerFactor = 10.0;
  parameter Real frequencyPowerFactor = 5.0;
  parameter Real gridPower = 100.0;
  
  // CPU mode-dependent parameters
  parameter Integer cores = 0;
  parameter Real freq = 0;

  // System state variables
  Real hydrogenProduction "Hydrogen supplied";
  Real loadDemand "Current system load demand";
  Real totalEnergySupply;

  // CPU control variables
  Integer activeCores;
  Real cpuFrequency;
  
equation
  // Assign hydrogen production and load demand from tables
  hydrogenTable.u = time;
  hydrogenProduction = hydrogenTable.y[2];
  
  loadTable.u = time;
  loadDemand = loadTable.y[2];
  
  // Compute total available energy supply
  totalEnergySupply = hydrogenProduction + gridPower;
  
  // Determine active CPU cores and frequency based on performance mode
  activeCores = cores;
  cpuFrequency = freq;

end ITSystem_HybridSupply;
