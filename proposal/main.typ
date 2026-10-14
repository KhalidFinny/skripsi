// Proposal Skripsi , Muhammad Khalid Atthoriq
// Politeknik Negeri Malang, Program Studi Teknik Informatika
//
// Build:  typst compile main.typ proposal.pdf
//
// CATATAN: BAB I (1.1 sampai 1.5) dan BAB II (2.1 Penelitian Terdahulu dan
// 2.2 Dasar Teori) sudah lengkap. Seluruh sitasi dibatasi tahun 2017 sampai
// 2026 sesuai arahan pembimbing.
// BAB III masih kosong (placeholder).

#set document(
  title: "Pengembangan Sistem Deteksi Anxiety Menggunakan Metode Motion Estimation (POC-ABS) Secara Realtime",
  author: "Muhammad Khalid Atthoriq",
)

#set page(
  paper: "a4",
  margin: (top: 3cm, bottom: 3cm, left: 4cm, right: 3cm),
  numbering: none,
)

#set text(font: "Liberation Serif", size: 12pt, lang: "id")
#set par(justify: true, leading: 1.15em, first-line-indent: 1.27cm)

#set heading(numbering: (..nums) => {
  let n = nums.pos()
  if n.len() == 1 {
    return "BAB " + numbering("I", n.first()) + "."
  }
  numbering("1.1", ..n)
})

// Judul BAB: rata tengah, tebal, selalu mulai halaman baru.
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  align(center, text(weight: "bold", it))
}

// Subjudul: rata kiri, tebal.
#show heading.where(level: 2): it => {
  block(text(weight: "bold", it))
}

#show heading: set block(above: 1.4em, below: 0.9em)

// Penomoran gambar dan tabel
//
// Nomor mengikuti nomor BAB tempat gambar atau tabel itu berada (Gambar 2.1,
// Tabel 2.1, dan seterusnya), sehingga penomoran tetap benar ketika BAB III
// ditambahkan nanti.

#let nomor-gambar(..n) = {
  let bab = counter(heading).get().at(0)
  str(bab) + "." + str(n.pos().first())
}

#let nomor-tabel(..n) = {
  let bab = counter(heading).get().at(0)
  str(bab) + "." + str(n.pos().first())
}

#set figure(numbering: nomor-gambar)
#show figure.where(kind: table): set figure(numbering: nomor-tabel)

// Tabel panjang boleh terpotong ke halaman berikutnya (Tabel 2.1 memuat
// ringkasan lima penelitian sehingga lebih tinggi dari satu halaman).
#show figure.where(kind: table): set block(breakable: true)

// Keterangan gambar dan tabel: rata tengah, tanpa titik dua setelah nomor,
// mengikuti bentuk "Gambar 2.1 Ekspresi Wajah".
#show figure.caption: it => {
  set align(center)
  text(size: 11pt)[
    #it.supplement #it.counter.display(it.numbering) #h(0.4em) #it.body
  ]
}

// Baris "Sumber:" di bawah gambar.
#let sumber(t) = align(center, text(size: 10pt, t))

// Utilitas daftar (Daftar Isi / Daftar Gambar / Daftar Tabel)


// Nomor halaman aktual dari sebuah label.
#let pg(lbl, style: "1") = context numbering(style, counter(page).at(lbl).first())

// Satu baris daftar: judul di kiri, nomor halaman di kanan.
#let row(title, page, indent: 0pt) = grid(
  columns: (1fr, auto),
  column-gutter: 1em,
  pad(left: indent, title),
  page,
)

// Judul halaman daftar (bukan heading, agar tidak ikut penomoran BAB).
#let fm-title(t) = align(center, text(weight: "bold", size: 12pt, t))

// Daftar Gambar dan Daftar Tabel disembunyikan sementara dari proposal.
// Formatnya tetap tersimpan: ubah nilai di bawah menjadi `true` untuk
// menampilkan kembali kedua halaman tersebut beserta barisnya di Daftar Isi.
#let tampilkan-daftar-gambar-tabel = false

// HALAMAN JUDUL

#align(center)[
  #v(1.5cm)
  #text(weight: "bold", size: 14pt)[
    PENGEMBANGAN SISTEM DETEKSI ANXIETY MENGGUNAKAN METODE MOTION ESTIMATION (POC-ABS) SECARA REALTIME
  ]

  #v(2.5cm)

  #text(size: 13pt)[PROPOSAL SKRIPSI]

  #v(2.5cm)

  #text[Oleh:]
  #v(0.4cm)
  #text(weight: "bold")[MUHAMMAD KHALID ATTHORIQ]
  #linebreak()
  #text[NIM. 2341720114]

  #v(3.5cm)

  #text(weight: "bold")[
    PROGRAM STUDI TEKNIK INFORMATIKA\
    JURUSAN TEKNOLOGI INFORMASI\
    POLITEKNIK NEGERI MALANG\
    2026
  ]
]
// DAFTAR ISI, DAFTAR GAMBAR, DAFTAR TABEL

#pagebreak()
#set page(numbering: "I")
#counter(page).update(1)

#fm-title[DAFTAR ISI] <daftar-isi>
#v(0.5cm)

