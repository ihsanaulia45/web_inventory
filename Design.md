# Design — ERP Product Operation

## 1. Arah desain

Desain mengadopsi struktur screenshot sebagai referensi: sidebar biru tua, top bar biru, area konten biru sangat muda, kartu putih dengan sudut membulat, dan tabel dengan zebra row biru muda. Identitas visual diubah untuk konteks Product Operation; bukan menyalin nama, avatar, atau data pada screenshot.

Prinsip: informasi risiko tampil lebih dahulu, filter dekat dengan data, angka tonase mudah dipindai, dan status selalu memiliki label teks selain warna.

## 2. Design tokens

| Token | Nilai | Pemakaian |
| --- | --- | --- |
| Navy | `#034E84` | Sidebar, top bar, primary action |
| Navy dark | `#023B66` | Hover/active navigation |
| Canvas | `#DCEFF4` | Latar area aplikasi |
| Surface | `#FFFFFF` | Kartu, tabel, dialog |
| Row tint | `#D8EEF4` | Zebra row dan selected row |
| Text | `#112B4A` | Teks utama |
| Muted | `#61758A` | Label bantu dan metadata |
| Border | `#C7DCE3` | Pembatas ringan |
| Safe | `#237A57` | Status SAFE |
| Warning | `#B7791F` | Status WARNING / due soon |
| Critical | `#C53030` | Status SHORTAGE / hold kritis |
| Radius card | `16px` | Kartu utama |
| Radius control | `999px` | Search dan chip filter |

Gunakan Inter atau system sans-serif. Ukuran dasar 14px, label 12px, judul halaman 24px, metrik KPI 28–32px. Ikon menggunakan satu library yang konsisten (misalnya Bootstrap Icons atau Lucide).

## 3. Shell aplikasi

### Desktop (≥ 1024px)

- Sidebar tetap, lebar 240px: logo “Product Operations”, item Dashboard, Sales Orders, Inventory Tracker, Shortage Monitor, Imports, Rules, dan Administration sesuai izin.
- Top bar tinggi 64px: breadcrumb/judul konteks di kiri, pencarian global di tengah, bell, avatar dan menu user di kanan.
- Konten memiliki padding 24px dan lebar maksimum cair; kartu tidak dipaksa melebar berlebihan pada monitor besar.
- Navigasi aktif memiliki latar navy gelap dan indikator kiri cyan muda.

### Mobile (< 1024px)

- Sidebar berubah menjadi drawer; top bar berisi menu, judul pendek, pencarian, dan profil.
- Bottom navigation memuat Dashboard, Orders, Trackers, Shortage, dan More.
- Kartu KPI menjadi 2 kolom (atau 1 kolom di layar sempit); tabel memiliki horizontal scroll dan kolom penting diprioritaskan.
- Filter menggunakan bottom sheet. Detail SO memakai tab/accordion agar konten tidak terlalu panjang.

## 4. Informasi dan navigasi

```text
Dashboard
Sales Orders
  └─ Sales Order Detail
Inventory Tracker
  ├─ A. Finish Good
  ├─ B. Not Finish
  ├─ C. In Process
  └─ D. Raw Material
Shortage Monitor
Imports & Data Quality
Rules & Categories
Administration
```

Klik `repeat_no`, order number, customer, atau coil adalah tautan kontekstual; pengguna selalu dapat kembali ke daftar sebelumnya dengan filter yang dipertahankan.

## 5. Dashboard

### Struktur desktop

```text
[Dashboard Product Operation                         Search               User]
[Due date][Customer][Purchaser][Status shortage] [Reset] [Apply filter]

[Open Order] [Shipped] [Finish Good] [Not Finish] [In Process] [Raw Material]

[ Tracker composition (donut / stacked bar) ] [ Shortage & Due Soon ]
[ by A–D, in tons                       ] [ Shortage/Warning/Safe ]

[ Priority Sales Orders — table, 2/3 width ] [ Inventory by yard — 1/3 width ]
```

- KPI menampilkan angka utama, satuan `t`, dan konteks filter aktif. Kartu shortage memakai angka jumlah SO, bukan tonase saja.
- Grafik komposisi memakai empat warna yang konsisten dengan label A–D. Tooltip memuat tonase dan persentase terhadap tracker coverage, bukan menganggap tahap-tahap tersebut seluruhnya stok siap kirim.
- Grafik shortage menggunakan label SAFE, WARNING, SHORTAGE dan angka eksplisit agar tetap terbaca tanpa warna.
- Tabel prioritas memiliki: repeat no, customer, SO, due date, open order, A, B, C, D, unallocated, status shortage, dan action “Open”.

### Interaksi

- Klik metrik A–D membuka halaman tracker dengan konteks filter saat ini.
- Klik segmen grafik membuka Sales Orders dengan filter tracker/status yang terkait.
- Klik baris prioritas membuka detail SO.
- Filter dipertahankan dalam URL query parameters agar dapat dibagikan dan diekspor.

