"""
Module: outlook_excel.py
Logique métier pour la synchronisation Outlook → Excel (Mesure Navire)
Intégré dans le projet manifest_matcher
"""

import re
from datetime import datetime, date

# win32com disponible uniquement sur Windows avec Outlook installé
try:
    import win32com.client
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

# ─── Configuration ────────────────────────────────────────────────────────────
SHEET_NAME = 'MESURE'
DATA_START  = 3   # Première ligne de données (après 2 lignes d'en-têtes)

# (TYPE, DIRECTION) → colonne Excel (1-based)
COLUMN_MAP = {
    ('TOP',       'IMPORT'): 5,   # E
    ('ZIP',       'IMPORT'): 6,   # F
    ('MANIFESTE', 'IMPORT'): 7,   # G
    ('TOP',       'EXPORT'): 8,   # H
    ('ZIP',       'EXPORT'): 9,   # I
    ('MANIFESTE', 'EXPORT'): 10,  # J
}

COL_LABELS = {
    5:  'TOP Import',
    6:  'ZIP Import',
    7:  'MANIFESTE Import',
    8:  'TOP Export',
    9:  'ZIP Export',
    10: 'MANIFESTE Export',
}

# Format d'objet : TOP IMPORT EA CETUS 012E ETA: 12-02-2026
SUBJECT_PATTERN = re.compile(
    r'^(TOP|ZIP|MANIFESTE)\s+(IMPORT|EXPORT)\s+(.+?)\s+([A-Z0-9]+[A-Z])\s+ETA[:\s]',
    re.IGNORECASE
)
# ──────────────────────────────────────────────────────────────────────────────


def build_navire_map(ws) -> dict:
    """Construit un dict (NAVIRE, VOY) -> numéro de ligne Excel."""
    navire_map = {}
    for row in range(DATA_START, ws.max_row + 1):
        navire = ws.cell(row=row, column=1).value
        voy    = ws.cell(row=row, column=2).value
        if navire and voy:
            key = (str(navire).strip().upper(), str(voy).strip().upper())
            navire_map[key] = row
    return navire_map


def format_date(dt):
    """Convertit pywintypes.datetime / datetime en date Python."""
    if dt is None:
        return None
    try:
        return date(dt.year, dt.month, dt.day)
    except Exception:
        if isinstance(dt, datetime):
            return dt.date()
        return None


def get_all_folders(folder, depth=0, max_depth=4):
    """Parcours récursif des dossiers Outlook."""
    folders = [folder]
    if depth < max_depth:
        try:
            for sub in folder.Folders:
                folders.extend(get_all_folders(sub, depth + 1, max_depth))
        except Exception:
            pass
    return folders


def fetch_outlook_emails() -> tuple[list, str | None]:
    """
    Se connecte à Outlook et retourne (liste_emails, erreur|None).
    Chaque email est un dict : type, direction, navire, voy, date, subject.
    """
    if not OUTLOOK_AVAILABLE:
        return [], "win32com non disponible — lancez l'application en local sur Windows."

    try:
        outlook   = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
    except Exception as e:
        return [], str(e)

    folders_to_search = []
    try:
        for i in range(1, namespace.Stores.Count + 1):
            store = namespace.Stores.Item(i)
            root  = store.GetRootFolder()
            folders_to_search.extend(get_all_folders(root))
    except Exception:
        pass

    if not folders_to_search:
        try:
            folders_to_search.append(namespace.GetDefaultFolder(6))  # Boîte de réception
            folders_to_search.append(namespace.GetDefaultFolder(5))  # Éléments envoyés
        except Exception:
            pass

    found = []
    for folder in folders_to_search:
        try:
            for item in folder.Items:
                try:
                    subject = getattr(item, 'Subject', None)
                    if not subject:
                        continue
                    m = SUBJECT_PATTERN.match(subject.strip())
                    if m:
                        sent_on  = getattr(item, 'SentOn', None) or getattr(item, 'ReceivedTime', None)
                        found.append({
                            'type':      m.group(1).strip().upper(),
                            'direction': m.group(2).strip().upper(),
                            'navire':    m.group(3).strip().upper(),
                            'voy':       m.group(4).strip().upper(),
                            'date':      format_date(sent_on),
                            'subject':   subject,
                        })
                except Exception:
                    continue
        except Exception:
            continue

    return found, None