#row([DAFTAR ISI], pg(<daftar-isi>, style: "I"))
#if tampilkan-daftar-gambar-tabel {
  row([DAFTAR GAMBAR], pg(<daftar-gambar>, style: "I"))
  row([DAFTAR TABEL], pg(<daftar-tabel>, style: "I"))
}
#row([BAB I. PENDAHULUAN], pg(<bab1>))
#row([Latar Belakang], pg(<latar-belakang>), indent: 1.27cm)
#row([Rumusan Masalah], pg(<rumusan-masalah>), indent: 1.27cm)
#row([Batasan Masalah], pg(<batasan-masalah>), indent: 1.27cm)
#row([Tujuan], pg(<tujuan>), indent: 1.27cm)
#row([Manfaat], pg(<manfaat>), indent: 1.27cm)
#row([BAB II. LANDASAN TEORI], pg(<bab2>))
#row([Penelitian Terdahulu], pg(<penelitian-terdahulu>), indent: 1.27cm)
#row([Dasar Teori], pg(<dasar-teori>), indent: 1.27cm)
#row([Ekspresi Mikro Wajah], pg(<ekspresi-mikro>), indent: 2.54cm)
#row([Kecemasan dan Ekspresi Mikro], pg(<gangguan-kecemasan>), indent: 2.54cm)
#row([Facial Landmark dan Dlib], pg(<dlib>), indent: 2.54cm)
#row([Phase Only Correlation with All Block Search (POC-ABS)], pg(<poc-abs>), indent: 2.54cm)
#row([Data Tabular dan Tabular Retrieval Network (TabR)], pg(<tabr>), indent: 2.54cm)
#row([Metrik Evaluasi], pg(<metrik-evaluasi>), indent: 2.54cm)
#row([BAB III. METODOLOGI PENELITIAN], pg(<bab3>))

#if tampilkan-daftar-gambar-tabel [
  #pagebreak()

  #fm-title[DAFTAR GAMBAR] <daftar-gambar>
  #v(0.5cm)

  #row([Gambar 2.1 Ekspresi Wajah], [7])
  #row([Gambar 2.2 Micro-expressions], [8])
  #row([Gambar 2.3 Facial Landmark Dlib], [10])
  #row([Gambar 2.4 Contoh dua frame untuk n1 dan n2], [11])
  #row([Gambar 2.5 Proses POC deteksi pergerakan dari gambar contoh 2.4], [12])
  #row([Gambar 2.6 Arsitektur TabR], [15])
  #row([Gambar 2.7 Encoder dan Predictor], [15])
  #row([Gambar 2.8 Retrieval Module], [16])
  #row([Gambar 3.1 Alur Pengumpulan Data Primer Penelitian], [34])
  #row([Gambar 3.2 Proses pengambilan data], [38])
  #row([Gambar 3.3 contoh Dataset dalam bentuk frame], [38])
  #row([Gambar 3.4 Desain Sistem], [40])
  #row([Gambar 3.5 Deteksi 68 Facial Landmark menggunakan Dlib], [41])
  #row([Gambar 3.6 Hasil cropping area mata-alis kanan, mata-alis kiri, dan mulut], [42])
  #row([Gambar 3.7 Alur model TabR], [44])
  #row([Gambar 3.8 Proses Context Freezing], [46])
  #row([Gambar 3.9 Diagram Alur], [50])

  #pagebreak()

  #fm-title[DAFTAR TABEL] <daftar-tabel>
  #v(0.5cm)

  #row([Tabel 2.1 Penelitian terdahulu yang dijadikan rujukan], [6])
  #row([Tabel 2.2 Contoh hasil ekstraksi fitur], [13])
  #row([Tabel 3.1 Kategorisasi dan skor], [39])
  #row([Tabel 3.2 Contoh bentuk hasil data], [42])
]
// BAB I , PENDAHULUAN

#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)

= PENDAHULUAN <bab1>

== Latar Belakang <latar-belakang>

Gangguan kecemasan (_anxiety_) merupakan salah satu permasalahan kesehatan mental
yang paling umum di dunia @javaid2023epidemiology. Persoalan utamanya bukan hanya
jumlah penderitanya, tetapi keterlambatan dalam mengenalinya. Jumlah psikolog
klinis yang terbatas membuat proses skrining dan penanganan dini berpotensi
tertunda, sehingga diperlukan alat bantu yang objektif untuk memperkuat
pemeriksaan awal. Kebutuhan ini juga terlihat pada kelompok remaja Indonesia,
karena hanya sebagian kecil dari mereka yang benar-benar mengakses layanan
dukungan atau konseling @wahdi2025mental.

Wajah merupakan kanal komunikasi nonverbal yang paling informatif karena mampu
merefleksikan niat, sikap, dan kondisi psikologis seseorang. Selain ekspresi
makro yang lazim dijumpai dalam interaksi sehari-hari, emosi juga dapat
termanifestasi dalam bentuk yang jauh lebih halus, yaitu _micro-expression_.
_Micro-expression_ adalah gerakan otot wajah yang berlangsung sangat singkat,
muncul tanpa disengaja, dan sulit dikendalikan secara sadar @oh2018survey.
Karena sifatnya demikian, _micro-expression_ dianggap lebih menggambarkan
kondisi emosional yang sebenarnya dibandingkan ekspresi yang dapat disamarkan.
Namun, durasinya yang sangat pendek membuat gerakan ini sulit dikenali secara
visual, sehingga informasi penting justru terletak pada perubahan antar-_frame_
dan bukan pada satu citra tunggal @rosiani2020pocabs.

_Anxiety_ tidak termasuk dalam kelompok emosi dasar karena secara konsep berbeda
dari _fear_. _Fear_ merupakan respons terhadap ancaman yang jelas dan dapat
diprediksi, sedangkan _anxiety_ muncul ketika ancaman bersifat tidak pasti dan
berlangsung lebih lama sehingga menimbulkan kewaspadaan yang berkelanjutan
@hur2020anxiety. Individu dengan _anxiety_ juga cenderung berusaha menekan atau
menyembunyikan emosinya, sehingga sinyal visual kecemasan jarang muncul secara
terang-terangan dan lebih banyak tampil sebagai gerakan wajah yang sangat halus
@oh2018survey. Hambatan lain datang dari keterbatasan data dan anotasi. Dataset
standar seperti CASME II dibangun dengan kategori emosi dasar dan menyediakan
kelas cadangan berlabel _others_, sehingga karakteristik visual _anxiety_ tidak
terdefinisi dengan jelas @li2022mesurvey. Pengumpulan dan pelabelan data secara
mandiri menjadi langkah penting untuk memperoleh gambaran kecemasan yang lebih
terkontrol.

