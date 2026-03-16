# Refactoring Parseurs PDF avec layout=True Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ré-écrire logiciellement les fonctions `parse_cargo` et `parse_sydam` en s'appuyant sur la compétence `lecteur-pdf`, c'est-à-dire en utilisant `layout=True` pour extraire des lignes respectant l'espacement visuel et en séparant les colonnes (Shipper vs. Consignee/Désignation) avec des regex basées sur les espacements massifs (`\s{4,}`).

**Architecture:** Modificaton de `page.extract_text()` à `page.extract_text(layout=True)` puis adaptation de chaque parseur pour exploiter l'espacement via expressions régulières (ex: `re.split(r'\s{4,}', line)`). On corrigera les erreurs éventuelles sur les anciens parseurs qui s'attendaient à un flux continu de textes cassés.

**Tech Stack:** `Python 3`, `pdfplumber`, `re`

---

### Task 1: Mettre à jour `parser_cargo.py` (Layout & Slicing)

**Files:**
- Modify: `parser_cargo.py`
- Test: `test_parsers.py`

**Step 1: Write the failing test**

```python
# Fichier de test: test_parsers.py
from parser_cargo import parse_cargo

def test_cargo_shipper_extraction_layout():
    # Avec l'ancien parseur, l'utilisation de layout=True briserait la logique de ' . ' pour séparer les colonnes
    c = parse_cargo("CARGO ZOI.pdf")
    bl = list(list(c["ports"].values())[0]["bls"].values())[0]
    shipper = bl.get("shipper", "")
    
    # On s'assure qu'on n'a pas inclus la colonne de droite "VOLUME:" ou "KG" dans le shipper
    assert "VOLUME" not in shipper
    assert len(shipper) > 10, "Shipper doit être trouvé correctement"
```

**Step 2: Run test to verify it fails**
Run: `pytest test_parsers.py::test_cargo_shipper_extraction_layout -v`
Expected: FAIL avec le test bloqué sur "VOLUME" car le vieux parseur fusionne tout dans `layout=True`.

**Step 3: Write minimal implementation**
Modifier `parser_cargo.py` :
1. Ligne 151: `txt = page.extract_text(layout=True)`
2. Dans `_extract_name_from_shipper_line`, remplacer la logique par un split d'espaces :
```python
            # Coupure par grands espaces si ça croise une autre colonne
            parts = re.split(r'\s{5,}', sl)
            sl = parts[0] if parts else ""
```

**Step 4: Run test to verify it passes**
Run: `pytest test_parsers.py::test_cargo_shipper_extraction_layout -v`
Expected: PASS

**Step 5: Commit**
```bash
git add parser_cargo.py
git commit -m "refactor(cargo): utiliser extract_text(layout=True) comme recommandé par lecteur-pdf"
```

---

### Task 2: Mettre à jour `parser_sydam.py` (Layout et Séparation par colonnes)

**Files:**
- Modify: `parser_sydam.py`
- Test: `test_parsers.py`

**Step 1: Write the failing test**

```python
# Fichier de test: test_parsers.py
from parser_sydam import parse_sydam

def test_sydam_shipper_designation_separation():
    s = parse_sydam("SYDAM ZOI.pdf")
    bl = list(list(s["ports"].values())[0]["bls"].values())[0]
    shipper = bl.get("shipper", "")
    
    # Sans layout=True de SYDAM, le texte de Designation (ex: PK PLASTIC ou SOLID) 
    # se retrouve mélangé dans Shipper par the parser qui accumule tout.
    assert "PLASTIC" not in shipper
    assert "CONTAINS NO" not in shipper
```

**Step 2: Run test to verify it fails**
Run: `pytest test_parsers.py::test_sydam_shipper_designation_separation -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Modifier `parser_sydam.py` :
1. Ligne 206: `txt = page.extract_text(layout=True)`
2. Mettre à jour la logique d'état pour le Shipper / Marchandise :
```python
        # Remplacer les appels de fusion s'il y a de grands espaces
        # Extraire Shipper à gauche, Marchandise à droite...
        parts = re.split(r'\s{4,}', line)
        if len(parts) >= 2:
            left_part = parts[0].strip()
            right_part = parts[1].strip()
            if left_part and state_dict["current_bl"]: ...
```
(On injecte la structure de `lecteur-pdf` explicitement sur les lignes sans préfixe).

**Step 4: Run test to verify it passes**
Run: `pytest test_parsers.py::test_sydam_shipper_designation_separation -v`
Expected: PASS

**Step 5: Commit**
```bash
git add parser_sydam.py
git commit -m "refactor(sydam): separer shipper et designation avec layout=True"
```
