---
name: pedagogical-implementation-planning
description: >-
  Enforces a mandatory learning-first implementation planning protocol before executing any new feature,
  ASIC pillar, subsystem, hardware driver, or non-trivial software implementation.
  Ensures the user has the opportunity to learn every underlying concept, review IC trade-offs, and approve
  the plan before any code or hardware logic is created.
---

# Pedagogical Implementation Planning Protocol (Learning-First Mandate)

## Core Directive: Stop & Plan First (Zero Premature Execution)

Whenever the user asks to start a new feature, ASIC pillar, hardware driver, application pipeline, or non-trivial software task (e.g., "Let's begin Pillar X", "Implement feature Y", "Add support for Z"):

> [!IMPORTANT]
> **MANDATORY HOLD — DO NOT IMPLEMENT CODE IMMEDIATELY.**
> The primary user goal is **learning every essential perspective of ASIC, FPGA, and embedded system design**.
> Rushing directly into writing code, tests, and drivers in a single turn robs the user of the learning journey.
>
> You MUST first pause, design, and present an educational, structured **Implementation Plan** as an interactive Markdown Artifact (`RequestFeedback: true`).
> You MUST wait for the user to review, ask questions, adjust the architecture, and explicitly approve the plan before writing any implementation code.

---

## The 4 Pillars of a Pedagogical Implementation Plan

Every implementation plan artifact created under this skill MUST follow this 4-part structure:

### 1. Conceptual Foundations & IC Fundamentals ("The Why")
* **Underlying Physics & Silicon Realities:**
  Explain the physics and circuit realities behind the task (e.g., dynamic switching power $P = \alpha C V^2 f$, clock skew, setup/hold timing margin, metastability, transistor counts, routing track congestion, sensor MEMS capacitance, sigma-delta modulation, DMA ring buffers).
* **Trade-Off Analysis:**
  Explicitly contrast the proposed approach against industry alternatives (e.g., Wallace tree compressor vs. ripple adder, standard-cell DFF vs. 6T SRAM, stationary weights vs. weight streaming, hardware decimation filter vs. software FIR).
* **Traps & Guardrails:**
  Identify common failure modes that pass functional simulation but fail on physical silicon or real hardware (unintended latches, race conditions, floating buses, hold-time violations across PVT corners, non-reentrant static state, memory wall bottlenecks).

### 2. Microarchitecture & Visual Dataflow Diagrams
* **Text / ASCII / Mermaid Diagrams:**
  Create clear block diagrams showing dataflow, bit widths, clock domains, and hardware abstraction boundaries.
* **Interface & Pinout Protocols:**
  Document exact signal mappings, logic voltage levels (e.g. 3.3V LVCMOS vs 1.8V core), and clock domain crossings (CDC) with dual flip-flop synchronizers where applicable.

### 3. Bite-Sized Milestone Roadmap
Break the implementation down into discrete, digestible milestones:
* **Milestone 1:** Mathematical Golden Model & Algorithmic Exploration (Python/NumPy).
* **Milestone 2:** Core Architecture / Driver Implementation (C99 / Verilog RTL).
* **Milestone 3:** Testbench Harness, Waveform Inspection & Numerical Parity Verification.
* **Milestone 4:** System Integration, Hardware Bench Emulation & End-to-End Demonstration.

For each milestone, state:
- **What is being built** and **why**.
- **What concepts the user will learn** from inspecting the code or test output.
- **Verification criteria** (exact pass/fail metrics, 0 LSB discrepancy, timing slack).

### 4. Interactive Learning Checkpoints & Questions for the User
* Highlight 1–3 specific microarchitectural choices or parameter trade-offs (e.g., precision vs. memory footprint, sampling rate vs. buffer size).
* Ask the user for their thoughts, questions, or preferred trade-offs.
* **STOP and yield control back to the user.** Do not begin implementing Milestone 1 until the user responds with approval.

---

## Execution Protocol (Post-Approval)

Once the user approves the plan:
1. **Paced Execution:** Implement **one milestone at a time**. Do not bundle all milestones into a single turn unless explicitly requested by the user.
2. **Deep Explanations in Code:** Accompany code with rich educational comments explaining the silicon and hardware reasoning behind non-trivial lines.
3. **Interactive Inspection:** Provide concrete shell commands for the user to run, inspect waveforms (`gtkwave` / `surfer`), examine intermediate tensors, or check power metrics.
4. **Milestone Check-In:** At the end of each milestone, summarize what was proven, confirm test results, and check in with the user before proceeding to the next milestone.