Sejalan dengan keterbatasan tersebut, pengembangan metode pengenalan
_micro-expression_ masih berpusat pada emosi dasar yang tersedia dalam dataset
standar. Pendekatan objektif berbasis sinyal visual sebenarnya telah menunjukkan
hasil yang menjanjikan, misalnya prediksi tingkat kecemasan dari rekaman video
@gavrilescu2019predicting, deteksi stres berbasis video @zhang2020video, dan
deteksi kecemasan dari kamera ponsel dengan akurasi mencapai 91%
@sahu2025anxietyfacetrack, tetapi semuanya masih bertumpu pada _action unit_ dan
fitur geometris. Pola serupa terlihat di Indonesia, di mana deteksi kesehatan
mental berbasis pembelajaran mesin lebih banyak menggunakan data fisiologis dan
perilaku @prakoso2026sistem @larasati2024penerapan. Dengan demikian, pengkajian
_anxiety_ melalui representasi pergerakan mikro wajah masih terbuka untuk
diteliti.

Untuk menjawab celah tersebut, penelitian ini memodelkan _anxiety_ berdasarkan
karakteristik pergerakan antar-_frame_, bukan berdasarkan kategori emosi pada
dataset standar. Metode _Phase Only Correlation with All Block Search_ (POC-ABS)
digunakan untuk mengambil pergeseran mikro antar-_frame_ dengan membandingkan
setiap blok citra pada dua _frame_, sehingga arah dan besar pergeseran halus
yang sulit terlihat secara langsung dapat terukur @rosiani2020pocabs. Hasil
ekstraksi berupa nilai numerik yang merepresentasikan arah dan besar pergerakan
mikro pada setiap area pengamatan, sehingga setiap sampel menjadi sekumpulan
fitur terstruktur atau data tabular. Representasi tersebut selanjutnya dimodelkan
menggunakan _Tabular Retrieval Network_ (TabR), yaitu jaringan _feed-forward_
yang juga mencari sampel terdekat dari data latih untuk memperkuat prediksi
@gorishniy2024tabr. Dengan pemrosesan yang relatif ringan, pendekatan ini
diarahkan pada sistem deteksi _anxiety_ yang dapat berjalan secara _realtime_.

Dengan demikian, penelitian ini diharapkan dapat mengisi celah metodologis dalam
pengkajian _micro-expression anxiety_, sekaligus menghasilkan sistem deteksi
_anxiety_ berbasis _motion estimation_ POC-ABS yang mampu membedakan kondisi
_anxiety_ dan tidak _anxiety_ secara objektif dan _realtime_.

== Rumusan Masalah <rumusan-masalah>

Berdasarkan latar belakang yang telah diuraikan, rumusan masalah penelitian ini
adalah sebagai berikut:

+ Bagaimana fitur pergerakan halus pada area wajah yang diekstraksi menggunakan
  metode POC-ABS mampu membedakan kondisi _anxiety_ dan tidak _anxiety_?
+ Bagaimana performa model TabR dalam mengklasifikasikan kondisi _anxiety_ dan
  tidak _anxiety_ berdasarkan fitur POC-ABS, ditinjau dari metrik _accuracy_,
  _precision_, _recall_, dan _F1-score_?

== Batasan Masalah <batasan-masalah>

Agar penelitian ini lebih terarah dan fokus, penulis menetapkan batasan-batasan
masalah sebagai berikut:

+ *Dataset.* Penelitian ini menggunakan dataset _micro-expression anxiety_ yang
  dikumpulkan secara mandiri melalui skema _pre--post_ situasi ujian dengan
  dukungan kuesioner. Pengelompokan label tingkat kecemasan (_anxiety_)
  dilakukan oleh pakar, yaitu Prof. Dr. Adi Atmoko, M.Pd., dosen Fakultas Ilmu
  Pendidikan yang memiliki keahlian di bidang bimbingan dan konseling.
+ *Fokus Representasi Emosi.* Penelitian ini difokuskan pada pengenalan kondisi
  _anxiety_ dan tidak _anxiety_, tanpa mengacu pada taksonomi emosi dasar
  seperti _happiness_, _anger_, _fear_, dan emosi dasar lainnya.
+ *Ekstraksi Pergerakan Mikro Wajah.* Ekstraksi pergerakan mikro wajah dibatasi
  pada penggunaan metode _Phase Only Correlation with All Block Search_
  (POC-ABS) untuk merepresentasikan pergeseran mikro antar-_frame_, tanpa
  membandingkan dengan metode ekstraksi gerakan lainnya.
+ *Area Pengamatan.* Penelitian hanya difokuskan untuk mengamati dan mengambil
  nilai pada area mata-alis kanan, mata-alis kiri, dan mulut.
+ *Model Klasifikasi.* Pemodelan dan klasifikasi data dilakukan menggunakan
  _Tabular Retrieval Network_ (TabR) berbasis data tabular, tanpa membahas atau
  membandingkan dengan model _deep learning_ lain seperti CNN atau _transformer_
  berbasis citra.
+ *Ruang Lingkup Sistem dan Evaluasi.* Penelitian ini dibatasi pada pemrosesan
  data citra wajah dan evaluasi performa model menggunakan metrik _Accuracy_,
  _Precision_, _Recall_, dan _F1-Score_.

