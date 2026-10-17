# ทดสอบ API ร้านก๋วยเตี๋ยวป้าส้มด้วย Bruno

Repository นี้ใช้ฝึกทดสอบ API ของระบบสั่งอาหาร โดยใช้ Flask เป็น API และ Bruno เป็นเครื่องมือส่งคำขอพร้อมตรวจสอบผลอัตโนมัติ ครอบคลุมการเข้าสู่ระบบ การดูเมนู การสั่งอาหาร การคำนวณราคา และการเปลี่ยนแปลงสต็อก

## สิ่งที่ทำใน repository นี้

- เพิ่ม Bruno Collection ชื่อ **Auntie Som Lab** จำนวน **45 คำขอ แบ่งเป็น 9 กลุ่มทดสอบ**
- เขียนสคริปต์ตรวจสอบ HTTP status รูปแบบข้อมูล ราคา และสต็อก พร้อมเก็บ token และรหัสคำสั่งซื้อไปใช้ในคำขอถัดไป
- เพิ่มสคริปต์เปิด API ใหม่ก่อนทดสอบแต่ละกลุ่ม เพื่อให้สต็อกและข้อมูลเริ่มต้นเหมือนกันทุกครั้ง
- สร้างไฟล์ Collection แบบ JSON และตรวจสอบการนำกลับเข้าใช้งานด้วย parser และ importer ของ Bruno
- รันทดสอบทั้ง Collection ต้นฉบับและ Collection ที่นำกลับเข้าจาก JSON แล้วได้ผลตรงกันทุกคำขอและทุกเงื่อนไขตรวจสอบ
- เก็บรายงานผลที่ลบ token ออกแล้ว โดยใช้โค้ด API เดิมใน `auntie-som-noodle-api/app.py`

| ไฟล์หรือโฟลเดอร์ | ใช้สำหรับ |
| --- | --- |
| [`auntie-som-noodle-api/`](auntie-som-noodle-api/) | API ที่ใช้ทดสอบ |
| [`bruno/`](bruno/) | Collection และคำขอทดสอบแบบ `.bru` |
| [`exports/Auntie-Som-Lab.json`](exports/Auntie-Som-Lab.json) | Collection แบบ JSON สำหรับนำเข้า Bruno |
| [`scripts/run_lab.py`](scripts/run_lab.py) | เปิด API และรันทดสอบแยกทีละกลุ่ม |
| [`scripts/verify-export.cjs`](scripts/verify-export.cjs) | ตรวจสอบว่า JSON และ Collection ที่นำกลับเข้ามามีข้อมูลตรงกับต้นฉบับ |
| [`reports/audit-results.md`](reports/audit-results.md) | สรุปเงื่อนไขที่ทดสอบไม่ผ่าน |
| [`reports/audit-results.json`](reports/audit-results.json) | ผลตอบกลับและผลตรวจสอบของ Collection ต้นฉบับ |
| [`reports/reimport-results.json`](reports/reimport-results.json) | ผลทดสอบของ Collection ที่นำกลับเข้าจาก JSON |
| [`reports/export-verification.json`](reports/export-verification.json) | ผลตรวจสอบไฟล์ส่งออกและการเปรียบเทียบผลทดสอบ |

## ผลทดสอบและปัญหาที่พบ

รันทดสอบครบ **45 คำขอ รวม 149 เงื่อนไขตรวจสอบ ผ่าน 128 และไม่ผ่าน 21 เงื่อนไข** ผลที่ไม่ผ่านแสดงปัญหาของ API ซึ่งยังคงตรวจสอบตามพฤติกรรมที่คาดหวังไว้ในชุดทดสอบ

### ปัญหาหลัก 3 ข้อ

