# Améliorations de l'Interface, Export Avancé et Filtrage Intelligent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Améliorer l'application Streamlit pour prendre en charge les rapports de réconciliation de grandes tailles (comme le ZOI), intégrer un export Excel avancé colorisé pour les différences, et ajouter un système de filtrage intelligent (ignorant les espaces blancs, abréviations connues et casses).

**Architecture:** Mettre à jour `reconciliation.py` pour nettoyer agressivement les chaînes de texte avant la comparaison (espaces multiples, ponctuation neutre). Créer une fonction dans le fichier principal `app.py` (ou importer via un utilitaire `export_excel.py`) qui génère un fichier `.xlsx` personnalisé via `openpyxl`. Mettre à jour l'UI de `app.py` pour présenter ces nouvelles options de filtrage et le bouton de téléchargement Excel.

**Tech Stack:** `Python 3`, `streamlit`, `pandas`, `openpyxl`, `pytest`

---

### Task 1: Installer `openpyxl` et configurer le projet pour Excel

**Files:**
- Modify: `requirements.txt`

**Step 1: Write the failing test**
Aucun test d'import à ce stade, mais nous préparons la suite pour l'export Excel.

**Step 2: Run test to verify it fails**
N/A

**Step 3: Write minimal implementation**
Ajouter `openpyxl` dans le fichier `requirements.txt`.

```text
openpyxl
```

**Step 4: Run test to verify it passes**
Lancer la ligne de commande pour installer la dépendance
Run: `pip install -r requirements.txt`
Expected: Installation réussie

**Step 5: Commit**
```bash
git add requirements.txt
git commit -m "build: ajouter openpyxl pour l'export Excel"
```

---

### Task 2: Ajouter une logique de nettoyage avancée (Filtrage) dans `reconciliation.py`

**Files:**
- Modify: `reconciliation.py`
- Test: `test_reconciliation.py`

**Step 1: Write the failing test**

```python
# Fichier: test_reconciliation.py
from reconciliation import reconcile_manifests

def test_reconcile_cleans_strings():
    data1 = {
        "navire": "ZOI", "numero_voyage": "604W", "eta": "05/03/2026",
        "ports": {"POL1": {"bls": {"123": {
            "shipper": "GAPUMA COTE D'IVOIRE",
            "consignee": "HONGKONG SPLENDID TRADE LTD.",
            "designation": "MOTORCYCLE CKD",
            "conteneurs": {}
        }}}}
    }
    data2 = {
        "navire": "zoi ", "numero_voyage": "604W", "eta": "05/03/2026",
        "ports": {"POL1": {"bls": {"123": {
            "shipper": "GAPUMA  COTE D IVOIRE",
            "consignee": "HONG KONG SPLENDID TRADE LIMITED",
            "designation": " MOTORCYCLE  C.K.D. ",
            "conteneurs": {}
        }}}}
    }
    
    # Avec les règles avancées, Shipper, Consignee et Désignation devraient correspondre.
    diffs = reconcile_manifests(data1, data2)
    diff_champs = [d["Champ"] for d in diffs]
    
    assert "Navire" not in diff_champs
    assert "Shipper" not in diff_champs
    assert "Consignee" not in diff_champs
    assert "Désignation" not in diff_champs
```

**Step 2: Run test to verify it fails**
Run: `pytest test_reconciliation.py -v`
Expected: FAIL. Le test échouera car "HONGKONG SPLENDID TRADE LTD." et "HONG KONG SPLENDID TRADE LIMITED" seront levés comme différences.

**Step 3: Write minimal implementation**
Modifier `reconciliation.py` pour étendre la fonction interne `_str(v)` :
- Supprimer la ponctuation (',', '.', '-', '_')
- Extra-spaces `re.sub(r'\s+', ' ', text)`
- Transformer 'LTD' en 'LIMITED', 'C.K.D' en 'CKD', etc.

```python
# Dans reconciliation.py
import re

def _clean_text(text: str) -> str:
    """Nettoie agressivement le texte pour la comparaison sémantique."""
    if not isinstance(text, str):
        return text
    
    # Passage en majuscules et remplacement tirets/pontuations
    t = str(text).upper()
    t = re.sub(r'[\.,_\-\']', ' ', t)
    
    # Remplacement d'abréviations communes
    abrevs = {
        r'\bLTD\b': 'LIMITED',
        r'\bCO\b': 'COMPANY',
        r'\bCORP\b': 'CORPORATION',
        r'\bINC\b': 'INCORPORATED',
    }
    for k, v in abrevs.items():
        t = re.sub(k, v, t)
        
    # Nettoyage espaces multiples et finaux
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def reconcile_manifests(data1: dict, data2: dict,
                        label1: str = "Valeur 1",
                        label2: str = "Valeur 2") -> list:
    # ...
    # Remplacer def _str(v):
    def _str(v) -> str:
        if v is None: return ""
        return _clean_text(v)
    # ... 
```

