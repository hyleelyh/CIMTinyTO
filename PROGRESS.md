# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-22 16:05
### [Built & Verified]
- `.agents/skills/lab-hardware-inventory/SKILL.md`: Authored dedicated project skill defining user's complete hardware lab fleet (Korad KA3005P, PYNQ-Z2, DE10-Lite, STM32 B-U585I-IOT02A, Raspberry Pi 5, SiFive HiFive 1, OBDLink LX, Arduino Uno R3), electrical safety rules, interface specs, and multi-demo matrix.
- `AGENTS.md`: Integrated User Laboratory Hardware Fleet section permanently linking system instructions to the hardware skill.
- `docs/physical_sizing_and_tradeoff_analysis.md`: Detailed block-by-block area audit, non-linear scaling laws, and ResNet/audio/automotive application analysis.
- Previous baseline verified: Verilator lint clean (0 warnings), Cocotb 3/3 test suites bit-exact pass (100%), parser self-tests clean.

### [Architecture Decisions & Physical Sizing Deep-Dive]
- **Hardware Fleet Integration & $0 Additional Cost Verification:**
  - Evaluated user's on-hand hardware inventory across 6 platforms. Confirmed that all sensor, voice, vision, and telemetry requirements are completely satisfied without purchasing any new hardware:
    1. **Voice AI (KWS):** STM32 B-U585I dual digital MEMS microphones (`MP23DB01HP`) via hardware PDM/MDF filter.
    2. **Industrial Vibration Anomaly:** STM32 B-U585I industrial 3D accelerometer (`ISM330DHCX`) with 16-bin CMSIS-DSP FFT.
    3. **Live Camera Vision:** Raspberry Pi 5 via 50 MHz SPI streaming Micro-ResNet at 12.5 FPS.
    4. **RISC-V Coprocessor:** SiFive HiFive 1 (320 MHz FE310) demonstrating heterogeneous open-source compute.
    5. **Tactile Hardware Console:** Terasic DE10-Lite (MAX 10 FPGA) with 7-segment hex accumulator displays.
    6. **Automotive Telemetry:** OBDLink LX reading 16 live CAN engine/CVT fluid temperature PIDs with complete wireless air-gap isolation.
- **Electrical Safety & Bring-Up Protocols:**
  - **Arduino Uno R3 Caution:** Identified $+5.0\text{V}$ logic hazard. Connecting directly to 3.3V SkyWater 130nm I/O pads risks gate oxide breakdown; bidirectional level shifting is strictly enforced.
  - **Power vs. Logic Decoupling:** Tiny Tapeout carrier board USB-C safely accepts 5V via on-board 3.3V and 1.8V LDO regulators; all external header pins operate strictly at safe 3.3V LVCMOS.
  - **Bench Instrumentation:** Korad KA3005P linear supply configured with $5.00\text{V}$, $120\text{ mA}$ OCP current limit for Day-1 smoke-testing and real-time $P = C V^2 f$ power profiling.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Golden Model): 100% COMPLETE & FROZEN.**
- **Pillar 2 (Microarchitecture & Verification): 100% COMPLETE & FROZEN.**
- **Pillar 3 (Physical ASIC Flow): IN PROGRESS / PENDING SIZING DECISION.**
  - All OpenLane 2 configs, constraints, and scripts verified.
  - Sizing decision paused for user reflection: Option 1 ($16\times 16$ on $2\times 2$ tile, $12.5\text{ FPS}$) vs. Option 2 ($8\times 8$ on $1\times 2$ tile, $2.7\text{ FPS}$).

### [Next Steps]
1. User to evaluate performance vs. shuttle budget goals.
2. If Option 1 ($16\times 16$ on $2\times 2$ tile): Update `info.yaml` to `tiles: "2x2"` and re-trigger OpenLane 2 cloud hardening on GitHub Actions.
3. If Option 2 ($8\times 8$ on $1\times 2$ tile): Parameterize RTL submodules down to $8\times 8$, update Cocotb testbenches, and re-trigger hardening on $1\times 2$.
4. Achieve physical GDS placement and routing sign-off before closing Pillar 3.
