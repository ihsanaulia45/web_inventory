# PRD — ERP Product Operation

## 1. Ringkasan

ERP Product Operation adalah aplikasi Django untuk memantau pemenuhan Sales Order (SO) dari posisi persediaan dan progres produksi. Sistem menjawab dua pertanyaan operasional: berapa kapasitas pemenuhan tiap SO, dan persediaannya sedang berada pada tracker mana.

Versi awal menggunakan data pada `Data/Training Web.xlsx`. Dataset bersifat dummy, dengan periode simulasi Oktober 2026–Februari 2027.

## 2. Tujuan dan hasil yang diharapkan

- Memberikan dashboard ringkas untuk Sales, Production Planning, Warehouse, dan manajer operasi.
- Menjadikan setiap SO dapat ditelusuri ke empat tracker inventory: Finish Good, Not Finish, In Process, dan Raw Material.
- Menampilkan risiko shortage serta prioritas tindakan berdasarkan due date, kondisi hold, dan status supply.
- Menyediakan daftar operasional yang dapat difilter, dicari, diurutkan, dan dibuka sampai detail coil/material.

## 3. Pengguna dan hak akses

| Peran | Kebutuhan utama | Hak akses awal |
| --- | --- | --- |
| Administrator | Kelola pengguna, master, impor data, dan aturan kategori | Penuh |
| Sales / Customer Service | Lihat status SO dan risiko delivery | Baca dashboard, SO, dan detail terkait |
| Production Planner | Prioritaskan proses dan shortage | Baca/tulis tracker, remark, dan aturan kategori |
| Warehouse | Pantau lokasi, material, dan penerimaan | Baca/tulis tracker Raw Material dan Finish Good |
| Manajer Operasi | Pantau KPI dan pengecualian | Baca seluruh laporan |

Autentikasi memakai akun Django. Semua perubahan data dan impor menyimpan pengguna, waktu, serta nilai sebelum/sesudah bila data operasional diedit.

## 4. Lingkup MVP

1. Dashboard analisis product operation.
2. Daftar dan detail Sales Order.
3. Inventory tracker A–D yang diturunkan dari SO.
4. Detail masing-masing tracker dan drill-down ke coil/material.
5. Pencarian, filter, sort, pagination, ekspor CSV/XLSX, dan impor XLSX tervalidasi.
6. Shortage monitor dan remark tindak lanjut.
7. Pengelolaan aturan kategori Finish Good dan Not Finish.

Di luar MVP: purchasing workflow/approval, MRP otomatis, integrasi ERP eksternal, penjadwalan produksi rinci, dan notifikasi real-time lintas sistem.

## 5. Sumber data dan model domain

### 5.1 Entitas sumber utama

| Entitas | Volume contoh | Kunci dan kegunaan |
| --- | ---: | --- |
| Sales_Order | 30 | `repeat_no` menjadi order anchor; berisi quantity, shipped, dan alokasi per tracker |
| Finish_Good | 14 | Produk selesai, coil, grade, due/delivery date, yard |
| Not_Finish | 10 | Produk belum selesai, line, hold reason, NG, yard |
| In_Process | 6 | Coil dalam proses, leading/post process, status, yard |
| Raw_Material | 18 | Material awal, berat, yard, kapal dan tanggal penerimaan |
| Shortage_Date | 30 | Status SAFE/WARNING/SHORTAGE serta projected shortage date |
| Shortage_Remark | 30 | Catatan tindak lanjut per `repeat_no` |

Dataset juga menyediakan Forecast, PRM, Packing Weight, Holiday, riwayat tracker, dan konfigurasi kategori. Entitas tersebut disiapkan sebagai modul pendukung dan sumber analisis lanjutan.

### 5.2 Kunci relasi

- Kunci bisnis utama: `repeat_no`.
- Sales Order juga dapat dicocokkan melalui `order_no`/`order_no1` sebagai validasi sekunder.
- Coil harus dipertahankan dengan `jsg_coil_no`; item produk dengan `jsg_product_no`.
- Relasi yang tidak menemukan `repeat_no` tidak boleh disembunyikan. Sistem menandainya sebagai **Unmatched** pada halaman kualitas data.

### 5.3 Pemetaan tracker A–D

