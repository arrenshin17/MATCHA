# IMPORT LIBRARY YANG DIPERLUKAN
# Flask: Framework web untuk membuat aplikasi web
# render_template: Untuk menampilkan file HTML
# request: Untuk mengambil data dari form
# redirect & url_for: Untuk mengarahkan ke halaman lain
# session: Untuk menyimpan data login user
# flash: Untuk menampilkan pesan notifikasi
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL  # Library untuk koneksi ke database MySQL
import math  # Library untuk fungsi matematika (ceil untuk pagination)

# INISIALISASI APLIKASI FLASK
app = Flask(__name__)

# Secret key diperlukan untuk mengenkripsi session (data login user)
app.secret_key = "matcha_secret_key_pro" 

# KONFIGURASI DATABASE

# Pengaturan untuk terhubung ke database MySQL
app.config['MYSQL_HOST'] = 'localhost'      # Server database (localhost = komputer lokal)
app.config['MYSQL_USER'] = 'root'           # Username MySQL
app.config['MYSQL_PASSWORD'] = ''           # Password MySQL (kosong untuk default XAMPP)
app.config['MYSQL_DB'] = 'matcha_db'        # Nama database yang akan digunakan

# Membuat koneksi ke database MySQL
mysql = MySQL(app)


# FUNGSI HELPER (FUNGSI PEMBANTU)
def is_logged_in():
    """
    Fungsi untuk mengecek apakah user sudah login atau belum.
    
    Returns:
        bool: True jika user sudah login, False jika belum
    """
    return 'logged_in' in session


# ROUTE UNTUK AUTENTIKASI (LOGIN & LOGOUT)
@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Halaman login untuk user masuk ke sistem.
    GET: Menampilkan halaman login
    POST: Memproses login user
    """
    # Jika user submit form login (klik tombol login)
    if request.method == 'POST':
        # Ambil data dari form login
        username = request.form['username']
        password = request.form['password']

        # Cari user di database berdasarkan username dan password
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id_users, role, username FROM users WHERE username=%s AND password=%s", 
            (username, password)
        )
        user = cursor.fetchone()  # Ambil satu data user
        cursor.close()

        # Jika user ditemukan (login berhasil)
        if user:
            # Simpan informasi user ke session (untuk mengingat user sudah login)
            session['logged_in'] = True      # Tandai bahwa user sudah login
            session['user_id'] = user[0]     # Simpan ID user
            session['role'] = user[1]        # Simpan role (gudang/kasir)
            session['username'] = user[2]    # Simpan username

            # Tampilkan pesan selamat datang
            flash(f"Selamat datang, {user[2]}!", "success")
            
            # Arahkan user ke halaman sesuai role-nya
            # Jika role = gudang, ke halaman gudang. Jika kasir, ke halaman kasir
            if user[1] == 'gudang':
                return redirect(url_for('gudang_barang'))
            else:
                return redirect(url_for('kasir'))
        
        # Jika user tidak ditemukan (login gagal)
        flash("Username atau Password salah!", "danger")

    # Tampilkan halaman login
    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Fungsi untuk logout (keluar dari sistem).
    Menghapus semua data session user.
    """
    session.clear()  # Hapus semua data session
    flash("Anda telah keluar.", "info")
    return redirect(url_for('login'))


# ROUTE UNTUK GUDANG (MANAJEMEN BARANG)
@app.route('/gudang')
def gudang_barang():
    """
    Halaman utama gudang dengan pagination (limit 5 per halaman).
    Hanya bisa diakses jika user sudah login.
    """
    # Cek apakah user sudah login, jika belum arahkan ke login
    if not is_logged_in():
        return redirect(url_for('login'))
    
    # Ambil parameter page dari URL, default = 1
    page = request.args.get('page', 1, type=int)
    limit = 10  # Jumlah barang per halaman
    offset = (page - 1) * limit  # Hitung offset (mulai dari mana)
    
    cursor = mysql.connection.cursor()
    
    # Hitung total barang di database
    cursor.execute("SELECT COUNT(*) FROM gudang")
    total_barang = cursor.fetchone()[0]
    
    # Hitung total halaman (pembulatan ke atas)
    total_pages = math.ceil(total_barang / limit) if total_barang > 0 else 1
    
    # Ambil data barang sesuai halaman (dengan LIMIT dan OFFSET)
    cursor.execute(
        "SELECT * FROM gudang ORDER BY id_gudang DESC LIMIT %s OFFSET %s",
        (limit, offset)
    )
    data_barang = cursor.fetchall()
    cursor.close()
    
    # Tampilkan halaman gudang dengan data barang dan info pagination
    return render_template(
        'gudang/barang.html',
        barang=data_barang,
        page=page,
        total_pages=total_pages,
        total_barang=total_barang
    )