== Tujuan <tujuan>

Berdasarkan rumusan masalah di atas, tujuan dari penelitian ini adalah:

+ Mengidentifikasi dan menganalisis kemampuan fitur pergerakan halus pada area
  wajah yang diekstraksi menggunakan metode POC-ABS dalam membedakan kondisi
  _anxiety_ dan tidak _anxiety_.
+ Mengevaluasi performa model TabR dalam mengklasifikasikan kondisi _anxiety_ dan
  tidak _anxiety_ berdasarkan fitur POC-ABS, ditinjau dari metrik _accuracy_,
  _precision_, _recall_, dan _F1-score_.

== Manfaat <manfaat>

Penelitian ini diharapkan dapat memberikan manfaat sebagai berikut:

+ *Kontribusi terhadap Analisis Anxiety Berbasis Ekspresi Wajah.* Penelitian ini
  memberikan kontribusi dalam pengembangan analisis _micro-expression anxiety_
  pada wajah yang belum banyak dikaji secara eksplisit dalam penelitian
  _micro-expression_ sebelumnya.
+ *Referensi Pengembangan Dataset Micro-Expression Anxiety.* Dataset _pre--post
  exam_ yang dikumpulkan secara mandiri melalui pengisian kuesioner dan
  perekaman ekspresi wajah dapat menjadi referensi awal bagi penelitian
  selanjutnya dalam membangun dan mengolah data _micro-expression anxiety_ yang
  bersifat natural dan kontekstual.
+ *Pendekatan Teknis untuk Deteksi Micro-Expression Anxiety.* Pendekatan teknis
  yang mengombinasikan ekstraksi pergerakan mikro wajah menggunakan _Phase Only
  Correlation with All Block Search_ (POC-ABS) dan pemodelan klasifikasi
  berbasis data tabular menggunakan _Tabular Retrieval Network_ (TabR) dapat
  menjadi acuan metodologis bagi penelitian selanjutnya dalam mendeteksi emosi
  wajah yang bersifat halus dan sulit diamati secara visual.

// ===========================================================================
// BAB II , LANDASAN TEORI
// ===========================================================================

= LANDASAN TEORI <bab2>

== Penelitian Terdahulu <penelitian-terdahulu>

Beberapa penelitian yang dijadikan rujukan dalam penelitian ini disajikan pada
Tabel 2.1.

#figure(
  table(
    columns: (1.5fr, 0.42fr, 1.06fr, 2.02fr),
    inset: 6pt,
    align: (left, center, left, left),
    stroke: 0.5pt,
    table.header(
      [*Judul Jurnal*], [*Tahun*], [*Metode*], [*Hasil Penelitian*],
    ),
    [
      A Novel Approach on Motion Estimation for Micro-Expression Recognition
      Using POC-ABS @rosiani2020pocabs
    ],
    [2020],
    [POC-ABS, SVM, KNN],
    [
      Akurasi 94,3% (SVM) dan 95,6% (KNN) pada CASME II dengan rata-rata waktu
      komputasi sekitar 0,03 detik; area alis dominan pada sejumlah ekspresi.
    ],
    [
      Pengenalan Ekspresi Mikro Wajah Berdasarkan Point Feature Tracking
      Menggunakan Fase Apex @choirina2022edukomputika
    ],
    [2022],
    [DRMF, KLT, SVM, MLP],
    [
      Akurasi 81,3% dengan waktu komputasi rata-rata 1,45 detik per video dengan
      membatasi area pengamatan pada alis dan sudut bibir.
    ],
    [
      TabR: Tabular Deep Learning Meets Nearest Neighbors @gorishniy2024tabr
    ],
    [2024],
    [TabR],
    [
      Peringkat rata-rata terbaik di antara model pembelajaran mendalam untuk
      data tabular dan pada sejumlah dataset melampaui GBDT, terutama pada data
      kecil hingga menengah.
    ],
    [
      Tabular Data Classification and Regression: XGBoost or Deep Learning with
      Retrieval-Augmented Generation @pasaribu2024tabular
    ],
    [2024],
    [XGBoost, TabNet, TabR],
    [
      TabR dengan komponen _retrieval_ unggul pada tugas klasifikasi, sedangkan
      XGBoost tetap unggul pada regresi.
    ],
    [
      Confusion Matrix @yang2024confusion
    ],
    [2024],
    [Confusion Matrix],
    [
      Kerangka tabel kontingensi untuk membaca pola kesalahan klasifikasi dan
      dasar perhitungan _accuracy_, _precision_, _recall_, serta _F1-score_.
    ],
  ),
  caption: [Penelitian terdahulu yang dijadikan rujukan],
) <tabel-2-1>

Dari penelitian tersebut, estimasi pergerakan berbasis blok (POC-ABS) terbukti
mampu merepresentasikan pergerakan mikro wajah secara cepat, dan pemodelan data
tabular berbasis _retrieval_ (TabR) terbukti unggul pada tugas klasifikasi data
berukuran kecil hingga menengah. Keduanya belum dipertemukan untuk memodelkan
kondisi _anxiety_, karena penelitian pengenalan ekspresi mikro masih berpusat
pada emosi dasar yang tersedia dalam dataset standar. Celah inilah yang menjadi
dasar penelitian ini.

== Dasar Teori <dasar-teori>

=== Ekspresi Mikro Wajah <ekspresi-mikro>

Ekspresi wajah merupakan kanal komunikasi nonverbal utama yang mengungkap
keadaan emosional seseorang, dan umumnya terbentuk tanpa disadari sebagai
reaksi atas emosi yang sedang dialami @dawel2025faking. Perubahan ekspresi
terpusat pada area seperti alis, kelopak mata, dan mulut, yang berperan penting
dalam menyampaikan informasi emosional @kim2022diagnostic.

