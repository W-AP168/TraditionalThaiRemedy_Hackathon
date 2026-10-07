"""ค้นหาตำรับยา: จากอาการ หรือจากรหัสตำรับ (ข้อมูล 3 คัมภีร์ × 2 ไฟล์)

วิธีใช้:  python Application_search_remedy.py [โฟลเดอร์ที่มีไฟล์ CSV]
"""

import sys

import pandas as pd

from remedy_data import check_data, load_data

HERBS = pd.DataFrame()
SYMPTOMS = pd.DataFrame()


def load(data_dir="."):
    global HERBS, SYMPTOMS
    print("⏳ กำลังโหลดฐานข้อมูล...")
    HERBS, SYMPTOMS = load_data(data_dir)
    print(f"✅ {HERBS['รหัสตำรับ'].nunique()} ตำรับ · {HERBS['ชื่อสมุนไพร'].nunique()} สมุนไพร · "
          f"{SYMPTOMS['อาการ'].nunique()} อาการ")
    for note in check_data(HERBS, SYMPTOMS):
        print("⚠️", note)


def _print_ingredients(recipe_id):
    ing = HERBS[HERBS["รหัสตำรับ"] == recipe_id]
    print(f"🌿 ส่วนประกอบสมุนไพร ({len(ing)} ชนิด):")
    for _, item in ing.iterrows():
        sci = f" (ชื่อวิทย์: {item['ชื่อวิทยาศาสตร์']})" if item["ชื่อวิทยาศาสตร์"] else ""
        print(f"   - {item['ชื่อสมุนไพร']}{sci}")


# ==========================================
# โหมดที่ 1: ค้นหาจากอาการ
# ==========================================
def search_by_symptoms(symptoms_list, top_n=3, partial=False, show=True):
    """คืนตาราง (DataFrame) ตำรับที่ตรงกับอาการ เรียงจากตรงมากไปน้อย

    partial=False (ค่าเริ่มต้น): ชื่ออาการต้องตรงกันทั้งคำ
    partial=True: ยอมให้ตรงบางส่วน เช่น "ไข้" เจอ "ไข้ตัวร้อน"
                  (ระวัง: "ตา" จะไปเจอ "ปวดตามข้อ" ด้วย)
    """
    wanted = [s.strip() for s in symptoms_list if s.strip()]
    rows = []
    for recipe_id, have in SYMPTOMS.groupby("รหัสตำรับ")["อาการ"]:
        have = set(have)
        if partial:
            matched = [w for w in wanted if any(w in h for h in have)]
        else:
            matched = [w for w in wanted if w in have]
        if matched:
            rows.append({
                "รหัสตำรับ": recipe_id,
                "อาการที่ตรง": matched,
                "จำนวนที่ตรง": len(matched),
                # ความสอดคล้อง = ตรงกี่ % ของอาการที่ค้นหา (ไม่ใช่ประสิทธิผลการรักษา)
                "ความสอดคล้อง": len(matched) / len(wanted),
                # ใช้ตัดสินเมื่อคะแนนเท่ากัน: ตำรับที่เน้นอาการนี้ (มีอาการอื่นน้อย) ขึ้นก่อน
                "ความเฉพาะ": len(matched) / len(have | set(wanted)),
            })
    results = pd.DataFrame(rows)
    if results.empty:
        if show:
            print(f"\n🔍 อาการ: {', '.join(wanted)}\n❌ ไม่พบตำรับที่ตรงกับอาการเหล่านี้")
        return results
    results = results.sort_values(["ความสอดคล้อง", "ความเฉพาะ"], ascending=False, ignore_index=True)

    if show:
        print(f"\n🔍 [ค้นหาจากอาการ] {', '.join(wanted)} → พบ {len(results)} ตำรับ "
              f"แสดง {min(top_n, len(results))} อันดับแรก\n")
        for i, r in results.head(top_n).iterrows():
            print("=" * 50)
            print(f"🏆 อันดับที่ {i + 1}")
            print(f"📌 รหัสตำรับ: {r['รหัสตำรับ']}")
            print(f"💡 ตรงกับอาการ: {', '.join(r['อาการที่ตรง'])} "
                  f"(ความสอดคล้อง {r['ความสอดคล้อง']:.0%})")
            _print_ingredients(r["รหัสตำรับ"])
        print("=" * 50)
    return results


# ==========================================
# โหมดที่ 2: ค้นหาจากรหัสตำรับ
# ==========================================
def search_by_recipe_id(target_id, show=True):
    """คืน (อาการ, สมุนไพร) ของตำรับนี้ หรือ None ถ้าไม่พบ"""
    target_id = target_id.strip()
    ing = HERBS[HERBS["รหัสตำรับ"] == target_id]
    sym = SYMPTOMS.loc[SYMPTOMS["รหัสตำรับ"] == target_id, "อาการ"].tolist()
    if ing.empty and not sym:
        if show:
            print(f"\n🔍 รหัส '{target_id}' ❌ ไม่พบในฐานข้อมูล")
        return None
    if show:
        print("=" * 50)
        print(f"📌 รหัสตำรับ: {target_id}  (คัมภีร์ {target_id.rstrip('0123456789/')})")
        print(f"💡 สรรพคุณ/แก้อาการ: {', '.join(sym) if sym else 'ไม่ระบุ'}")
        _print_ingredients(target_id)
        print("=" * 50)
    return sym, ing


if __name__ == "__main__":
    load(sys.argv[1] if len(sys.argv) > 1 else ".")
    # 🟢 ทดลองใช้: เปลี่ยนอาการ/รหัสในวงเล็บได้เลย
    search_by_symptoms(["ไข้", "ไอ"])
    search_by_recipe_id("WRO133/1")
    search_by_recipe_id("NR007/1")
