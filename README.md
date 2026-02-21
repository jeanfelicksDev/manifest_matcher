# Manifest Matcher - Contr\N{LATIN SMALL LETTER O}le Fichier SYDAM

Application locale bas\N{LATIN SMALL LETTER E}e sur Streamlit (Python) permettant de r\N{LATIN SMALL LETTER E}concilier et comparer automatiquement un Manifeste Douanier sous format **XML** avec son \N{LATIN SMALL LETTER E}quivalent sous format **PDF**.

## 🚀 Fonctionnalit\N{LATIN SMALL LETTER E}s
- Interface web intuitive avec interface Drag & Drop (Style Duolingo)
- Extraction automatique des donn\N{LATIN SMALL LETTER E}es du XML (Navire, Port, BLs, Conteneurs, Poids)
- Extraction NLP du tableau PDF avec la librairie `pdfplumber`
- Comparatif ligne \N{LATIN SMALL LETTER A} ligne et aggr\N{LATIN SMALL LETTER E}gation de poids par port
- Export des diff\N{LATIN SMALL LETTER E}rences en fichier `.csv` pour audit

## ⚙️ Installation

1. Assurez-vous d'avoir Python 3 install\N{LATIN SMALL LETTER E}.
2. Clonez ce r\N{LATIN SMALL LETTER E}pertoire.
3. Cr\N{LATIN SMALL LETTER E}ez un environnement virtuel et installez les d\N{LATIN SMALL LETTER E}pendances :
   ```bash
   python -m venv venv
   # Activation sous Windows
   .\venv\Scripts\Activate.ps1   
   
   pip install streamlit pandas xmltodict pdfplumber
   ```

## 🖥️ Utilisation

Lancez le serveur localement :
```bash
python -m streamlit run app.py
```
L'application s'ouvrira dans votre navigateur.