#figure(
  image("figures/fig2-1-ekspresi-wajah.png", width: 70%),
  caption: [Ekspresi Wajah],
) <gambar-2-1>
#sumber[Sumber: data CASME II]

Berdasarkan karakteristik kemunculannya, ekspresi wajah dibedakan menjadi
ekspresi makro dan ekspresi mikro. Ekspresi makro melibatkan perubahan pada
hampir seluruh bagian wajah sehingga relatif mudah diamati, sedangkan ekspresi
mikro merupakan gerakan otot wajah yang muncul tanpa disengaja dengan durasi
sangat singkat dan intensitas gerakan yang halus, berlangsung sekitar 0,04
hingga 0,2 detik, serta hanya tampak pada sebagian kecil bagian wajah
@choirina2022edukomputika.

Ekspresi mikro (_micro-expression_) muncul ketika seseorang berupaya menutupi
atau menekan emosi yang sesungguhnya, sehingga gerakan wajah yang tampak
bersifat spontan dan sukar dikendalikan. Berbeda dari ekspresi makro yang dapat
dimanipulasi secara sadar, ekspresi mikro menyingkap emosi autentik melalui
perubahan otot wajah yang sangat halus dan berdurasi pendek @ben2021video.
Intensitas pergerakan ototnya terbukti jauh lebih kecil daripada ekspresi
makro, sehingga ekspresi yang muncul sering kali tidak membentuk pola wajah
yang utuh dan sulit dikenali secara visual @lu2022objective. Ekspresi ini lahir
dari interaksi antara sistem motorik emosional dan sistem kontrol volunter
wajah, sehingga pergerakan ototnya tidak selalu terorganisasi secara penuh
seperti pada ekspresi sadar @dong2022spontaneous. Dengan demikian, ekspresi
mikro lebih tepat dipahami sebagai indikator kebocoran emosi yang kuat, dan
sifatnya yang halus serta lokal inilah yang menjadikannya sukar dikenali secara
kasat mata.

#figure(
  image("figures/fig2-2-micro-expression.png", width: 85%),
  caption: [Micro-expressions],
) <gambar-2-2>

=== Kecemasan dan Ekspresi Mikro <gangguan-kecemasan>

Kecemasan (_anxiety_) dipahami sebagai perasaan antisipatif terhadap
kemungkinan munculnya situasi yang menakutkan, yang mendorong individu bersiap
bertindak, meskipun pada kenyataannya ancaman tersebut tidak benar-benar
terjadi dan tidak terikat pada objek atau kondisi tertentu yang perlu
dihindari. Secara psikologis, kondisi ini berbeda dari _fear_, sebab _fear_
muncul sebagai respons terhadap ancaman yang nyata dan spesifik serta memicu
reaksi cepat seperti _fight or flight_, sedangkan _anxiety_ berkaitan dengan
ancaman yang tidak terdefinisi dengan jelas dan menghasilkan kewaspadaan yang
berlangsung terus-menerus @hur2020anxiety.

Kecemasan berubah menjadi kondisi abnormal ketika intensitas dan durasinya
tidak sebanding dengan ancaman yang dihadapi atau justru muncul tanpa sebab
yang jelas, sehingga tidak lagi dapat dimaknai sebagai respons adaptif terhadap
lingkungan. Pada kondisi itu, kecemasan dapat berkembang menjadi gangguan
psikologis yang mengganggu fungsi sosial, pekerjaan, serta aktivitas sehari-hari
individu @javaid2023epidemiology. Tingginya prevalensi gangguan kecemasan di
Indonesia menunjukkan bahwa kecemasan abnormal merupakan persoalan kesehatan
mental yang serius, terutama pada kelompok remaja dan pelajar @wahdi2025mental.

Dalam interaksi sosial, kecemasan yang berlangsung terus-menerus tidak selalu
diungkapkan secara jelas melalui ekspresi wajah yang mudah dikenali. Individu
dengan _anxiety_ cenderung melakukan regulasi emosi dengan menahan ekspresi
negatif guna menjaga citra diri dan menyesuaikan diri dengan lingkungan sosial,
sehingga tanda-tanda visual kecemasan sering kali tidak tampak secara eksplisit
@lei2024camouflaging. Sebagai konsekuensinya, respons emosional yang berkaitan
dengan kecemasan lebih sering muncul dalam bentuk aktivasi otot wajah yang
tidak disengaja, berintensitas sangat rendah, dan berdurasi singkat. Pola
kemunculan tersebut sejalan dengan karakteristik _micro-expression_, yaitu
ekspresi wajah yang timbul ketika individu berupaya menyembunyikan emosi yang
sesungguhnya, namun tetap menunjukkan kebocoran emosi secara spontan
@zhao2023microexpressions. Dalam kerangka _micro-expression_, perubahan tersebut
tampak pada area berikut:

+ Area mata, khususnya perubahan halus di sekitar bagian bawah mata yang
  mencerminkan peningkatan kewaspadaan.
+ Area sudut bibir (_lip corner_), yang menunjukkan ketegangan ringan sebagai
  respons terhadap ketidaknyamanan emosional.

Perubahan pada area-area tersebut bersifat sementara dan sulit dikenali secara
kasat mata, sehingga lebih relevan dianalisis dalam kerangka _micro-expression_
dan pendekatan visual yang sensitif terhadap perubahan kecil pada fitur wajah
@sharma2024demystifying.