| ปัญหา | วิธีทดสอบ | ผลที่คาดหวัง | ผลที่พบจริง |
| --- | --- | --- | --- |
| คำนวณราคาต่ำกว่าที่ควรเป็น 5 | กลุ่ม `02-valid-order-and-price` สั่งเมนูรหัส 1 จำนวน 1 แล้วเรียกดูคำสั่งซื้อ | ราคาเมนู 50 × จำนวน 1 ได้ยอดรวม 50 | ทั้งตอนสร้างและเรียกดูคำสั่งซื้อได้ยอดรวม 45 เพราะ API หัก 5 ออกจากยอดรวม |
| สั่งเกินสต็อกได้ | กลุ่ม `04-overstock` สั่งเมนูรหัส 1 จำนวน 3 ขณะที่มีสต็อก 2 | HTTP 400 และสต็อกยังเป็น 2 | HTTP 200 สร้างคำสั่งซื้อสำเร็จ และสต็อกกลายเป็น -1 |
| ค้นหาคำสั่งซื้อที่ไม่มีอยู่แล้วได้สถานะสำเร็จ | กลุ่ม `01-contract-and-auth` เรียก `GET /orders/ORD-does-not-exist` | HTTP 404 พร้อมข้อความผิดพลาด | HTTP 200 แม้ในข้อมูลตอบกลับมี `Order not found` |

การตรวจสอบราคาคำนวณจากราคาในเมนูคูณจำนวนที่สั่ง โดยถือว่าไม่มีส่วนลด เพราะไม่มีเงื่อนไขส่วนลดระบุไว้

### ปัญหาเพิ่มเติมเกี่ยวกับจำนวนที่สั่ง

ผลต่อไปนี้ทดสอบโดยเริ่ม API ใหม่ทุกกรณี ใช้เมนูรหัส 1 ราคา 50 และสต็อกเริ่มต้น 2

| ค่าที่ส่ง | ผลที่พบจริง |
| --- | --- |
| `quantity: 0` | สร้างคำสั่งซื้อได้ ยอดรวม -5 และสต็อกยังเป็น 2 |
| `quantity: -1` | สร้างคำสั่งซื้อได้ ยอดรวม -55 และสต็อกเพิ่มเป็น 3 |
| ไม่ส่ง `quantity` | HTTP 500 และตอบกลับเป็น HTML |
| `quantity: 1.5` | สร้างคำสั่งซื้อได้ ยอดรวม 70 และสต็อกเหลือ 0.5 |
| `quantity: "one"` | HTTP 500 และตอบกลับเป็น HTML |

ชุดทดสอบคาดหวังให้จำนวนที่ไม่ถูกต้องได้รับ HTTP 400 หรือ 422 พร้อมข้อความผิดพลาดแบบ JSON และสต็อกต้องไม่เปลี่ยนแปลง

## วิธีติดตั้งและรันทดสอบอัตโนมัติ

ต้องมี Python 3.10 ขึ้นไป, Node.js 22 ขึ้นไป, npm และ Git คำสั่งด้านล่างใช้กับ PowerShell บน Windows โดยเครื่องที่ใช้ทดสอบจริงเป็น Python 3.14.7, Node.js 22.14.0, Flask 3.1.3 และ Bruno CLI 4.2.1

```powershell
git clone https://github.com/chayathorn-nk/api-testing-course.git
cd api-testing-course
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
npm.cmd test
```

ก่อนรัน ให้หยุด API ที่เปิดค้างอยู่บนพอร์ต `5000` สคริปต์จะเปิด API ที่ `http://localhost:5000` เอง รอจนพร้อมใช้งาน รันทดสอบหนึ่งกลุ่ม แล้วปิด API ก่อนเริ่มกลุ่มถัดไป เมื่อเสร็จแต่ละกลุ่มจะล้าง token ใน environment

เมื่อใช้ API ปัจจุบัน คำสั่งทดสอบจะจบด้วย **exit code 1** เพราะตรวจพบข้อผิดพลาดข้างต้น ส่วน **exit code 2** หมายถึงปัญหาการตั้งค่าหรือการรันทดสอบ อ่านผลสรุปได้ที่ [`reports/audit-results.md`](reports/audit-results.md)

หากต้องการรันเฉพาะกลุ่ม เช่น การสั่งเกินสต็อก ให้ใช้:

```powershell
python scripts/run_lab.py --scenario 04-overstock
```

การรันเฉพาะกลุ่มจะเขียนทับรายงานสรุปเดิม หากต้องการรายงานครบทุกกลุ่ม ให้รัน `npm.cmd test` อีกครั้ง

