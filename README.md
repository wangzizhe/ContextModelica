# ContextModelica

A modular framework for simulating Modelica **Variable Structure Systems (VSS)** using the [Functional Mock-up Interface (FMI)](https://fmi-standard.org/) with **context-aware mode switching via [Context Petri Nets (CoPN)](https://wangzizhe.github.io/CoPN)**

## ✨ Features

- 🔧 **FMUVSS** – FMU-based execution of VSS with switchable modes
- 🔁 **ContextModelica** – Context-driven control of mode transitions using CoPN
- 🧬 **ModeGen** – Submodel extraction from a unified Modelica layer (SUM)

## 📦 Modules

### 1. `FMUVSS`

A lightweight VSS simulation engine that leverages low-level FMI APIs

- **Output:** Full simulation result of VSS

### 2. `ContextModelica`

Enables formal, expressive **mode management** via CoPN, supporting complex context relationships

- **Features:** Context relationships like weak/strong inclusion, exclusion, and requirement 
  - Learn more: [Context Relationships | CoPN](https://wangzizhe.github.io/CoPN/docs/Overview/ContextRelationships.html)

### 3. `ModeGen`

Parses a **monolithic Modelica model** and generates mode-specific FMUs

- **Output:** Verified, co-simulation-ready FMUs

## 👀 License

This project is licensed under the [MIT License](./LICENSE)

## 📄 Citation

[Context-Oriented Modelica for Advanced Variability Management](https://www.ecp.ep.liu.se/index.php/modelica/article/view/1303) (DOI: https://doi.org/10.3384/ecp218165)

[PhD Thesis: Context-Oriented Modelica for Advanced Variability Management](https://nbn-resolving.org/urn:nbn:de:bsz:14-qucosa2-1055309)