Kecemasan juga tidak selalu berhenti ketika situasi pemicunya berakhir. Studi
menunjukkan bahwa seseorang tetap melakukan evaluasi berulang atas pengalaman
ujian yang telah dijalani, dan _post-event processing_ teramati muncul secara
bermakna setelah situasi ujian serta berkaitan dengan tingkat kecemasan yang
dialami @mocklinghoff2024postevent. Temuan tersebut mengindikasikan bahwa
gangguan kecemasan dapat berlangsung sebelum maupun sesudah stimulus pemicunya
berakhir.

=== Facial Landmark dan Dlib <dlib>

Deteksi wajah merupakan tahap awal dalam pemrosesan citra wajah yang bertujuan
mengenali keberadaan wajah sekaligus memisahkan area wajah dari latar belakang,
sehingga analisis berikutnya hanya tertuju pada wilayah wajah yang relevan
@li2022mesurvey. Pada analisis _micro-expression_, hasil deteksi wajah menjadi
_facial region_ yang memasok tahap selanjutnya, yaitu pelokalan titik fitur dan
ekstraksi pergerakan otot wajah yang sangat halus @choirina2022edukomputika.

Dlib merupakan pustaka _open-source_ yang menyediakan fungsi deteksi wajah dan
pelokalan titik _landmark_ wajah, sehingga menopang proses pemrosesan lanjutan
dalam analisis wajah. Melalui pendekatan _facial landmark_, komponen wajah
seperti mata, alis, dan mulut dapat diidentifikasi sebagai bagian dari tahap
pra-pemrosesan @bachtiar2021jtiik. Representasi fitur berbasis _landmark_ juga
menjadi pilihan yang lazim pada data berukuran kecil, karena membuat
pengklasifikasi bekerja pada fitur terstruktur dan bukan pada citra mentah
@li2022mesurvey. Representasi _facial landmark_ yang digunakan pada penelitian
ini ditunjukkan pada gambar berikut.

#figure(
  image("figures/fig2-3-facial-landmark-dlib.png", width: 52%),
  caption: [Facial Landmark Dlib],
) <gambar-2-3>
#sumber[Sumber: data CASME II]

Gambar tersebut memperlihatkan representasi _facial landmark_ yang dipakai,
dengan setiap titik mewakili posisi geometris tertentu pada wajah. Titik-titik
_landmark_ ini dimanfaatkan untuk memetakan struktur wajah, seperti area alis,
mata, hidung, dan mulut, sehingga pergerakan atau perubahan pada bagian wajah
dapat dianalisis secara lebih terperinci.

=== Phase Only Correlation with All Block Search (POC-ABS) <poc-abs>

_Phase Only Correlation with All Block Search_ (POC-ABS) merupakan metode
estimasi pergerakan berbasis _block matching_ untuk mendeteksi pergerakan wajah
yang sangat halus dan berdurasi singkat. Metode ini membandingkan setiap blok
pada dua _frame_ berurutan untuk menentukan ada atau tidaknya pergerakan
translasi pada blok yang sama. Blok yang identik tidak menghasilkan vektor
gerak, sedangkan blok yang berbeda menghasilkan vektor gerak yang
merepresentasikan pergerakan halus pada area wajah tertentu. Vektor gerak
tersebut menjadi fitur pergerakan yang menggambarkan kebocoran ekspresi yang
muncul secara spontan dan berintensitas rendah @rosiani2020pocabs.

POC bekerja pada domain frekuensi melalui _Fast Fourier Transform_ (FFT).
Informasi fase dimanfaatkan untuk menentukan pergeseran antar blok karena fase
merepresentasikan posisi relatif objek, sedangkan amplitudo lebih dipengaruhi
oleh intensitas pencahayaan @rosiani2020pocabs. Dengan cara ini, pergeseran
antar blok dapat dihitung secara efisien tanpa terpengaruh perbedaan terang
citra.

Proses estimasi pergerakan dilakukan dengan membagi citra menjadi blok-blok
kecil yang dianalisis secara lokal. Dua _frame_ berurutan, yaitu $n_1$ dan
$n_2$, dibandingkan pada blok yang bersesuaian untuk mengamati adanya
pergeseran, sebagaimana diilustrasikan pada Gambar 2.4.

#figure(
  image("figures/fig2-4-dua-frame-n1-n2.png", width: 72%),
  caption: [Contoh dua frame untuk n1 dan n2],
) <gambar-2-4>
#sumber[Sumber: data CASME II]

Misalkan dua _frame_ berukuran $N_1 times N_2$ dinyatakan sebagai
$f(n_1, n_2)$ dan $g(n_1, n_2)$. Transformasi Fourier Diskrit dari kedua
_frame_ tersebut dinyatakan sebagai berikut.

$ F(k_1, k_2) = sum_(n_1, n_2) f(n_1, n_2) W_(N_1)^(k_1 n_1) W_(N_2)^(k_2 n_2) = A_F (k_1, k_2) e^(j theta_F (k_1, k_2)) $

$ G(k_1, k_2) = sum_(n_1, n_2) g(n_1, n_2) W_(N_1)^(k_1 n_1) W_(N_2)^(k_2 n_2) = A_G (k_1, k_2) e^(j theta_G (k_1, k_2)) $

dengan $A_F$ dan $A_G$ menyatakan amplitudo spektrum, sedangkan $theta_F$ dan
$theta_G$ menyatakan informasi fase.

_Cross spectrum_ $R(k_1, k_2)$ diperoleh dengan menormalisasi hasil perkalian
$F(k_1, k_2)$ dan konjugat kompleks $G(k_1, k_2)$. Normalisasi ini menghilangkan
pengaruh amplitudo sehingga hanya informasi fase yang dipertahankan.

$ R(k_1, k_2) = frac(F(k_1, k_2) G^* (k_1, k_2), |F(k_1, k_2)| |G(k_1, k_2)|) = e^(j (theta_F (k_1, k_2) - theta_G (k_1, k_2))) $

