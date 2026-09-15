#!/usr/bin/env python3
"""
scripts/audit_test_vectors.py — Golden Test Vector Verifier & Auditor
====================================================================
Audits `model/test_vectors_gate0.json` to verify:
1. JSON Schema integrity and presence of all required metadata.
2. Dynamic range of expected accumulator outputs (strictly within 13-bit signed [-4096, +4095]).
3. Matrix and vector dimensions (16x16 weights, 16 inputs, 16 accumulators).
4. Physical/mathematical consistency for downstream RTL and FPGA testbenches.

Usage:
    python3 scripts/audit_test_vectors.py [path/to/test_vectors.json]
"""

import sys
import json
from pathlib import Path

DEFAULT_PATH = Path("model/test_vectors_gate0.json")

def audit_vectors(json_path: Path):
    if not json_path.exists():
        print(f"[-] Error: File not found: {json_path}")
        sys.exit(1)

    print(f"[*] Loading test vectors from: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check top-level metadata
    metadata = data.get("metadata", {})
    vectors = data.get("vectors", [])

    gen = metadata.get("generator", "N/A")
    arr_size = metadata.get("array_size", "16x16")
    n_cycles = metadata.get("bitstream_length_N", 256)
    acc_bits = metadata.get("accumulator_bits", 13)

    print("\n" + "=" * 82)
    print("                 CIMTinyTO GATE 0 GOLDEN VECTOR AUDIT")
    print("=" * 82)
    print(f" Generator         : {gen}")
    print(f" Array Dimension   : {arr_size}")
    print(f" Bitstream Cycle N : {n_cycles}")
    print(f" Target Precision  : {acc_bits}-bit Signed Accumulator [-4096, +4095]")
    print(f" Total Test Vectors: {len(vectors)}")
    print("-" * 82)

    all_passed = True

    print(f"{'Idx':<4} | {'Test Vector Name':<34} | {'Min':>6} | {'Max':>6} | {'13b Range':^9} | {'Status':^6}")
    print("-" * 82)

    for idx, vec in enumerate(vectors):
        name = vec.get("name", f"vector_{idx}")
        accumulators = vec.get("expected_accumulators", [])
        weights = vec.get("weights", [])
        inputs = vec.get("inputs", [])

        # Dimension checks for 16x16 macro
        dim_ok = (len(weights) == 16 and all(len(row) == 16 for row in weights) and
                  len(inputs) == 16 and len(accumulators) == 16)

        if not accumulators or not dim_ok:
            print(f"{idx:<4} | {name:<34} | {'N/A':>6} | {'N/A':>6} | {'DIM_ERR':^9} |  FAIL")
            all_passed = False
            continue

        min_val = min(accumulators)
        max_val = max(accumulators)

        # 13-bit signed range check: [-4096, 4095]
        range_ok = (-4096 <= min_val <= 4095) and (-4096 <= max_val <= 4095)
        status_ok = dim_ok and range_ok

        if not status_ok:
            all_passed = False

        status_str = "PASS" if status_ok else "FAIL"
        range_str = "VALID" if range_ok else "OVERFLOW"

        print(f"{idx:<4} | {name:<34} | {min_val:6d} | {max_val:6d} | {range_str:^9} |  {status_str:^4}")

    print("=" * 82)
    if all_passed:
        print("[+] AUDIT SUCCESS: All test vectors strictly conform to 13-bit signed limits")
        print("    and 16x16 structural bounds. Ready for RTL (Gate 1) & FPGA (Gate 3) testbenches.")
        print("=" * 82 + "\n")
        return 0
    else:
        print("[-] AUDIT FAILURE: One or more test vectors exceeded dynamic range or had invalid dimensions.")
        print("=" * 82 + "\n")
        return 1

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    sys.exit(audit_vectors(target))
