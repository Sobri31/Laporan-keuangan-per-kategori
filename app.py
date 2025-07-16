
import streamlit as st
import pdfplumber
import re
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Laporan Dana Otomatis", layout="wide")

st.title("📄 Aplikasi Otomatisasi Laporan Dana")

uploaded_file = st.file_uploader("Unggah file PDF laporan", type=["pdf"])

# Kata kunci default
default_keywords = ["baut", "trass", "dinabol", "alat listrik", "klip wpc", "downled"]

user_keywords = st.text_area(
    "🛠️ Tambahkan kata kunci untuk kategori 'Baut, Trass, Dinabol' (pisahkan dengan koma)",
    value=", ".join(default_keywords),
    height=80
)

keywords = [k.strip().lower() for k in user_keywords.split(",") if k.strip()]

# Fungsi bantu parsing rupiah
def parse_rupiah(text):
    return int(text.replace("Rp", "").replace(".", "").replace(",", "").strip())

# Parsing data PDF
def extract_transactions(pdf_file):
    results = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            for i in range(len(lines) - 1):
                line = lines[i].strip()
                if re.match(r"\d{1,2}\s\w+\s2025", line):  # Cek baris tanggal
                    tanggal = line
                    deskripsi = lines[i + 1].strip()
                    jenis = "Keluar" if "Keluar" in deskripsi else "Masuk" if "Masuk" in deskripsi else ""
                    masuk = ""
                    keluar = ""
                    if jenis == "Keluar":
                        match = re.search(r"Rp[\d\.]+", deskripsi)
                        keluar = match.group(0) if match else ""
                    elif jenis == "Masuk":
                        match = re.search(r"Rp[\d\.]+", deskripsi)
                        masuk = match.group(0) if match else ""
                    if jenis:
                        results.append((tanggal, deskripsi, jenis, masuk, keluar))
    return results

# Buat tabel PDF hasil
def create_pdf(data_by_category):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Laporan Kategori Pengeluaran", ln=True, align='C')
    pdf.ln(10)

    for category, rows in data_by_category.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, category, ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 8, "Tanggal", 1)
        pdf.cell(90, 8, "Deskripsi", 1)
        pdf.cell(30, 8, "Masuk", 1)
        pdf.cell(30, 8, "Keluar", 1)
        pdf.ln()
        total = 0
        pdf.set_font("Arial", '', 10)
        for row in rows:
            pdf.cell(40, 8, row[0], 1)
            pdf.cell(90, 8, row[1][:40], 1)
            pdf.cell(30, 8, row[3] if row[3] else "-", 1)
            pdf.cell(30, 8, row[4] if row[4] else "-", 1)
            pdf.ln()
            if row[4]:
                try:
                    total += parse_rupiah(row[4])
                except:
                    pass
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(160, 8, "TOTAL", 1)
        pdf.cell(30, 8, f"Rp{total:,.0f}".replace(",", "."), 1)
        pdf.ln(10)

    out_pdf = BytesIO()
    pdf.output(out_pdf)
    out_pdf.seek(0)
    return out_pdf

if uploaded_file:
    data = extract_transactions(uploaded_file)
    data = [d for d in data if d[2] == "Keluar"]
    data = [d for d in data if not any(k in d[1].lower() for k in ["tes", "titipan", "salah input"])]

    kategori_v = [d for d in data if "v" in d[1].lower()]
    kategori_transfer = [d for d in data if any(k in d[1].lower() for k in ["transfer", "setor", "setoran bagus"])]
    kategori_baut = [d for d in data if any(k in d[1].lower() for k in keywords)]
    kategori_bon = [d for d in data if "bon" in d[1].lower()]
    kategori_lain = [d for d in data if d not in kategori_v and d not in kategori_transfer and d not in kategori_baut and d not in kategori_bon]

    data_by_category = {
        "Kategori: V": kategori_v,
        "Kategori: Transfer & Setor Mandiri": kategori_transfer,
        "Kategori: Baut, Trass, Dinabol, dll": kategori_baut,
        "Kategori: Bon": kategori_bon,
        "Kategori: Pengeluaran Lainnya": kategori_lain
    }

    st.success("✅ Transaksi berhasil diproses!")
    for name, rows in data_by_category.items():
        st.subheader(name)
        st.table(rows)

    pdf_file = create_pdf(data_by_category)
    st.download_button("📥 Unduh Hasil sebagai PDF", data=pdf_file, file_name="Laporan_Hasil.pdf")
