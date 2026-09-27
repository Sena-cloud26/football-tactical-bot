"""
Excel Parser — membaca file squad/atribut pemain (format FM-style export atau custom)
dan mengubahnya menjadi ringkasan terstruktur yang bisa disisipkan ke prompt LLM.
"""

import pandas as pd


def load_squad_excel(file) -> pd.DataFrame:
    """Baca file Excel squad. Mendukung banyak sheet — pakai sheet pertama secara default."""
    df = pd.read_excel(file, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def summarize_squad(df: pd.DataFrame, max_rows: int = 40) -> str:
    """
    Ubah dataframe squad menjadi teks ringkas terstruktur untuk konteks LLM.
    Dibatasi max_rows agar tidak membengkakkan prompt (hemat token = kreatif tapi efisien).
    """
    if df.empty:
        return "Tidak ada data pemain."

    cols = list(df.columns)
    lines = [f"Kolom tersedia: {', '.join(cols)}", f"Total pemain: {len(df)}", ""]

    preview = df.head(max_rows)
    for _, row in preview.iterrows():
        parts = [f"{col}={row[col]}" for col in cols if pd.notna(row[col])]
        lines.append(" | ".join(parts))

    if len(df) > max_rows:
        lines.append(f"... dan {len(df) - max_rows} pemain lainnya (tidak ditampilkan agar ringkas).")

    return "\n".join(lines)


def basic_stats(df: pd.DataFrame) -> dict:
    """Statistik ringkas otomatis (opsional, untuk ditampilkan di UI sebagai insight cepat)."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    stats = {}
    for col in numeric_cols:
        stats[col] = {
            "rata-rata": round(df[col].mean(), 2),
            "tertinggi": df[col].max(),
            "terendah": df[col].min(),
        }
    return stats