**Step 4: Run test to verify it passes**
Run: `pytest test_reconciliation.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add reconciliation.py test_reconciliation.py
git commit -m "feat: ajout du nettoyage sémantique global sur les strings comparées"
```

---

### Task 3: Créer la logique d'export Excel Avancé (Cellules colorées)

**Files:**
- Create: `utils_export.py`

**Step 1: Write the failing test**

```python
# Fichier: test_export.py
import os
import pandas as pd
from utils_export import generate_excel_diff_report

def test_generate_excel():
    diffs = [
        {"Contexte": "BL", "Identifiant": "123", "Champ": "Shipper", "Valeur 1": "A", "Valeur 2": "B"}
    ]
    filepath = "rapport_test.xlsx"
    generate_excel_diff_report(diffs, filepath)
    
    assert os.path.exists(filepath)
    df = pd.read_excel(filepath)
    assert len(df) == 1
    os.remove(filepath)
```

**Step 2: Run test to verify it fails**
Run: `pytest test_export.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'utils_export'`

**Step 3: Write minimal implementation**

```python
# Fichier: utils_export.py
import pandas as pd
from openpyxl.styles import PatternFill

def generate_excel_diff_report(differences: list, output_path: str):
    """"Génère un export xlsx propre à partir des différences, avec code couleur rouge."""
    if not differences:
        pd.DataFrame([{"Message": "Aucune différence"}]).to_excel(output_path, index=False)
        return

    df = pd.DataFrame(differences)
    # On écrit avec openpyxl
    writer = pd.ExcelWriter(output_path, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Différences')
    
    workbook = writer.book
    worksheet = writer.sheets['Différences']
    
    # Fond rouge pastel pour les décalages ("Valeur 1" et "Valeur 2")
    red_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    
    # Application du code couleur aux deux dernières colonnes itérativement
    for row in range(2, len(df) + 2):
        cell1 = worksheet.cell(row=row, column=len(df.columns) - 1)
        cell2 = worksheet.cell(row=row, column=len(df.columns))
        if cell1.value != cell2.value:
             cell1.fill = red_fill
             cell2.fill = red_fill
             
    # Ajuster la largeur des colonnes
    for column_cells in worksheet.columns:
        length = max(len(str(cell.value) or "") for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 60)
        
    writer.close()
```

**Step 4: Run test to verify it passes**
Run: `pytest test_export.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add utils_export.py test_export.py
git commit -m "feat: ajouter export excel avancé stylisé"
```

---

### Task 4: Intégrer la logique et UI d'Excel Report dans `app.py`

**Files:**
- Modify: `app.py`

**Step 1: Write the failing test**
Les tests e2e Streamlit ne sont pas présents ici. On va s'assurer que notre script a incorporé `openpyxl` et génère le buffer Excel.

**Step 2: Run test to verify it fails**
N/A

**Step 3: Write minimal implementation**

Modifier `app.py` pour importer `generate_excel_diff_report` et remplacer le bouton "Télécharger CSV" par "Télécharger Rapport EXCEL".

```python
# Dans app.py, vers le haut :
from utils_export import generate_excel_diff_report
import tempfile
import os

# Vers la ligne 475, où il y a le CSV :
# Retirer/remplacer: csv = df_diff.to_csv(...) st.download_button("Télécharger ... CSV")

# Ajouter :
with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    tmp_path = tmp.name

generate_excel_diff_report(differences, tmp_path)

with open(tmp_path, "rb") as exc:
    xls_data = exc.read()

st.download_button(
    label="📥 Télécharger le rapport Excel detaillé",
    data=xls_data,
    file_name="differences_manifeste.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
os.remove(tmp_path)
```

**Step 4: Run test to verify it passes**
Run: `python -m streamlit run app.py` en fond, vérifier manuellement si le bouton "Télécharger le rapport Excel" interagit de manière cohérente sans crash. (Le développeur le fera dans son environnement).

**Step 5: Commit**
```bash
git add app.py
git commit -m "feat: ajouter le format xlsx pour le telechargement de la reconciliation"
```
