"""Apriori จากข้อมูล 3 คัมภีร์ × 2 ไฟล์ CSV

แยกวิเคราะห์ 2 แบบ (ไม่ปนกัน):
  1. สมุนไพร ↔ สมุนไพร   : ตำรับมีสมุนไพร A มักมี B ด้วยไหม
  2. อาการ → สมุนไพร     : ตำรับแก้อาการ X มักใช้สมุนไพร B ไหม
อาการติดป้าย "อาการ:" ไว้ ชื่ออาการจะได้ไม่ชนกับชื่อสมุนไพร

วิธีใช้:  python Database.py [โฟลเดอร์ที่มีไฟล์ CSV]
"""

import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from mlxtend.frequent_patterns import apriori, association_rules

from remedy_data import check_data, load_data

MIN_SUPPORT = 0.02      # พบในอย่างน้อย 2% ของตำรับ
MIN_CONFIDENCE = 0.3
MIN_LIFT = 1.0
MAX_LEN = 3             # จำกัดขนาดกลุ่ม ไม่ให้ช้า/หน่วยความจำเต็ม
PAIR = ("ขิง", "ดีปลี")  # ถ้ามีไฟล์ชื่อพ้อง ขิงแห้ง จะถูกรวมเป็น ขิง
SYMPTOM_TAG = "อาการ:"


def binary_matrix(herbs, symptoms=None):
    """ตาราง ตำรับ × รายการ (True/False) 1 แถว = 1 ตำรับ"""
    items = herbs[["รหัสตำรับ", "ชื่อสมุนไพร"]].rename(columns={"ชื่อสมุนไพร": "item"})
    if symptoms is not None:
        s = symptoms[["รหัสตำรับ", "อาการ"]].rename(columns={"อาการ": "item"})
        items = pd.concat([items, s.assign(item=SYMPTOM_TAG + s["item"])], ignore_index=True)
    return pd.crosstab(items["รหัสตำรับ"], items["item"]).astype(bool)


def run_rules(matrix, keep):
    frequent = apriori(matrix, min_support=MIN_SUPPORT, use_colnames=True, max_len=MAX_LEN)
    print(f"   itemsets ที่ผ่านเกณฑ์: {len(frequent)}")
    if frequent.empty:
        print("   ⚠️ ไม่พบ ลองลด MIN_SUPPORT")
        return pd.DataFrame()
    rules = association_rules(frequent, metric="lift", min_threshold=MIN_LIFT)
    # ฝั่งขวาเหลือ 1 รายการ อ่านง่ายกว่า "A → B + C"
    rules = rules[rules["consequents"].map(len) == 1]
    rules = rules[(rules["confidence"] >= MIN_CONFIDENCE) & rules.apply(keep, axis=1)]
    rules = rules.sort_values(["lift", "confidence"], ascending=False)
    # frozenset({'ขิง'}) → "ขิง" ให้อ่านง่ายใน Excel
    out = rules[["antecedents", "consequents", "support", "confidence", "lift"]].copy()
    for col in ("antecedents", "consequents"):
        out[col] = out[col].map(lambda s: " + ".join(sorted(s)))
    out.insert(2, "จำนวนตำรับ", (rules["support"] * len(matrix)).round().astype(int))
    return out.reset_index(drop=True)


def is_herb(name):
    return not name.startswith(SYMPTOM_TAG)


def thai_font():
    for name in ("Tahoma", "Leelawadee UI", "Sarabun", "TH Sarabun New", "Noto Sans Thai", "Thonburi", "Loma"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            return name
    return None


def main(data_dir="."):
    herbs, symptoms = load_data(data_dir)
    n = herbs["รหัสตำรับ"].nunique()
    print(f"รวมข้อมูลสำเร็จ: {n} ตำรับ · {herbs['ชื่อสมุนไพร'].nunique()} สมุนไพร · "
          f"{symptoms['อาการ'].nunique()} อาการ")
    for note in check_data(herbs, symptoms):
        print("⚠️", note)

    # ---- 1. สมุนไพร ↔ สมุนไพร ----
    print("\n[1] สมุนไพร ↔ สมุนไพร")
    herb_rules = run_rules(binary_matrix(herbs), lambda r: True)
    print(herb_rules.head(10).to_string())
    herb_rules.to_csv("Apriori_Rules_Herb_Herb.csv", index=False, encoding="utf-8-sig")

    # ---- 2. อาการ → สมุนไพร ----
    print("\n[2] อาการ → สมุนไพร")
    sym_rules = run_rules(
        binary_matrix(herbs, symptoms),
        lambda r: all(not is_herb(i) for i in r["antecedents"]) and all(is_herb(i) for i in r["consequents"]),
    )
    print(sym_rules.head(10).to_string())
    sym_rules.to_csv("Apriori_Rules_Symptom_Herb.csv", index=False, encoding="utf-8-sig")
    print("\n✅ บันทึก Apriori_Rules_Herb_Herb.csv และ Apriori_Rules_Symptom_Herb.csv")

    # ---- 3. เจาะลึก: ขิงแห้ง + ดีปลี ใช้กับอาการอะไร ----
    a, b = PAIR
    print(f"\n--- เจาะลึก: {a} & {b} ---")
    has = herbs.groupby("รหัสตำรับ")["ชื่อสมุนไพร"].apply(set)
    both = has[has.map(lambda s: a in s and b in s)].index
    print(f"พบตำรับที่มีทั้ง {a} และ {b}: {len(both)} ตำรับ")
    # symptoms ไม่มีแถวซ้ำแล้ว → 1 อาการนับ 1 ครั้งต่อ 1 ตำรับ
    counts = symptoms[symptoms["รหัสตำรับ"].isin(both)]["อาการ"].value_counts().reset_index()
    counts.columns = ["อาการที่รักษา", "จำนวนตำรับที่พบ"]
    print(counts.head(10).to_string())
    counts.to_csv("Symptoms_Khing_Deepli.csv", index=False, encoding="utf-8-sig")

    if counts.empty:
        return
    font = thai_font()
    if font:
        plt.rcParams["font.family"] = font
    else:
        print("⚠️ ไม่พบฟอนต์ไทยในเครื่อง ตัวอักษรในกราฟอาจเป็นกล่อง")
    top10 = counts.head(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=top10, x="จำนวนตำรับที่พบ", y="อาการที่รักษา", color="#1F4D3A")
    plt.title(f'Top 10 อาการในตำรับที่มี "{a}" และ "{b}" ({len(both)} ตำรับ)', fontsize=16, pad=15)
    plt.xlabel("จำนวนตำรับ", fontsize=12)
    plt.ylabel("อาการ", fontsize=12)
    plt.savefig("Symptoms_Khing_Deepli_Chart.png", dpi=300, bbox_inches="tight")
    print("✅ บันทึกกราฟ Symptoms_Khing_Deepli_Chart.png")
    if plt.get_backend().lower() != "agg":
        plt.show()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
