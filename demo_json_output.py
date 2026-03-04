"""
demo_json_output.py
-------------------
Script de démonstration : parse SYDAM.pdf et CARGO.pdf
et génère le JSON conforme au plan défini dans PlanJson.docx
"""

import json
from parser_sydam import parse_sydam
from parser_cargo import parse_cargo

if __name__ == "__main__":
    print("=" * 60)
    print("DEMO - Parsing SYDAM.pdf -> JSON")
    print("=" * 60)
    sydam_data = parse_sydam("SYDAM.pdf")
    sydam_json = json.dumps(sydam_data, ensure_ascii=False, indent=2)

    preview = {
        "navire": sydam_data["navire"],
        "numero_voyage": sydam_data["numero_voyage"],
        "eta": sydam_data["eta"],
        "ports": {}
    }
    for port, pdata in list(sydam_data["ports"].items())[:2]:
        preview["ports"][port] = {"bls": {}}
        for bl, bdata in list(pdata["bls"].items())[:2]:
            preview["ports"][port]["bls"][bl] = bdata

    print(json.dumps(preview, ensure_ascii=False, indent=2))
    print(f"\n-> SYDAM: {len(sydam_data['ports'])} ports, "
          f"{sum(len(p['bls']) for p in sydam_data['ports'].values())} BLs extraits")

    with open("output_sydam.json", "w", encoding="utf-8") as f:
        f.write(sydam_json)
    print("-> Fichier complet : output_sydam.json\n")

    print("=" * 60)
    print("DEMO - Parsing CARGO.pdf -> JSON")
    print("=" * 60)
    cargo_data = parse_cargo("CARGO.pdf")
    cargo_json = json.dumps(cargo_data, ensure_ascii=False, indent=2)

    preview2 = {
        "navire": cargo_data["navire"],
        "numero_voyage": cargo_data["numero_voyage"],
        "eta": cargo_data["eta"],
        "ports": {}
    }
    for port, pdata in list(cargo_data["ports"].items())[:2]:
        preview2["ports"][port] = {"bls": {}}
        for bl, bdata in list(pdata["bls"].items())[:2]:
            preview2["ports"][port]["bls"][bl] = bdata

    print(json.dumps(preview2, ensure_ascii=False, indent=2))
    print(f"\n-> CARGO: {len(cargo_data['ports'])} ports, "
          f"{sum(len(p['bls']) for p in cargo_data['ports'].values())} BLs extraits")

    with open("output_cargo.json", "w", encoding="utf-8") as f:
        f.write(cargo_json)
    print("-> Fichier complet : output_cargo.json\n")