@app.route('/gudang/barang/tambah', methods=['POST'])
def tambah_barang():
    """
    Fungsi untuk menambah barang baru ke gudang.
    Menerima data dari form dan menyimpannya ke database.
    """
    try:
        # Ambil data dari form
        barcode = request.form.get('barcode')
        nama_barang = request.form.get('nama_barang')
        harga_jual = request.form.get('harga_jual')
        stok = request.form.get('stok')
        
        # Simpan data barang baru ke database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO gudang (barcode, nama_barang, harga_jual, stok) VALUES (%s, %s, %s, %s)", 
            (barcode, nama_barang, harga_jual, stok)
        )
        mysql.connection.commit()  # Simpan perubahan ke database
        cursor.close()
        
        flash("Barang berhasil ditambah!", "success")
    except Exception as error:
        # Jika terjadi error (biasanya karena barcode sudah ada)
        flash("Gagal menambah barang karena barcode sudah digunakan", "danger")
    
    # Kembali ke halaman gudang
    return redirect(url_for('gudang_barang'))


@app.route('/gudang/barang/edit/<int:id>', methods=['POST'])
def edit_barang(id):
    """
    Fungsi untuk mengedit/update data barang yang sudah ada.
    
    Args:
        id (int): ID barang yang akan diedit
    """
    try:
        # Ambil data baru dari form
        barcode = request.form.get('barcode')
        nama_barang = request.form.get('nama_barang')
        harga_jual = request.form.get('harga_jual')
        stok = request.form.get('stok')
        
        # Update data barang di database
        cursor = mysql.connection.cursor()
        cursor.execute(
            """UPDATE gudang 
               SET barcode=%s, nama_barang=%s, harga_jual=%s, stok=%s 
               WHERE id_gudang=%s""",
            (barcode, nama_barang, harga_jual, stok, id)
        )
        mysql.connection.commit()  # Simpan perubahan
        cursor.close()
        
        flash("Barang berhasil diperbarui!", "success")
    except Exception as error:
        flash(f"Gagal update: {str(error)}", "danger")
    
    return redirect(url_for('gudang_barang'))


@app.route('/gudang/barang/hapus/<int:id>')
def hapus_barang(id):
    """
    Fungsi untuk menghapus barang dari gudang.
    Juga menghapus riwayat transaksi terkait barang tersebut.
    
    Args:
        id (int): ID barang yang akan dihapus
    """
    cursor = mysql.connection.cursor()
    try:
        # PENTING: Hapus item transaksi terkait dulu sebelum hapus barang
        # Ini dilakukan agar tidak terjadi error Foreign Key
        cursor.execute("DELETE FROM transaksi_item WHERE id_gudang=%s", (id,))
        
        # Setelah itu baru hapus barang utamanya
        cursor.execute("DELETE FROM gudang WHERE id_gudang=%s", (id,))
        
        mysql.connection.commit()  # Simpan perubahan
        flash("Barang dan riwayat transaksi terkait berhasil dihapus!", "success")
    except Exception as error:
        # Jika terjadi error, batalkan semua perubahan
        mysql.connection.rollback()
        flash(f"Gagal menghapus: Barang ini mungkin bagian dari data penting. {str(error)}", "danger")
    finally:
        cursor.close()
    
    return redirect(url_for('gudang_barang'))


# ROUTE UNTUK KASIR (TRANSAKSI PENJUALAN)
@app.route('/kasir')
def kasir():
    """
    Halaman utama kasir untuk melakukan transaksi penjualan.
    Menampilkan daftar barang, keranjang belanja, dan riwayat transaksi.
    """
    # Cek apakah user sudah login
    if not is_logged_in():
        return redirect(url_for('login'))
    
    # Inisialisasi keranjang belanja di session jika belum ada
    if 'keranjang' not in session:
        session['keranjang'] = []
    
    # Ambil data barang yang stoknya masih ada (stok > 0)
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id_gudang, barcode, nama_barang, harga_jual, stok FROM gudang WHERE stok > 0")
    data_barang = cursor.fetchall()
    
    # Ambil 10 riwayat transaksi terakhir untuk ditampilkan
    cursor.execute("""
        SELECT t.id_transaksi, t.total_harga, t.created_at, u.username 
        FROM transaksi t 
        JOIN users u ON t.id_users = u.id_users 
        ORDER BY t.created_at DESC 
    """)
    riwayat_transaksi = cursor.fetchall()
    cursor.close()

    # Hitung total harga semua item di keranjang (Grand Total)
    grand_total = sum(item['subtotal'] for item in session['keranjang'])
    
    # Tampilkan halaman kasir
    return render_template(
        'kasir/kasir.html', 
        barang=data_barang, 
        riwayat=riwayat_transaksi, 
        keranjang=session['keranjang'],
        grand_total=grand_total
    )


