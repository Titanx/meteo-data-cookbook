import pdfplumber

PDF = r"c:\work\meteo\news\WIND-Bench_arXiv2026\wind_bench_2609.12228.pdf"
OUT = r"c:\work\meteo\news\WIND-Bench_arXiv2026\paper_fulltext.txt"

with pdfplumber.open(PDF) as pdf:
    n = len(pdf.pages)
    parts = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        parts.append(f"\n===== PAGE {i+1} =====\n{text}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))

print(f"pages: {n}")
print(f"saved: {OUT}")
