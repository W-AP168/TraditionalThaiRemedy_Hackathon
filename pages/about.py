import streamlit as st

import ui

st.title("เกี่ยวกับโครงการ")
st.markdown(
    """
**ตำรับยาไทย** เป็นแพลตฟอร์มที่เชื่อมระหว่าง

คัมภีร์โบราณ → ข้อมูลมีโครงสร้าง → การค้นพบทางสถิติ → การตีความโดยมนุษย์

### เราถามอะไร
หมอยาไทยโบราณใช้สมุนไพรบางคู่ร่วมกันซ้ำ ๆ มากกว่าที่ความบังเอิญจะอธิบายได้หรือไม่?

### วิธีการ
1. แปลงตำรับเป็น **binary matrix** (ตำรับ × สมุนไพร)
2. ใช้ **Apriori** หาคู่ที่ปรากฏร่วมกันบ่อย (support, confidence, lift)
3. ทดสอบแต่ละคู่ด้วย **permutation test** และปรับ multiple testing ด้วย **FDR (Benjamini–Hochberg)**

### สิ่งที่เราอ้าง และไม่อ้าง
- ✓ *Statistically enriched associations observed in historical prescriptions*
- ✓ อาจสะท้อนรูปแบบการตั้งตำรับที่เกิดซ้ำ และควรศึกษาต่อ
- ✗ ไม่ได้พิสูจน์ว่าหมอโบราณ "รู้" กลไกใด
- ✗ ไม่ได้พิสูจน์ประสิทธิผลทางคลินิกหรือเหตุและผล
"""
)
st.caption(ui.dataset_caption())
ui.disclaimer()
