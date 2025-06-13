import streamlit as st
import easyocr
from PIL import Image
import os
import re
import pandas as pd
import xml.etree.ElementTree as ET

# OCR cu EasyOCR compatibil Streamlit Cloud
reader = easyocr.Reader(['ro'], gpu=False)

# UI Streamlit
st.set_page_config(page_title="Extractor Facturi", layout="centered")
st.title("📄 Extractor de date din facturi (PDF / imagine)")

uploaded_file = st.file_uploader("Încarcă factura (doar imagine deocamdată)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.info("📥 Procesez imaginea...")
    image = Image.open(uploaded_file)
    text_extras = reader.readtext(image, detail=0, paragraph=True)
    text_extras = "\n".join(text_extras)

    st.success("✅ Text extras din imagine:")
    st.text_area("📑 Conținut detectat:", text_extras, height=250)

    # Extragem date simple
    numar = re.search(r"nr\.?\s*(\S+)", text_extras, re.IGNORECASE)
    cui = re.search(r"C\.I\.F\.?\s*(RO?\d+)", text_extras, re.IGNORECASE)
    total = re.search(r"(\d+[\.,]\d{2})\s*RON", text_extras)
    furnizor = re.search(r"Furnizor\:?\s*(.*?)\s*(?:/|\\n)", text_extras)
    data = re.search(r"(\d{2}\.\d{2}\.\d{4})", text_extras)

    date_factura = {
        "Număr Factură": numar.group(1) if numar else "-",
        "Data": data.group(1) if data else "-",
        "Furnizor": furnizor.group(1).strip() if furnizor else "-",
        "CUI": cui.group(1) if cui else "-",
        "Total RON": total.group(1).replace(",", ".") if total else "-"
    }

    st.subheader("📋 Date extrase:")
    st.write(date_factura)

    # Extragem produse (format: Denumire x Cantitate x Preț)
    produse = []
    linii = text_extras.split('\n')
    for linie in linii:
        linie = linie.strip()
        match = re.search(r"(.+?)\s+(\d+)\s+x\s+(\d+[\.,]\d{2})", linie)
        if match:
            denumire = match.group(1).strip()
            cantitate = int(match.group(2))
            pret_unitar = float(match.group(3).replace(",", "."))
            pret_total = round(cantitate * pret_unitar, 2)
            produse.append({
                "Denumire Produs": denumire,
                "Cantitate": str(cantitate),
                "Preț Unitar": f"{pret_unitar:.2f}",
                "Preț Total": f"{pret_total:.2f}"
            })

    if produse:
        st.subheader("📦 Produse detectate:")
        st.write(produse)

    # Export Excel + XML
    os.makedirs("facturi-export", exist_ok=True)
    excel_path = os.path.join("facturi-export", f"{date_factura['Număr Factură']}.xlsx")
    xml_path = os.path.join("facturi-export", f"{date_factura['Număr Factură']}.xml")

    with pd.ExcelWriter(excel_path) as writer:
        pd.DataFrame([date_factura]).to_excel(writer, sheet_name="Date Factura", index=False)
        if produse:
            pd.DataFrame(produse).to_excel(writer, sheet_name="Produse", index=False)

    root = ET.Element("Factura")
    for k, v in date_factura.items():
        ET.SubElement(root, k.replace(" ", "_")).text = v

    if produse:
        produse_elem = ET.SubElement(root, "Produse")
        for prod in produse:
            p_elem = ET.SubElement(produse_elem, "Produs")
            for k, v in prod.items():
                ET.SubElement(p_elem, k.replace(" ", "_")).text = v

    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    st.success("📤 Export realizat în folderul facturi-export!")
    with open(excel_path, "rb") as f:
        st.download_button("⬇️ Descarcă Excel", f, file_name=os.path.basename(excel_path), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with open(xml_path, "rb") as f:
        st.download_button("⬇️ Descarcă XML", f, file_name=os.path.basename(xml_path), mime="application/xml")