## 6. Halaman Sales Orders

Toolbar mengikuti screenshot: search berbentuk pil, tombol Sort dan Filter, serta aksi Export di kanan. Tabel diletakkan pada surface putih dengan header ringkas dan zebra row.

| Kolom desktop | Tampilan mobile |
| --- | --- |
| Repeat no, SO, customer, purchaser | Repeat no, customer, status |
| Due date, quantity, shipped, open order | Due date, open order |
| A, B, C, D, unallocated | Ringkasan tracker dalam chip/baris kedua |
| Shortage status, actions | Status dan chevron detail |

Status menggunakan pill: `SHORTAGE` merah, `WARNING` amber, `SAFE` hijau. Hold dan reconciliation mismatch memakai ikon peringatan dengan tooltip serta teks yang tersedia untuk screen reader.

## 7. Detail Sales Order

Bagian atas memuat repeat no, order no, customer/purchaser, designation, due date, shortage status, dan tombol back/export. Di bawahnya:

1. **Order allocation**: progress/segmented bar Shipped, A–D, dan Unallocated; angka tonase serta persentasenya.
2. **Tracker cards**: empat kartu A–D yang dapat dibuka. Kartu menampilkan tonase SO, jumlah coil detail yang cocok, dan pengecualian (hold/NG/mismatch) jika ada.
3. **Risk and action**: shortage date, remaining stock, supply until, remark terbaru, dan CTA tambah remark bagi planner.
4. **Traceability**: tab `Finish Good`, `Not Finish`, `In Process`, `Raw Material`, `Forecast & Supply`, masing-masing berisi tabel data detail.

Jangan memberi label “Ready to ship” pada total A–D. Hanya Finish Good yang tidak hold dan sesuai kualitas dapat memperoleh badge “Eligible for shipment” setelah aturan bisnis ATP disepakati.

## 8. Halaman tracker dan detail coil

Masing-masing tracker memakai pola daftar yang sama: judul, total tonase, count coil, search, Sort, Filter, Export, tabel, dan pagination. Filter spesifik tampil sebagai chip di filter panel:

- Finish Good: grade, yard, finishing date, due date, category.
- Not Finish: final line, hold reason, count NG, yard, category.
- In Process: coil status, leading process, post process, shift, yard.
- Raw Material: yard, class, ship name, acceptance date, designation.

Klik coil membuka side panel pada desktop atau full-screen sheet di mobile. Panel memuat atribut coil, timeline tanggal, relasi SO, dan link ke detail SO.

## 9. Empty, loading, dan error states

- Loading: skeleton kartu/tabel, bukan spinner penuh halaman.
- Tanpa hasil: “Tidak ada Sales Order yang sesuai filter” dan tombol reset filter.
- Unmatched: tampilkan jumlah record dan link ke Data Quality; jangan hilangkan dari total source count.
- Import invalid: tampilkan status batch, jumlah gagal, alasan per baris, dan tombol unduh error file.
- Akses ditolak: halaman ringkas dengan tombol kembali; jangan menampilkan menu atau data terlindungi.

## 10. Komponen yang perlu dibuat

| Komponen | Variasi |
| --- | --- |
| AppShell | Desktop sidebar, mobile drawer/bottom nav |
| FilterBar | Search, date range, multi-select, reset/apply |
| MetricCard | Standard, warning, critical, clickable |
| StatusPill | Safe, warning, shortage, hold, unmatched |
| TrackerBadge | A/B/C/D dengan warna dan tonase |
| DataTable | Desktop/mobile, sort, pagination, empty state |
| RiskPanel | Shortage detail dan remarks |
| CoilDetailPanel | Side panel / mobile sheet |
| ImportWizard | Upload, preview, validation, result |

## 11. Django template implementation guidance

- Gunakan base template untuk `AppShell`, partial/template tags untuk FilterBar, StatusPill, TrackerBadge, dan pagination agar konsisten.
- Endpoint list membaca parameter query yang sama dengan dashboard; ekspor harus memakai filter tersebut.
- Agregasi dashboard dikerjakan di query Django/database, bukan menghitung seluruh dataset di browser.
- Gunakan progressive enhancement: form filter tetap berfungsi tanpa JavaScript; AJAX/HTMX dapat mempercepat refresh tabel dan kartu bila dipilih.
- Semua nilai uang/tonase dan tanggal diformat dari data typed; jangan mengirim HTML dari field impor.

## 12. Validasi visual sebelum implementasi selesai

- Desktop 1440px: sidebar, KPI, grafik, dan tabel tidak saling bertumpuk; konten tabel terbaca tanpa font kecil.
- Tablet 768px dan mobile 390px: navigasi berubah sesuai aturan, filter dapat digunakan, detail SO dapat ditelusuri, dan tabel tetap dapat diakses.
- Kontras teks dan status lulus; warna tidak menjadi satu-satunya pembeda kondisi.
- Kondisi SHORTAGE, WARNING, SAFE, hold, empty, and import-error diuji secara visual.