@app.route('/kasir/tambah', methods=['POST'])
def kasir_tambah():
    """
    Fungsi untuk menambahkan barang ke keranjang belanja.
    Jika barang sudah ada di keranjang, jumlahnya akan ditambah.
    """
    # Ambil data dari form
    id_barang = request.form.get('id_barang')
    jumlah = int(request.form.get('qty', 1))  # Default jumlah = 1 jika tidak diisi

    # Cari informasi barang dari database
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT id_gudang, barcode, nama_barang, harga_jual, stok FROM gudang WHERE id_gudang=%s", 
        (id_barang,)
    )
    barang = cursor.fetchone()
    cursor.close()

    # Jika barang ditemukan
    if barang:
        # Ambil keranjang dari session
        keranjang = session.get('keranjang', [])
        
        # Cek apakah barang sudah ada di keranjang
        barang_sudah_ada = False
        for item in keranjang:
            # Jika barang sudah ada di keranjang
            if item['id'] == str(id_barang):
                # Cek apakah stok cukup untuk ditambah
                if item['qty'] + jumlah <= barang[4]:  # barang[4] = stok
                    # Tambah jumlah barang di keranjang
                    item['qty'] += jumlah
                    # Update subtotal
                    item['subtotal'] = item['qty'] * item['harga']
                else:
                    # Jika stok tidak cukup, tampilkan pesan error
                    flash(f"Stok tidak cukup! Sisa: {barang[4]}", "danger")
                
                barang_sudah_ada = True
                break
        
        # Jika barang belum ada di keranjang, tambahkan sebagai item baru
        if not barang_sudah_ada:
            if jumlah <= barang[4]: #ngecek stok cukup
                    keranjang.append({
                    'id': str(barang[0]),           # ID barang
                    'barcode': barang[1],           # Barcode
                    'nama': barang[2],              # Nama barang
                    'harga': barang[3],             # Harga jual
                    'qty': jumlah,                  # Jumlah yang dibeli
                    'subtotal': barang[3] * jumlah  # Subtotal (harga x jumlah)
                })
            else:
                flash(f"Stok tidak cukup! Sisa: {barang[4]}", "danger")
        
        # Simpan keranjang kembali ke session
        session['keranjang'] = keranjang
        session.modified = True  # Tandai bahwa session sudah dimodifikasi
        
    return redirect(url_for('kasir'))


@app.route('/kasir/hapus/<int:index>')
def kasir_hapus(index):
    """
    Fungsi untuk menghapus item dari keranjang belanja.
    
    Args:
        index (int): Urutan item di keranjang yang akan dihapus (mulai dari 0)
    """
    keranjang = session.get('keranjang', [])
    
    # Cek apakah index valid (ada dalam keranjang)
    if 0 <= index < len(keranjang):
        keranjang.pop(index)  # Hapus item dari keranjang
        session['keranjang'] = keranjang
        session.modified = True
    
    return redirect(url_for('kasir'))


@app.route('/kasir/bayar', methods=['POST'])
def kasir_bayar():
    """
    Fungsi untuk memproses pembayaran/checkout.
    
    Langkah-langkah:
    1. Simpan data transaksi ke tabel transaksi
    2. Simpan detail item yang dibeli ke tabel transaksi_item
    3. Kurangi stok barang di gudang
    4. Kosongkan keranjang
    """
    keranjang = session.get('keranjang', [])
    
    # Jika keranjang kosong, kembali ke halaman kasir
    if not keranjang:
        return redirect(url_for('kasir'))

    cursor = mysql.connection.cursor()
    try:
        # LANGKAH 1: Hitung total harga semua item di keranjang
        total_harga = sum(item['subtotal'] for item in keranjang)
        
        # LANGKAH 2: Simpan data transaksi ke tabel transaksi
        cursor.execute(
            "INSERT INTO transaksi (id_users, total_harga, created_at) VALUES (%s, %s, NOW())", 
            (session['user_id'], total_harga)
        )
        id_transaksi = cursor.lastrowid  # Ambil ID transaksi yang baru dibuat

        # LANGKAH 3: Simpan detail setiap item dan kurangi stok
        for item in keranjang:
            # Simpan detail item ke tabel transaksi_item
            cursor.execute(
                "INSERT INTO transaksi_item (id_transaksi, id_gudang, qty, harga) VALUES (%s, %s, %s, %s)", 
                (id_transaksi, item['id'], item['qty'], item['harga'])
            )
            
            # Kurangi stok barang di gudang
            cursor.execute(
                "UPDATE gudang SET stok = stok - %s WHERE id_gudang = %s", 
                (item['qty'], item['id'])
            )
        
        # Simpan semua perubahan ke database
        mysql.connection.commit()
        
        # LANGKAH 4: Kosongkan keranjang setelah transaksi berhasil
        session['keranjang'] = []
        
        flash("Transaksi Berhasil Disimpan!", "success")
    except Exception as error:
        # Jika terjadi error, batalkan semua perubahan
        mysql.connection.rollback()
        flash(f"Gagal: {str(error)}", "danger")
    finally:
        cursor.close()
    
    return redirect(url_for('kasir'))


# JALANKAN APLIKASI
if __name__ == '__main__':
    # Jalankan aplikasi Flask
    # host='0.0.0.0' = bisa diakses dari perangkat lain di jaringan yang sama (kek sama wifi gitu)
    # port=11111 = aplikasi berjalan di port 11111
    # debug=True = mode development (auto-reload jika ada perubahan code)
    app.run(host='0.0.0.0', port=11111, debug=True)