# ContextModelica

A modular framework for simulating Modelica **Variable Structure Systems (VSS)** using the [Functional Mock-up Interface (FMI)](https://fmi-standard.org/) and **context-aware mode switching using [Context Petri Nets](https://wangzizhe.github.io/CoPN)**.

## ✨ Features

- 🔧 **FMUVSS** – Intuitive FMU-based simulation of VSS without external control models.
- 🔁 **ContextFMUVSS** – Integrates Context Petri Nets for expressive and formal mode-switching logic.
- 🧬 **ModeGen** – Extracts submodels from monolithic Modelica code/Single Underlying Layer (SUM) and exports them as individual FMUs.

## 📦 Modules

### 1. `FMUVSS`

A lightweight simulator that lets users define **VSS behavior using FMUs** directly. Mode-switching conditions are user-defined with simple logic.

- **Use when:** you want quick, low-overhead VSS simulations.
- **Input:** multiple FMUs, switch conditions.
- **Output:** the full simulation result of VSS.

### 2. `ContextFMUVSS`

This module enables **formal state management** using **Context Petri Nets**, offering expressive control over VSS mode transitions.

- **Use when:** you need complex and state-dependent transitions.
- **Features:** Context relationships like weak/strong inclusion, exclusion, and requirement. 
  - Learn more: [Context Relationships | CoPN](https://wangzizhe.github.io/CoPN/docs/Overview/ContextRelationships.html)

### 3. `ModeGen`

Parses **monolithic Modelica models** and automatically generates multiple FMUs based on mode definitions.

- **Use when:** You start from a unified Modelica system (SUM).
- **Output:** Co-Simulation FMUs ready for use.

## 👀 License

This project is licensed under the [MIT License](./LICENSE).