Fungsi _Phase Only Correlation_ $r(n_1, n_2)$ diperoleh melalui transformasi
Fourier balik dua dimensi dari $R(k_1, k_2)$.

$ r(n_1, n_2) = frac(1, N_1 N_2) sum_(k_1, k_2) R(k_1, k_2) W_(N_1)^(-k_1 n_1) W_(N_2)^(-k_2 n_2) $

Nilai maksimum $r(n_1, n_2)$ menunjukkan tingkat kemiripan fase antara kedua
_frame_, sedangkan posisi puncaknya menunjukkan estimasi pergeseran translasi.
Jika kedua blok identik, puncak korelasi bernilai satu dan tajam sempurna;
sebaliknya, nilai korelasi turun secara signifikan ketika kedua blok berbeda.

#figure(
  image("figures/fig2-5-proses-poc.png", width: 72%),
  caption: [Proses POC deteksi pergerakan dari gambar contoh 2.4],
) <gambar-2-5>
#sumber[Sumber: hasil pengolahan penulis pada data CASME II]

Hasil perbandingan pada Gambar 2.5 menghasilkan dua fitur utama, yaitu
koordinat $X$ dan $Y$, yang merepresentasikan pergeseran piksel dari titik
pusat menuju posisi baru setelah terjadinya pergeseran antar-_frame_.
Berdasarkan kedua nilai tersebut diturunkan dua fitur tambahan, yaitu sudut
pergeseran (_theta_) dan besar pergeseran (_magnitude_).

$ theta_"rad" = arctan(y/x) quad theta_"deg" = theta_"rad" dot frac(180, pi) quad theta = theta_"deg" + (360 dot (y < 0)) $

$ m = sqrt(x^2 + y^2) $

Sudut $theta$ menyatakan arah vektor pergeseran terhadap sumbu $X$, sedangkan
_magnitude_ $m$ menyatakan panjang vektor pergeseran. Nilai _magnitude_ yang
kecil merepresentasikan pergerakan mikro atau perubahan yang sangat halus.
Kombinasi fitur $X$, $Y$, $theta$, dan $m$ inilah yang disusun menjadi dataset
untuk tahap klasifikasi.

Secara ringkas, tahapan POC-ABS pada setiap pasangan blok adalah sebagai
berikut.

+ Citra dibagi menjadi blok berukuran tetap, kemudian blok yang bersesuaian
  dari _frame_ referensi dan _frame_ berikutnya dipotong untuk dibandingkan.
+ Setiap blok dikenai _window_ Hanning dua dimensi untuk mengurangi efek tepi,
  lalu ditransformasikan ke domain frekuensi menggunakan FFT2.
+ Korelasi fase dihitung dan ditransformasikan balik menjadi matriks korelasi
  spasial $r(x, y)$.
+ Titik puncak $r(x, y)$ dideteksi untuk memperoleh pergeseran blok $d_x$ dan
  $d_y$, yang selanjutnya diubah menjadi _magnitude_ dan sudut pergeseran.
+ Setiap blok menghasilkan fitur berupa posisi dan vektor gerak, seperti contoh
  pada Tabel 2.2.

#figure(
  table(
    columns: (1fr, 1fr, 1fr, 1.2fr, 1.4fr),
    inset: 6pt,
    align: center,
    stroke: 0.5pt,
    table.header(
      [*Blok*], [*X*], [*Y*], [*Magnitude*], [*Theta*],
    ),
    [10], [10], [10], [2.00], [0° (kanan)],
    [22], [17], [17], [2.24], [-63° (kanan bawah)],
    [41], [10], [31], [2.00], [90° (bawah)],
    [46], [45], [31], [1.41], [-45° (kanan bawah)],
    [50], [63], [31], [2.00], [180° (kiri)],
  ),
  caption: [Contoh hasil ekstraksi fitur],
) <tabel-2-2>

Blok dengan vektor panjang dan arah yang jelas menunjukkan adanya pergerakan
nyata, sedangkan blok dengan $d_x = d_y = 0$ menandakan tidak adanya pergerakan.
Visualisasi vektor gerak dilakukan menggunakan panah (_quiver_), dengan $X$ dan
$Y$ sebagai posisi tengah blok serta $d_x$ dan $d_y$ sebagai komponen arah
vektornya, dan panah hanya ditampilkan pada blok yang memiliki pergerakan.


=== Data Tabular dan Tabular Retrieval Network (TabR) <tabr>

Data tabular merupakan representasi data dalam struktur baris dan kolom, dengan
setiap baris merepresentasikan satu objek pengamatan dan setiap kolom
merepresentasikan fitur yang menggambarkan karakteristik objek tersebut
@arik2021tabnet. Representasi ini merupakan tipe data yang paling umum dijumpai
dalam aplikasi pembelajaran mesin di dunia nyata @gorishniy2024tabr. Pada
penelitian ini, hasil ekstraksi POC-ABS disusun sebagai data tabular, yaitu
setiap sampel ekspresi menjadi satu baris dan setiap fitur pergerakan pada tiap
area pengamatan menjadi kolom. Dengan demikian, informasi pergerakan mikro yang
halus dapat dimodelkan secara eksplisit tanpa bergantung pada struktur spasial
citra maupun urutan temporal video.


