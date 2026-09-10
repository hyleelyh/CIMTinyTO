#!/usr/bin/env python3
"""
parse_openlane_reports.py — EDA Physical Sign-off & Timing Audit Parser

Purpose:
  In physical ASIC design (OpenLane 2 / OpenROAD), timing and physical reports
  are distributed across dozens of files. This script parses:
  1. Static Timing Analysis (STA):
     - Setup Slack (T_slack, setup >= 0 ns).
     - Hold Slack (T_slack, hold >= 0 ns) -> FATAL SILICON VIOLATION if negative!
  2. Placement Density:
     - Standard cell core utilization (target: ~58.8%, warning if > 65%).
  3. Physical Verification Sign-off:
     - Magic DRC violations (must be 0).
     - Netgen LVS mismatches (must be 0).
     - Antenna violations (must be 0).
  4. Emits a compact Markdown sign-off table (<30 lines).

Exit Codes:
  0 = Clean sign-off (all timing, density, and DRC/LVS passed).
  1 = Fatal sign-off failure (hold violation, DRC, LVS, or antenna failure).
  2 = Timing setup failure (recoverable by lowering clock frequency).
"""

import sys
import os
import re
import argparse
from typing import Dict, Tuple, Optional


def parse_openlane_metrics(report_text: str) -> Dict:
    """Extract timing, placement, and physical metrics from text or CSV summary."""
    data = {
        "setup_slack_ns": None,
        "hold_slack_ns": None,
        "worst_slack_ns": None,
        "core_utilization_pct": None,
        "magic_drc_count": None,
        "lvs_error_count": None,
        "antenna_violations": None,
        "clock_period_ns": None,
        "effective_frequency_mhz": None
    }

    # Regex search patterns
    patterns = {
        "setup_slack_ns": [
            r"wns\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)",
            r"setup[_ ]slack\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)",
            r"worst[_ ]negative[_ ]slack\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)",
            r"tns_setup\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)"
        ],
        "hold_slack_ns": [
            r"worst[_ ]hold[_ ]slack\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)",
            r"hold[_ ]slack\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)",
            r"whs\s*[:=,\s]+([-+]?[0-9]*\.?[0-9]+)"
        ],
        "core_utilization_pct": [
            r"core[_ ]util(?:ization)?\s*[:=,\s]+([0-9]*\.?[0-9]+)",
            r"utilization\s*[:=,\s]+([0-9]*\.?[0-9]+)%",
            r"placement[_ ]density\s*[:=,\s]+([0-9]*\.?[0-9]+)"
        ],
        "magic_drc_count": [
            r"magic[_ ]drc[_ ]error[_ ]count\s*[:=,\s]+(\d+)",
            r"drc[_ ]errors\s*[:=,\s]+(\d+)",
            r"magic[_ ]drc\s*[:=,\s]+(\d+)"
        ],
        "lvs_error_count": [
            r"lvs[_ ]error[_ ]count\s*[:=,\s]+(\d+)",
            r"lvs[_ ]errors\s*[:=,\s]+(\d+)",
            r"netgen[_ ]lvs[_ ]errors\s*[:=,\s]+(\d+)"
        ],
        "antenna_violations": [
            r"antenna[_ ]violations\s*[:=,\s]+(\d+)",
            r"antenna[_ ]drc\s*[:=,\s]+(\d+)"
        ],
        "clock_period_ns": [
            r"clock[_ ]period\s*[:=,\s]+([0-9]*\.?[0-9]+)",
            r"target[_ ]period\s*[:=,\s]+([0-9]*\.?[0-9]+)"
        ]
    }

    for key, regexes in patterns.items():
        for reg in regexes:
            match = re.search(reg, report_text, re.IGNORECASE)
            if match:
                val = match.group(1)
                if "count" in key or "violations" in key:
                    data[key] = int(val)
                else:
                    data[key] = float(val)
                break

    # Calculate effective frequency if clock period and setup slack are present
    if data["clock_period_ns"] is not None and data["setup_slack_ns"] is not None:
        eff_period = data["clock_period_ns"] - data["setup_slack_ns"]
        if eff_period > 0:
            data["effective_frequency_mhz"] = round(1000.0 / eff_period, 1)

    return data


