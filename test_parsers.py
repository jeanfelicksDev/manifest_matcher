import json
from parser_sydam import parse_sydam
from parser_cargo import parse_cargo

# ===== TEST SYDAM =====
print("=" * 60)
print("TEST SYDAM.pdf")
print("=" * 60)
data = parse_sydam("SYDAM.pdf")
print("Navire       :", data["navire"])
print("Voyage       :", data["numero_voyage"])
print("ETA          :", data["eta"])
print("Nb ports     :", len(data["ports"]))
total_bls = sum(len(p["bls"]) for p in data["ports"].values())
print("Nb BLs total :", total_bls)
print()

shown = 0
for port, pdata in data["ports"].items():
    for bl, bdata in pdata["bls"].items():
        if shown >= 3:
            break
        print("  Port =", port, "| BL =", bl)
        print("    shipper    :", bdata["shipper"])
        print("    consignee  :", bdata["consignee"])
        print("    notify     :", bdata["notify"])
        print("    designation:", bdata["designation"])
        print("    conteneurs :")
        for ct_num, ct in bdata["conteneurs"].items():
            print("      ", ct_num, "type=", ct["type"],
                  "plomb=", ct["num_plomb"],
                  "colis=", ct["nbre_colis"],
                  "poids=", ct["poids_brut"])
        print()
        shown += 1
    if shown >= 3:
        break

# Sauvegarder JSON complet
with open("output_sydam.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("--> output_sydam.json ecrit")

print()
print("=" * 60)
print("TEST CARGO.pdf")
print("=" * 60)
data2 = parse_cargo("CARGO.pdf")
print("Navire       :", data2["navire"])
print("Voyage       :", data2["numero_voyage"])
print("ETA          :", data2["eta"])
print("Nb ports     :", len(data2["ports"]))
total_bls2 = sum(len(p["bls"]) for p in data2["ports"].values())
print("Nb BLs total :", total_bls2)
print()

shown2 = 0
for port, pdata in data2["ports"].items():
    for bl, bdata in pdata["bls"].items():
        if shown2 >= 3:
            break
        print("  Port =", port, "| BL =", bl)
        print("    shipper    :", bdata["shipper"])
        print("    consignee  :", bdata["consignee"])
        print("    notify     :", bdata["notify"])
        print("    designation:", bdata["designation"])
        print("    conteneurs :")
        for ct_num, ct in bdata["conteneurs"].items():
            print("      ", ct_num,
                  "type=", ct["type"],
                  "plomb=", ct["num_plomb"],
                  "colis=", ct["nbre_colis"],
                  "poids=", ct["poids_brut"],
                  "vol=", ct["volume"])
        print()
        shown2 += 1
    if shown2 >= 3:
        break

with open("output_cargo.json", "w", encoding="utf-8") as f:
    json.dump(data2, f, ensure_ascii=False, indent=2)
print("--> output_cargo.json ecrit")