| Tracker | Nama | Nilai ringkasan SO | Sumber detail | Kondisi operasional |
| --- | --- | --- | --- | --- |
| A | Finish Good | `finishing_products` | `Finish_Good` | Siap dialokasikan/dikirim, kecuali hold atau kualitas tidak layak |
| B | Not Finish | `waiting_finish` | `Not_Finish` | Menunggu penyelesaian; pantau hold dan `count_ng` |
| C | In Process | `in_process` | `In_Process` | Sedang/waiting dalam alur proses; tampilkan leading dan post process |
| D | Raw Material | `raw_material_jsg` | `Raw_Material` | Bahan telah diterima/tersedia; tampilkan yard dan penerimaan |

`not_allotment` bukan tracker A–D. Nilai tersebut ditampilkan terpisah sebagai **Belum Dialokasikan**, karena menjadi gap pemenuhan yang memerlukan tindakan planner.

Untuk ringkasan per SO, kolom kuantitas pada Sales Order menjadi sumber otoritatif. Rekor coil pada empat tabel tracker adalah bukti detail/drill-down. Jika total berat detail tidak sama dengan nilai SO, sistem menampilkan indikator rekonsiliasi, bukan mengganti nilai SO secara diam-diam.

## 6. Kebutuhan fungsional

### FR-01 Dashboard analisis

Dashboard menampilkan filter global (periode due date, customer, purchaser, designation, delivery place, status shortage) dan metrik berikut:

- Total open order (quantity dikurangi shipped), total quantity, dan total shipped.
- Total tonase pada tracker A–D serta tonase belum dialokasikan.
- Jumlah SO SHORTAGE, WARNING, SAFE, dan SO yang due dalam 7 hari.
- Donut/stacked bar komposisi tracker A–D terhadap open order.
- Tren due date atau forecast bulanan.
- Daftar prioritas: SHORTAGE dahulu, lalu WARNING/due date terdekat, hold, dan nilai belum dialokasikan terbesar.
- Ringkasan per customer/purchaser dan per yard.

Kartu dan grafik dapat diklik untuk membuka daftar SO dengan filter yang sesuai.

### FR-02 Sales Order tracker

Halaman Sales Order memperlihatkan satu baris per `repeat_no`: order number, customer, purchaser, designation/ukuran, due date, quantity, shipped, open order, A–D, belum dialokasikan, status shortage, dan kategori prioritas.

Pengguna dapat:

- mencari repeat no, SO, customer, purchaser, coil, atau designation;
- menyaring date range, tracker, shortage status, customer, purchaser, yard, dan hold;
- mengurutkan due date, open order, shortage date, atau nilai tracker;
- membuka detail SO dari baris tabel.

### FR-03 Detail Sales Order

Detail menampilkan identitas order, progress bar komposisi supply, kartu tracker A–D, status shortage, remark terbaru, forecast terkait, serta daftar coil/material pada setiap tracker.

Urutan alokasi yang terlihat pada UI: Shipped → Finish Good → Not Finish → In Process → Raw Material → Belum Dialokasikan. Sistem tidak mengasumsikan bahwa masing-masing tahap dapat langsung dikirim; status hold/NG harus tetap tampak.

### FR-04 Halaman tracker

Setiap tracker memiliki halaman khusus, tabel responsif, filter, dan detail:

- **Finish Good:** grade, finishing date, due date, required delivery date, yard, dan kategori.
- **Not Finish:** final line, result code, ship/finish hold reason, count NG, yard, dan kategori.
- **In Process:** coil status, leading process, next/post process, shift date, due date, dan yard.
- **Raw Material:** kelas, vessel/truck, maker shipped date, acceptance dates, designation/size, dan yard.

### FR-05 Shortage dan tindakan

Halaman shortage menampilkan SO Shortage/Warning, shortage date, remaining stock, supply until, proyeksi supply, remark terbaru, dan pemilik tindakan. Planner dapat membuat atau memperbarui remark tanpa mengubah data impor sumber.

### FR-06 Impor dan kualitas data

- Administrator mengunggah XLSX dalam format yang ditetapkan per entitas.
- Sistem melakukan preview, validasi header/tipe/kunci, dan menolak baris invalid dengan file error yang dapat diunduh.
- Impor berjalan atomik per batch atau jelas menyatakan partial success per baris.
- Sistem merekam file, jumlah baris, pengunggah, waktu, dan hasil impor.
- Riwayat tracker digunakan sebagai append-only snapshot; data aktif tidak boleh terhapus saat impor.

