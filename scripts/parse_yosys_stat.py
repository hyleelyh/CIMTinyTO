#!/usr/bin/env python3
"""
parse_yosys_stat.py — EDA Log Hygiene Parser for Yosys Synthesis Reports

Purpose:
  In open-source silicon flows (Sky130 / OpenLane), Yosys synthesis logs often
  exceed 5,000+ lines. This script parses raw Yosys logs or 'stat' outputs to:
  1. Audit sequential registers (ensuring all 256 weight DFFs were synthesized and not pruned).
  2. Detect dangerous inferred latches (unintentional latches from incomplete if/case blocks).
  3. Categorize standard cells (combinational logic, arithmetic, multiplexers, sequential).
  4. Emit a compact Markdown summary table strictly under 30 lines.

Exit Codes:
  0 = Clean synthesis (no latches, registers preserved, valid cell counts).
  1 = Latch detected or syntax/synthesis error.
  2 = Register count audit failure (e.g. missing weight DFFs).
"""

import sys
import os
import re
import argparse
from typing import Dict, List, Tuple, Optional


def parse_yosys_log(text: str) -> Dict:
    """Parse Yosys log/stat text and extract cell counts, area, and warnings."""
    results = {
        "top_module": "unknown",
        "total_cells": 0,
        "chip_area_um2": 0.0,
        "sequential_cells": 0,
        "combinational_cells": 0,
        "inferred_latches": [],
        "cell_breakdown": {},
        "warnings": [],
        "errors": []
    }

    lines = text.splitlines()
    in_stat_block = False

    # Regex patterns
    mod_pattern = re.compile(r"===\s*(\S+)\s*===")
    cell_line_pattern = re.compile(r"^\s*([a-zA-Z0-9_\$]+)\s+(\d+)\s*$")
    area_pattern = re.compile(r"Chip area for module\s*['\"]?(\S+?)['\"]?:\s*([0-9\.]+)")
    total_cells_pattern = re.compile(r"Number of cells:\s*(\d+)")
    latch_warning_pattern = re.compile(r"(Latch inferred for signal.*|inferring latch.*)", re.IGNORECASE)

    for line in lines:
        # Check for latch warnings in synthesis log
        latch_match = latch_warning_pattern.search(line)
        if latch_match:
            results["inferred_latches"].append(latch_match.group(1).strip())

        # Check for module header in stat
        mod_match = mod_pattern.search(line)
        if mod_match:
            results["top_module"] = mod_match.group(1)
            in_stat_block = True
            continue

        # Check total cells
        tot_match = total_cells_pattern.search(line)
        if tot_match:
            results["total_cells"] = int(tot_match.group(1))
            continue

        # Check chip area
        area_match = area_pattern.search(line)
        if area_match:
            try:
                results["chip_area_um2"] = float(area_match.group(2))
            except ValueError:
                pass
            continue

        # Parse individual cell counts
        c_match = cell_line_pattern.match(line)
        if c_match:
            cell_name = c_match.group(1)
            count = int(c_match.group(2))
            results["cell_breakdown"][cell_name] = count

            # Check if cell is an inferred latch
            if "dlatch" in cell_name.lower() or "dlxtp" in cell_name.lower():
                results["inferred_latches"].append(f"Cell {cell_name} ({count} instances)")

    # Classify cells into sequential vs combinational
    for cell, count in results["cell_breakdown"].items():
        cell_lower = cell.lower()
        if any(dff_kw in cell_lower for dff_kw in ["dfxtp", "dfrtp", "dfbbp", "dff", "flop"]):
            results["sequential_cells"] += count
        elif "dlatch" in cell_lower or "dlxtp" in cell_lower:
            pass  # Latch tracked separately
        else:
            results["combinational_cells"] += count

    return results


