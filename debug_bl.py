import json
from reconciliation import reconcile_manifests
import pprint

sydam = json.load(open('output_sydam.json'))
cargo = json.load(open('output_cargo.json'))

diffs = reconcile_manifests(sydam, cargo, "SYDAM", "CARGO")

# Look specifically for conteneur differences for OOLU2318938980
print("Diffs for OOLU2318938980:")
for d in diffs:
    if "OOLU2318938980" in d.get("BL", "") and "Conteneur" in d.get("Contexte", ""):
        print(d)

print("\nDiffs for OOLU2165247280:")
for d in diffs:
    if "OOLU2165247280" in d.get("BL", "") and "Conteneur" in d.get("Contexte", ""):
        print(d)