### FR-07 Kategori dan prioritas

Aturan Finish Good dan Not Finish dibaca dari konfigurasi kategori dan kondisi yang tersedia. Engine evaluasi menjalankan aturan berdasarkan `priority`; aturan aktif pertama yang seluruh kondisinya terpenuhi memberikan kategori dan probability. Administrator dapat mengelola aturan dengan validasi kolom, operator, urutan, dan status aktif.

## 7. Perhitungan dan aturan bisnis

Seluruh berat/quantity ditampilkan dalam satuan ton, tiga desimal pada tabel detail dan satu/tiga desimal sesuai konteks pada dashboard. Satuan tidak boleh dicampur dengan jumlah coil.

| Metrik | Rumus |
| --- | --- |
| Open order | `max(quantity - shipped, 0)` |
| Tracker coverage | `A + B + C + D` dari kolom Sales Order |
| Unallocated | nilai `not_allotment` dari Sales Order; tidak dihitung sebagai inventory tracker |
| Due soon | `due_date` berada dalam 7 hari kalender dari business date yang dipilih |
| Shortage priority | `SHORTAGE` > `WARNING` > `SAFE`, lalu due date naik, kemudian unallocated turun |
| Detail reconciliation | total `weight` detail per `repeat_no` dibandingkan terhadap nilai tracker SO; perbedaan melewati toleransi ditandai |

Business date adalah tanggal aplikasi yang dapat dikonfigurasi administrator. Aturan due soon dan kategori tidak boleh memakai tanggal server yang tersembunyi agar hasil laporan dapat direproduksi.

## 8. Kebutuhan nonfungsional

- Framework utama: Django dengan database PostgreSQL untuk produksi.
- Django Admin digunakan untuk operasi master dan troubleshooting, bukan pengganti dashboard pengguna.
- Halaman daftar memakai pagination server-side; indeks minimum pada `repeat_no`, order number, due date, customer, purchaser, tracker/status, dan coil number.
- Otorisasi berbasis grup Django, CSRF, audit log, validasi upload, dan pembatasan tipe/ukuran berkas.
- Target performa awal: halaman dashboard dan daftar terfilter selesai dalam <3 detik pada 10.000 SO, tanpa menghitung waktu download ekspor.
- Antarmuka desktop-first namun lengkap di mobile. Bahasa UI Indonesia dengan istilah data yang dipertahankan bila merupakan field bisnis.
- Aksesibilitas: kontras memadai, status tidak hanya dibedakan warna, fokus keyboard, dan tabel dapat di-scroll horizontal di mobile.

## 9. Kriteria penerimaan MVP

1. Pengguna dapat menemukan SO melalui `repeat_no`, nomor SO, atau customer dan melihat empat tracker A–D pada satu layar.
2. Total tracker pada dashboard dan hasil filter konsisten dengan nilai Sales Order yang sedang difilter.
3. Klik kartu/grafik menghasilkan daftar yang telah difilter dengan benar.
4. Setiap record tracker yang memiliki `repeat_no` dapat kembali ke halaman SO terkait.
5. SO berstatus SHORTAGE/WARNING tampil sebelum SAFE dalam daftar prioritas dan shortage date ditampilkan bila ada.
6. Hold, NG, dan unmatched/reconciliation mismatch terlihat sebagai pengecualian, bukan disamarkan sebagai stok siap kirim.
7. Pengunggahan XLSX invalid tidak mengubah data aktif dan memberikan alasan error yang dapat ditindaklanjuti.
8. Tampilan memenuhi desktop dan mobile sesuai Design.md.

## 10. Asumsi dan keputusan terbuka

- MVP memperlakukan field alokasi Sales Order sebagai snapshot bisnis, bukan kalkulasi ulang dari berat coil detail.
- Definisi operasional “available to promise”/ATP dan toleransi rekonsiliasi perlu disetujui sebelum otomatisasi keputusan delivery.
- Sumber `Shortage_Date` dipakai untuk status shortage pada MVP. Formula untuk merekalkulasi shortage dari forecast/PRM menjadi fase berikutnya.
- Customer, purchaser, dan designation belum memiliki tabel master eksplisit pada workbook; fase implementasi perlu menetapkan master atau mengambil nilai unik dari data impor.