_Tabular Retrieval Network_ (TabR) merupakan model _deep learning_ yang
dirancang khusus untuk permasalahan klasifikasi dan regresi pada data tabular
dengan mengintegrasikan mekanisme _retrieval_ ke dalam jaringan _feed-forward_.
TabR dikembangkan untuk mengatasi keterbatasan model _deep learning_ tabular
konvensional yang sering kali masih tertinggal performanya dibandingkan metode
_gradient-boosted decision trees_ (GBDT). Dengan memanfaatkan prinsip
_retrieval-augmented learning_, TabR memperkaya representasi suatu sampel
dengan informasi dari sampel lain yang paling relevan dalam data latih,
sehingga prediksi tidak hanya bergantung pada bobot model, tetapi juga pada
konteks lokal antar sampel @gorishniy2024tabr.

Mekanisme _retrieval_ pada TabR dijalankan menggunakan _Facebook AI Similarity
Search_ (FAISS), yaitu pustaka _open-source_ untuk mencari vektor yang paling
mirip terhadap suatu _query_ pada ruang berdimensi tinggi secara efisien
@johnson2021faiss. FAISS membangun indeks berbasis _Approximate Nearest
Neighbor_ (ANN) sehingga pencarian tetangga terdekat tidak perlu menghitung
jarak terhadap seluruh vektor. Pada penelitian ini, FAISS berperan sebagai
infrastruktur pencarian kandidat terdekat di dalam modul _retrieval_ TabR,
bukan sebagai model pembelajaran tersendiri.

Pendekatan _retrieval_ pada TabR memungkinkan model menangkap hubungan lokal
yang sulit direpresentasikan melalui transformasi global, terutama pada data
tabular berukuran kecil hingga menengah. Studi empiris menunjukkan bahwa TabR
mencapai performa rata-rata terbaik di antara model _deep learning_ tabular dan
pada sejumlah dataset mampu melampaui GBDT, khususnya pada tugas klasifikasi
@gorishniy2024tabr @pasaribu2024tabular.

#figure(
  image("figures/fig2-6-arsitektur-tabr.png", width: 85%),
  caption: [Arsitektur TabR],
) <gambar-2-6>
#sumber[Sumber: diadaptasi dari @gorishniy2024tabr]

Berdasarkan Gambar 2.6, TabR dikembangkan dari jaringan _feed-forward_
$f(x) = P(E(x))$ dengan menambahkan modul _retrieval_ $R$ setelah _encoder_
dalam bentuk cabang residual. _Encoder_ memetakan sampel target $x$ dan sampel
kandidat ${x_i}$ ke ruang representasi laten yang sama, sehingga diperoleh
$tilde(x) = E(x)$ dan $tilde(x)_i = E(x_i)$. Modul _retrieval_ kemudian
mengambil informasi dari sampel kandidat yang paling mirip dan menggabungkannya
dengan representasi sampel target.

$ z = tilde(x) + R(tilde(x), {tilde(x)_i, y_i}) quad hat(y) = P(z) $

Dengan mekanisme ini, keputusan model tidak hanya bergantung pada bobot
jaringan, tetapi juga pada konteks lokal antar sampel.

#figure(
  image("figures/fig2-7-encoder-decoder.png", width: 85%),
  caption: [Encoder dan Predictor],
) <gambar-2-7>
#sumber[Sumber: diadaptasi dari @gorishniy2024tabr]

Berdasarkan Gambar 2.7, _encoder_ $E$ dan _predictor_ $P$ pada TabR dirancang
sebagai jaringan _feed-forward_ sederhana. _Encoder_ memproses data tabular
melalui _Input Module_, lalu dilanjutkan beberapa _block_ pemrosesan untuk
menghasilkan representasi laten $tilde(x)$. _Predictor_ $P$ memetakan
representasi tersebut ke ruang keluaran melalui rangkaian _block_ dan lapisan
linear untuk menghasilkan prediksi akhir.

#figure(
  image("figures/fig2-8-retrieval-module.png", width: 78%),
  caption: [Retrieval Module],
) <gambar-2-8>
#sumber[Sumber: diadaptasi dari @gorishniy2024tabr]

Berdasarkan Gambar 2.8, modul _retrieval_ $R$ memilih sejumlah $m$ sampel
kandidat yang paling mirip dengan sampel target pada ruang laten. Nilai
kemiripan $s_i = S(tilde(x), tilde(x)_i)$ dinormalisasi dengan _softmax_ untuk
memperoleh bobot kontribusi

$ w_i = frac(exp(s_i), sum_(j in I_"cand") exp(s_j)) $

Informasi dari sampel kandidat kemudian diagregasi menggunakan bobot tersebut,

$ R = sum_(i=1)^m w_i dot V(tilde(x), tilde(x)_i, y_i) $

untuk memperkaya representasi laten sampel target sebelum dilakukan prediksi
akhir.

=== Metrik Evaluasi <metrik-evaluasi>

Kelas _anxiety_ tinggi ditetapkan sebagai kelas positif dan _anxiety_ rendah
sebagai kelas negatif. Performa model diukur menggunakan _accuracy_, _precision_,
_recall_, dan _F1-score_ @chicco2023mcc, yang dihitung menggunakan persamaan
berikut.

+ _Accuracy_

  $ "accuracy" = frac("TP" + "TN", "TP" + "TN" + "FP" + "FN") $

+ _Precision_

  $ "precision" = frac("TP", "TP" + "FP") $

+ _Recall_

  $ "recall" = frac("TP", "TP" + "FN") $

+ _F1-Score_

  $ F_1 = frac(2 dot "precision" dot "recall", "precision" + "recall") $

// ===========================================================================
// BAB III , METODOLOGI PENELITIAN (belum ditulis)
// ===========================================================================

= METODOLOGI PENELITIAN <bab3>

#text(style: "italic")[Bagian ini belum ditulis.]


// ===========================================================================
// DAFTAR PUSTAKA
// ===========================================================================

#pagebreak()
#bibliography("refs.bib", style: "apa", title: [DAFTAR PUSTAKA])