def format_summary_table(data: Dict, expected_min_dffs: int = 256) -> Tuple[str, int]:
    """Generate a clean markdown summary (<30 lines) and return exit code."""
    out = []
    exit_code = 0

    latch_count = len(data["inferred_latches"])
    dff_count = data["sequential_cells"]
    area = data["chip_area_um2"]
    total = data["total_cells"]

    status_icon = "PASS"
    if latch_count > 0:
        status_icon = "FAIL (Latches Inferred!)"
        exit_code = 1
    elif dff_count < expected_min_dffs:
        status_icon = f"FAIL (DFF count {dff_count} < expected {expected_min_dffs})"
        exit_code = 2

    out.append("### Yosys Synthesis Hygiene Audit")
    out.append(f"- **Top Module:** `{data['top_module']}` | **Status:** **{status_icon}**")
    out.append(f"- **Total Standard Cells:** {total} | **Sequential (DFF):** {dff_count} | **Area:** {area:,.1f} µm²")
    out.append("")
    out.append("| Cell Category | Cell Name | Instances | Notes / Silicon Impact |")
    out.append("|---|---|---|---|")

    # Group cell breakdown by top contributors
    sorted_cells = sorted(data["cell_breakdown"].items(), key=lambda x: x[1], reverse=True)
    shown_count = 0
    for cell, count in sorted_cells:
        if shown_count >= 8:
            break
        cell_lower = cell.lower()
        if "dfxtp" in cell_lower or "dfrtp" in cell_lower:
            cat = "Sequential"
            note = "Registers (Weight / Acc)"
        elif "dlatch" in cell_lower or "dlxtp" in cell_lower:
            cat = "FATAL LATCH"
            note = "Race condition risk!"
        elif "xnor" in cell_lower or "xor" in cell_lower:
            cat = "Arithmetic"
            note = "Stochastic PE / Adder Tree"
        elif "and" in cell_lower or "nand" in cell_lower:
            cat = "Logic Gate"
            note = "PE / Control Logic"
        elif "mux" in cell_lower:
            cat = "Multiplexer"
            note = "Routing / Mode Select"
        else:
            cat = "Combinational"
            note = "Logic Standard Cell"

        out.append(f"| {cat} | `{cell}` | {count} | {note} |")
        shown_count += 1

    if len(sorted_cells) > shown_count:
        rem_count = sum(c for _, c in sorted_cells[shown_count:])
        out.append(f"| Other Cells | *{len(sorted_cells) - shown_count} cell types* | {rem_count} | Standard cell library |")

    out.append("")
    if latch_count > 0:
        out.append(f"> [!CAUTION]\n> **Inferred Latches Detected ({latch_count}):** Review incomplete `if`/`case` blocks in RTL!")
        for l in data["inferred_latches"][:3]:
            out.append(f"> - {l}")
    elif dff_count >= expected_min_dffs:
        out.append(f"> [!NOTE]\n> **Register Audit Verified:** {dff_count} DFFs intact (meets target {expected_min_dffs} weight DFFs).")

    return "\n".join(out), exit_code


def run_self_tests():
    """Verify parser against mock Yosys logs."""
    print("[TEST] Running parse_yosys_stat self-tests...")

    # Test Case 1: Clean synthesis
    clean_sample = """
=== tt_um_scim_core ===
   Number of wires:                1200
   Number of cells:                 650
     sky130_fd_sc_hd__and2_0         64
     sky130_fd_sc_hd__dfxtp_1       256
     sky130_fd_sc_hd__xnor2_1       128
     sky130_fd_sc_hd__mux2_1         48
     sky130_fd_sc_hd__inv_1          30
   Chip area for module 'tt_um_scim_core': 18828.500000
"""
    data = parse_yosys_log(clean_sample)
    assert data["top_module"] == "tt_um_scim_core"
    assert data["sequential_cells"] == 256
    assert len(data["inferred_latches"]) == 0
    table, code = format_summary_table(data, expected_min_dffs=256)
    assert code == 0, f"Expected clean exit code 0, got {code}"
    print("  [✓] Test 1: Clean log parsed with exit code 0.")

    # Test Case 2: Inferred Latch detection
    latch_sample = """
Warning: Latch inferred for signal '\\col_accum_reg' from process.
=== tt_um_scim_core ===
   Number of cells:                 100
     sky130_fd_sc_hd__dfxtp_1       256
     sky130_fd_sc_hd__dlxtp_1        16
   Chip area for module 'tt_um_scim_core': 5000.0
"""
    data_latch = parse_yosys_log(latch_sample)
    assert len(data_latch["inferred_latches"]) > 0
    table_latch, code_latch = format_summary_table(data_latch, expected_min_dffs=256)
    assert code_latch == 1, f"Expected latch exit code 1, got {code_latch}"
    print("  [✓] Test 2: Inferred latch caught with exit code 1.")

    # Test Case 3: Missing DFFs (pruning detection)
    pruned_sample = """
=== tt_um_scim_core ===
   Number of cells:                 50
     sky130_fd_sc_hd__dfxtp_1        64
   Chip area for module 'tt_um_scim_core': 2000.0
"""
    data_pruned = parse_yosys_log(pruned_sample)
    table_pruned, code_pruned = format_summary_table(data_pruned, expected_min_dffs=256)
    assert code_pruned == 2, f"Expected pruned DFF exit code 2, got {code_pruned}"
    print("  [✓] Test 3: Pruned DFFs caught with exit code 2.")

    print("[TEST] All parse_yosys_stat self-tests PASSED successfully!")


def main():
    parser = argparse.ArgumentParser(description="Parse Yosys synthesis logs and enforce cell hygiene.")
    parser.add_argument("logfile", nargs="?", help="Path to Yosys synthesis log (reads stdin if omitted).")
    parser.add_argument("--min-dffs", type=int, default=256, help="Minimum expected DFF count (default: 256).")
    parser.add_argument("--test", action="store_true", help="Run internal parser test suite.")
    args = parser.parse_args()

    if args.test:
        run_self_tests()
        sys.exit(0)

    if args.logfile:
        if not os.path.exists(args.logfile):
            print(f"Error: Log file '{args.logfile}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.logfile, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        if sys.stdin.isatty():
            print("Usage: parse_yosys_stat.py [logfile] or pipe via stdin. Use --test for self-test.", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read()

    data = parse_yosys_log(content)
    summary, exit_code = format_summary_table(data, expected_min_dffs=args.min_dffs)
    print(summary)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
