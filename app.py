from flask import *
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = "matcha_secret_key_pro" 

# database 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'matcha_db'

mysql = MySQL(app)

# cek login
def is_logged_in():
    return 'logged_in' in session

# login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id_users, role, username FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            # Set Session
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['role'] = user[1]
            session['username'] = user[2]

            flash(f"Selamat datang, {user[2]}!", "success")
            return redirect(url_for('gudang_barang' if user[1] == 'gudang' else 'kasir'))
        
        flash("Username atau Password salah!", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for('login'))


# gudang
@app.route('/gudang')
def gudang_barang():
    if not is_logged_in(): return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM gudang ORDER BY id_gudang DESC")
    data = cur.fetchall()
    cur.close()
    return render_template('gudang/barang.html', barang=data)

# CRUD gudang
@app.route('/gudang/barang/tambah', methods=['POST'])
def tambah_barang():
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO gudang (barcode, nama_barang, harga_jual, stok) VALUES (%s, %s, %s, %s)", 
                    (request.form.get('barcode'), request.form.get('nama_barang'), 
                     request.form.get('harga_jual'), request.form.get('stok')))
        mysql.connection.commit()
        flash("Barang berhasil ditambah!", "success")
    except Exception as e:
        flash(f"Gagal menambah barang karena barcode sudah digunakan", "danger")
    finally:
        cur.close()
    return redirect(url_for('gudang_barang'))

@app.route('/gudang/barang/edit/<int:id>', methods=['POST'])
def edit_barang(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE gudang SET barcode=%s, nama_barang=%s, harga_jual=%s, stok=%s WHERE id_gudang=%s
        """, (request.form.get('barcode'), request.form.get('nama_barang'), 
              request.form.get('harga_jual'), request.form.get('stok'), id))
        mysql.connection.commit()
        flash("Barang berhasil diperbarui!", "success")
    except Exception as e:
        flash(f"Gagal update: {str(e)}", "danger")
    finally:
        cur.close()
    return redirect(url_for('gudang_barang'))

@app.route('/gudang/barang/hapus/<int:id>')
def hapus_barang(id):
    cur = mysql.connection.cursor()
    try:
        # Menghapus item transaksi terkait dulu agar tidak error Foreign Key
        cur.execute("DELETE FROM transaksi_item WHERE id_gudang=%s", (id,))
        # Baru hapus barang utamanya
        cur.execute("DELETE FROM gudang WHERE id_gudang=%s", (id,))
        mysql.connection.commit()
        flash("Barang dan riwayat transaksi terkait berhasil dihapus!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Gagal menghapus: Barang ini mungkin bagian dari data penting. {str(e)}", "danger")
    finally:
        cur.close()
    return redirect(url_for('gudang_barang'))

# kasir
@app.route('/kasir')
def kasir():
    if not is_logged_in(): return redirect(url_for('login'))
    
    # Inisialisasi keranjang di session jika belum ada
    if 'keranjang' not in session:
        session['keranjang'] = []
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_gudang, barcode, nama_barang, harga_jual, stok FROM gudang WHERE stok > 0")
    data_barang = cur.fetchall()
    
    cur.execute("""
        SELECT t.id_transaksi, t.total_harga, t.created_at, u.username 
        FROM transaksi t JOIN users u ON t.id_users = u.id_users 
        ORDER BY t.created_at DESC LIMIT 10
    """)
    riwayat = cur.fetchall()
    cur.close()

    # Hitung Grand Total untuk ditampilkan
    grand_total = sum(item['subtotal'] for item in session['keranjang'])
    
    return render_template('kasir/kasir.html', 
                           barang=data_barang, 
                           riwayat=riwayat, 
                           keranjang=session['keranjang'],
                           grand_total=grand_total)

@app.route('/kasir/tambah', methods=['POST'])
def kasir_tambah():
    id_barang = request.form.get('id_barang')
    qty = int(request.form.get('qty', 1))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id_gudang, barcode, nama_barang, harga_jual, stok FROM gudang WHERE id_gudang=%s", (id_barang,))
    b = cur.fetchone()
    cur.close()

    if b:
        keranjang = session.get('keranjang', [])
        # Logika cek jika barang sudah ada di keranjang, tambah qty-nya saja
        found = False
        for item in keranjang:
            if item['id'] == str(id_barang):
                if item['qty'] + qty <= b[4]:
                    item['qty'] += qty
                    item['subtotal'] = item['qty'] * item['harga']
                else:
                    flash(f"Stok tidak cukup! Sisa: {b[4]}", "danger")
                found = True
                break
        
        if not found:
            keranjang.append({
                'id': str(b[0]), 'barcode': b[1], 'nama': b[2],
                'harga': b[3], 'qty': qty, 'subtotal': b[3] * qty
            })
        
        session['keranjang'] = keranjang
        session.modified = True
        
    return redirect(url_for('kasir'))

@app.route('/kasir/hapus/<int:index>')
def kasir_hapus(index):
    keranjang = session.get('keranjang', [])
    if 0 <= index < len(keranjang):
        keranjang.pop(index)
        session['keranjang'] = keranjang
        session.modified = True
    return redirect(url_for('kasir'))

@app.route('/kasir/bayar', methods=['POST'])
def kasir_bayar():
    keranjang = session.get('keranjang', [])
    if not keranjang:
        return redirect(url_for('kasir'))

    cur = mysql.connection.cursor()
    try:
        total = sum(item['subtotal'] for item in keranjang)
        # Simpan Transaksi
        cur.execute("INSERT INTO transaksi (id_users, total_harga, created_at) VALUES (%s, %s, NOW())", 
                    (session['user_id'], total))
        id_trx = cur.lastrowid

        for item in keranjang:
            # Simpan Detail
            cur.execute("INSERT INTO transaksi_item (id_transaksi, id_gudang, qty, harga) VALUES (%s, %s, %s, %s)", 
                        (id_trx, item['id'], item['qty'], item['harga']))
            # Potong Stok
            cur.execute("UPDATE gudang SET stok = stok - %s WHERE id_gudang = %s", (item['qty'], item['id']))
        
        mysql.connection.commit()
        session['keranjang'] = [] # Kosongkan setelah bayar
        flash("Transaksi Berhasil Disimpan!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Gagal: {str(e)}", "danger")
    finally:
        cur.close()
    
    return redirect(url_for('kasir'))
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=11111, debug=True)