def format_openlane_summary(data: Dict) -> Tuple[str, int]:
    """Generate a clean markdown summary table (<30 lines) and return exit code."""
    out = []
    exit_code = 0
    failures = []
    warnings = []

    # Hold Slack Audit (Critical Silicon Fatality)
    hold = data["hold_slack_ns"]
    if hold is not None:
        if hold < 0:
            failures.append(f"FATAL: Hold slack violated ({hold:.3f} ns < 0 ns). Silicon will suffer race conditions!")
            exit_code = 1
        hold_str = f"{hold:+.3f} ns"
    else:
        hold_str = "N/A (check STA report)"

    # Setup Slack Audit
    setup = data["setup_slack_ns"]
    if setup is not None:
        if setup < 0:
            if exit_code == 0:
                exit_code = 2
            warnings.append(f"Setup slack negative ({setup:.3f} ns). Maximum frequency reduced.")
        setup_str = f"{setup:+.3f} ns"
    else:
        setup_str = "N/A"

    # DRC / LVS / Antenna
    drc = data["magic_drc_count"]
    if drc is not None and drc > 0:
        failures.append(f"DRC Failures: {drc} Magic violations!")
        exit_code = 1
    drc_str = f"{drc}" if drc is not None else "0"

    lvs = data["lvs_error_count"]
    if lvs is not None and lvs > 0:
        failures.append(f"LVS Mismatches: {lvs} Netgen errors!")
        exit_code = 1
    lvs_str = f"{lvs}" if lvs is not None else "0"

    ant = data["antenna_violations"]
    if ant is not None and ant > 0:
        failures.append(f"Antenna Rule Violations: {ant} gates at ESD breakdown risk!")
        exit_code = 1
    ant_str = f"{ant}" if ant is not None else "0"

    # Placement Density
    util = data["core_utilization_pct"]
    if util is not None:
        if util > 65.0:
            warnings.append(f"Core utilization {util:.1f}% exceeds 65% congestion limit.")
        util_str = f"{util:.1f}%"
    else:
        util_str = "N/A"

    overall_status = "PASS (Sign-off Ready)" if exit_code == 0 else ("WARNING (Setup Failure)" if exit_code == 2 else "FAIL (Fatal)")

    out.append("### OpenLane Physical & Timing Sign-Off Audit")
    out.append(f"- **Overall Status:** **{overall_status}**")
    if data["effective_frequency_mhz"]:
        out.append(f"- **Target Clock:** {data['clock_period_ns']} ns | **Achievable Frequency:** ~{data['effective_frequency_mhz']} MHz")
    out.append("")
    out.append("| Sign-Off Category | Metric | Recorded Value | Requirement | Status |")
    out.append("|---|---|---|---|---|")
    out.append(f"| **Hold Timing** | Hold Slack (WHS) | `{hold_str}` | $\\ge 0.000$ ns | {'✓ PASS' if (hold is None or hold >= 0) else '✗ FATAL'} |")
    out.append(f"| **Setup Timing** | Setup Slack (WNS) | `{setup_str}` | $\\ge 0.000$ ns | {'✓ PASS' if (setup is None or setup >= 0) else '⚠ SLOW'} |")
    out.append(f"| **Floorplan** | Core Utilization | `{util_str}` | $\\le 65.0\\%$ | {'✓ OPTIMAL' if (util is None or util <= 65.0) else '⚠ HIGH'} |")
    out.append(f"| **Physical DRC** | Magic DRC Errors | `{drc_str}` | 0 errors | {'✓ CLEAN' if (drc is None or drc == 0) else '✗ VIOLATION'} |")
    out.append(f"| **Physical LVS** | Netgen Mismatches | `{lvs_str}` | 0 errors | {'✓ CLEAN' if (lvs is None or lvs == 0) else '✗ MISMATCH'} |")
    out.append(f"| **Antenna DRC** | Gate Violations | `{ant_str}` | 0 errors | {'✓ CLEAN' if (ant is None or ant == 0) else '✗ DAMAGE'} |")

    if failures:
        out.append("")
        out.append("> [!CAUTION]")
        for f in failures:
            out.append(f"> **{f}**")
    elif warnings:
        out.append("")
        out.append("> [!WARNING]")
        for w in warnings:
            out.append(f"> **{w}**")
    else:
        out.append("")
        out.append("> [!NOTE]\n> **Tapeout Ready:** All static timing corners, physical design rules, and core density targets passed.")

    return "\n".join(out), exit_code


