import json
from parser_cargo import parse_cargo
from parser_sydam import parse_sydam
import time

try:
    print("Parsing CARGO...")
    c = parse_cargo("CARGO ZOI.pdf")
    print(f"CARGO parsed. Navire: {c.get('navire')}, {len(c.get('ports', {}))} ports")
    # count total bls
    total_bls = sum(len(p['bls']) for p in c.get('ports', {}).values())
    print(f"Total BLs: {total_bls}")
except Exception as e:
    import traceback
    traceback.print_exc()

print("---")
try:
    print("Parsing SYDAM...")
    s = parse_sydam("SYDAM ZOI.pdf")
    print(f"SYDAM parsed. Navire: {s.get('navire')}, {len(s.get('ports', {}))} ports")
    total_bls_s = sum(len(p['bls']) for p in s.get('ports', {}).values())
    print(f"Total BLs: {total_bls_s}")
except Exception as e:
    import traceback
    traceback.print_exc()