## วิธีใช้ผ่าน Bruno Desktop

1. ติดตั้ง Bruno Desktop แล้วเปิดโฟลเดอร์ `bruno` เป็น Collection
2. สร้าง environment สำหรับใช้งานจากไฟล์ตัวอย่าง:

   ```powershell
   Copy-Item bruno/environments/local.example.bru bruno/environments/local.bru
   ```

3. เลือก environment ชื่อ `local` ซึ่งกำหนด `baseUrl` เป็น `http://localhost:5000` และใช้บัญชีทดสอบ `student` / `hungry` โดยเว้น `accessToken` ว่างไว้
4. เปิด API จากโฟลเดอร์หลักของ repository:

   ```powershell
   .\.venv\Scripts\python.exe -m flask --app auntie-som-noodle-api/app.py run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
   ```

5. รันทีละโฟลเดอร์ตามตารางด้านล่าง แต่ละกลุ่มมีคำขอ Login เพื่อเก็บ token อัตโนมัติ หลังจบแต่ละกลุ่มให้หยุด API ด้วย `Ctrl+C` แล้วเปิดใหม่ด้วยคำสั่งเดิมก่อนรันกลุ่มถัดไป

| กลุ่มทดสอบ | สิ่งที่ตรวจสอบ |
| --- | --- |
| `01-contract-and-auth` | เมนู การเข้าสู่ระบบ token ที่ขาดหายหรือไม่ถูกต้อง เมนูและคำสั่งซื้อที่ไม่มีอยู่ |
| `02-valid-order-and-price` | สร้างและเรียกดูคำสั่งซื้อ คำนวณราคา และลดสต็อก |
| `03-exhausted-stock` | สั่งสินค้าชิ้นสุดท้าย แล้วตรวจสอบการปฏิเสธเมื่อสต็อกหมด |
| `04-overstock` | สั่งจำนวนมากกว่าสต็อกที่มี |
| `05-zero-quantity` | จำนวนที่สั่งเป็นศูนย์ |
| `06-negative-quantity` | จำนวนที่สั่งติดลบ |
| `07-missing-quantity` | ไม่ส่งจำนวนที่สั่ง |
| `08-fractional-quantity` | จำนวนที่สั่งเป็นทศนิยม |
| `09-string-quantity` | จำนวนที่สั่งเป็นข้อความ |

เมื่อใช้งานเสร็จ ให้คัดลอกไฟล์ environment ตัวอย่างทับ `local.bru` อีกครั้งเพื่อล้าง token ไฟล์ `local.bru` และรายงานดิบใน `reports/raw/` ถูกกำหนดให้อยู่ใน `.gitignore`

## วิธีตรวจสอบ Collection แบบ JSON

ไฟล์ [`exports/Auntie-Som-Lab.json`](exports/Auntie-Som-Lab.json) มีคำขอ สคริปต์ เงื่อนไขตรวจสอบ และ environment ที่เว้น token ว่างไว้ สามารถนำเข้าผ่านเมนู **Import Collection → Bruno Collection**

ในงานนี้สร้าง JSON และตรวจสอบการนำกลับเข้าด้วยเครื่องมือของ Bruno ผ่านสคริปต์ เนื่องจาก Bruno Desktop ที่ดาวน์โหลดมาไม่สามารถเปิดหน้าต่างใช้งานได้บนเครื่องที่ทดสอบ

ตรวจสอบไฟล์ JSON ที่มีอยู่ด้วย:

```powershell
npm.cmd run verify:export
```

หากแก้ไข Collection ใน `bruno/` แล้วต้องการสร้าง JSON ใหม่ ให้ใช้:

```powershell
node scripts/verify-export.cjs --write
```

สคริปต์จะเปรียบเทียบคำขอ สคริปต์ เงื่อนไขตรวจสอบ และตัวแปรก่อนและหลังนำกลับเข้า พร้อมเปรียบเทียบรายงานผลทดสอบที่เก็บไว้ หากเพิ่งรันเฉพาะกลุ่ม ให้รัน `npm.cmd test` ให้ครบทุกกลุ่มก่อนใช้คำสั่งตรวจสอบ JSON