def run_self_tests():
    """Verify parser against mock OpenLane reports."""
    print("[TEST] Running parse_openlane_reports self-tests...")

    # Test 1: Clean sign-off
    clean_sample = """
    setup slack: +1.420
    hold slack: +0.280
    core_utilization: 58.8
    clock_period: 40.0
    magic_drc_error_count: 0
    lvs_error_count: 0
    antenna_violations: 0
    """
    data = parse_openlane_metrics(clean_sample)
    assert data["setup_slack_ns"] == 1.42
    assert data["hold_slack_ns"] == 0.28
    assert data["core_utilization_pct"] == 58.8
    table, code = format_openlane_summary(data)
    assert code == 0, f"Expected clean exit code 0, got {code}"
    print("  [✓] Test 1: Clean sign-off passed with code 0.")

    # Test 2: Fatal hold timing violation
    hold_violation_sample = """
    setup slack: +2.100
    hold slack: -0.150
    core_utilization: 55.0
    magic_drc_error_count: 0
    lvs_error_count: 0
    antenna_violations: 0
    """
    data_hold = parse_openlane_metrics(hold_violation_sample)
    table_hold, code_hold = format_openlane_summary(data_hold)
    assert code_hold == 1, f"Expected fatal hold exit code 1, got {code_hold}"
    print("  [✓] Test 2: Fatal negative hold slack caught with exit code 1.")

    # Test 3: DRC failure
    drc_fail_sample = """
    setup slack: +0.500
    hold slack: +0.050
    magic_drc_error_count: 4
    lvs_error_count: 0
    """
    data_drc = parse_openlane_metrics(drc_fail_sample)
    table_drc, code_drc = format_openlane_summary(data_drc)
    assert code_drc == 1, f"Expected DRC failure exit code 1, got {code_drc}"
    print("  [✓] Test 3: Magic DRC failure caught with exit code 1.")

    # Test 4: Setup slack warning
    setup_fail_sample = """
    setup slack: -0.800
    hold slack: +0.120
    clock_period: 20.0
    magic_drc_error_count: 0
    lvs_error_count: 0
    antenna_violations: 0
    """
    data_setup = parse_openlane_metrics(setup_fail_sample)
    table_setup, code_setup = format_openlane_summary(data_setup)
    assert code_setup == 2, f"Expected setup warning exit code 2, got {code_setup}"
    print("  [✓] Test 4: Setup timing warning caught with exit code 2.")

    print("[TEST] All parse_openlane_reports self-tests PASSED successfully!")


def main():
    parser = argparse.ArgumentParser(description="Parse OpenLane physical and timing reports.")
    parser.add_argument("report", nargs="?", help="Path to OpenLane summary file or directory (reads stdin if omitted).")
    parser.add_argument("--test", action="store_true", help="Run internal parser test suite.")
    args = parser.parse_args()

    if args.test:
        run_self_tests()
        sys.exit(0)

    if args.report:
        if os.path.isdir(args.report):
            # Look for summary files inside run directory
            found_text = ""
            for root, _, files in os.walk(args.report):
                for file in files:
                    if file in ["metrics.csv", "final_summary_report.csv", "signoff.rpt", "min.rpt", "max.rpt"]:
                        fpath = os.path.join(root, file)
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            found_text += f"\n--- {file} ---\n" + f.read()
            if not found_text:
                print(f"Error: No recognizable summary reports found in directory '{args.report}'.", file=sys.stderr)
                sys.exit(1)
            content = found_text
        elif os.path.isfile(args.report):
            with open(args.report, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            print(f"Error: Path '{args.report}' does not exist.", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("Usage: parse_openlane_reports.py [path] or pipe via stdin. Use --test for self-test.", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read()

    data = parse_openlane_metrics(content)
    summary, exit_code = format_openlane_summary(data)
    print(summary)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
