import json
from parser_cargo import parse_cargo
from parser_sydam import parse_sydam
from reconciliation import reconcile_manifests

try:
    c = parse_cargo("CARGO ZOI.pdf")
    s = parse_sydam("SYDAM ZOI.pdf")
    diffs = reconcile_manifests(c, s, "CARGO", "SYDAM")
    
    missing_bls = [d for d in diffs if d["Champ"] == "Présence BL"]
    print(f"Total differences: {len(diffs)}")
    print(f"Missing BLs: {len(missing_bls)}")
    if missing_bls:
        for d in missing_bls[:5]:
            print(f"- {d['Identifiant']}: {d['CARGO']} | {d['SYDAM']}")

except Exception as e:
    import traceback
    traceback.print_exc()
