import json
from parser_cargo import parse_cargo
from parser_sydam import parse_sydam

try:
    print("--- CARGO ZOI ---")
    p = parse_cargo("CARGO ZOI.pdf")
    bls = []
    for port, data in p.get("ports", {}).items():
        bls.extend(list(data['bls'].keys()))
    print("CARGO First 3 BLs:", bls[:3])
except Exception as e:
    print("Cargo error:", e)

try:
    print("\n--- SYDAM ZOI ---")
    ps = parse_sydam("SYDAM ZOI.pdf")
    bls_s = []
    for port, data in ps.get("ports", {}).items():
        bls_s.extend(list(data['bls'].keys()))
    print("SYDAM First 3 BLs:", bls_s[:3])
except Exception as e:
    print("Sydam error:", e)
