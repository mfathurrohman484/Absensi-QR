from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
import qrcode
import os
from flask import make_response
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'secretkey'

# ======================================
# KONFIGURASI DATABASE
# ======================================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'absensi_qr'

mysql = MySQL(app)

# ======================================
# LOGIN
# ======================================
@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username=%s AND password=%s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        if user:

            session['login'] = True
            session['username'] = username
            session['role'] = user[4]

            # JIKA ADMIN
            if user[4] == 'admin':
                return redirect('/dashboard')

            # JIKA USER
            else:
                return redirect('/user_dashboard')

        else:
            # FIX: Redirect balik ke login dengan pesan error
            return render_template('login.html', error='Username atau password salah!')

    return render_template('login.html')


# ======================================
# DASHBOARD ADMIN
# ======================================
@app.route('/dashboard')
def dashboard():

    if 'login' not in session:
        return redirect('/')

    # FIX: Cek role, hanya admin yang boleh akses
    if session.get('role') != 'admin':
        return redirect('/user_dashboard')

    cursor = mysql.connection.cursor()

    # TOTAL USERS
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # TOTAL ABSENSI
    cursor.execute("SELECT COUNT(*) FROM absensi")
    total_absensi = cursor.fetchone()[0]

    # DATA GRAFIK ABSENSI
    cursor.execute(
        """
        SELECT tanggal, COUNT(*)
        FROM absensi
        GROUP BY tanggal
        ORDER BY tanggal ASC
        """
    )

    chart = cursor.fetchall()

    labels = []
    values = []

    for row in chart:
        labels.append(str(row[0]))
        values.append(row[1])

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_absensi=total_absensi,
        labels=labels,
        values=values
    )


# ======================================
# DASHBOARD USER
# ======================================
@app.route('/user_dashboard')
def user_dashboard():

    if 'login' not in session:
        return redirect('/')

    username = session['username']

    cursor = mysql.connection.cursor()

    # AMBIL DATA USER
    cursor.execute(
        """
        SELECT * FROM users
        WHERE username=%s
        """,
        (username,)
    )

    user = cursor.fetchone()

    # RIWAYAT ABSENSI USER
    cursor.execute(
        """
        SELECT *
        FROM absensi
        WHERE user_id=%s
        ORDER BY id DESC
        """,
        (user[0],)
    )

    riwayat = cursor.fetchall()

    return render_template(
        'user_dashboard.html',
        user=user,
        riwayat=riwayat
    )


# ======================================
# LOGOUT
# ======================================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# ======================================
# DATA USERS
# ======================================
@app.route('/users')
def users():

    if 'login' not in session:
        return redirect('/')

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM users")

    data = cursor.fetchall()

    return render_template('users.html', users=data)


# ======================================
# TAMBAH USER
# FIX: Dipisah dari edit_user, logika QR dipindah ke sini
# ======================================
@app.route('/tambah_user', methods=['GET', 'POST'])
def tambah_user():

    if 'login' not in session:
        return redirect('/')

    if request.method == 'POST':

        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cursor = mysql.connection.cursor()

        # SIMPAN USER
        cursor.execute(
            """
            INSERT INTO users(nama, username, password, role)
            VALUES(%s,%s,%s,%s)
            """,
            (nama, username, password, role)
        )

        mysql.connection.commit()

        # AMBIL ID USER TERAKHIR
        user_id = cursor.lastrowid

        # ======================================
        # GENERATE QR CODE
        # ======================================
        qr_data = f'USER-{user_id}'

        img = qrcode.make(qr_data)

        # BUAT FOLDER JIKA BELUM ADA
        os.makedirs('static/qrcode', exist_ok=True)

        # NAMA FILE QR
        filename = f'{user_id}.png'

        # PATH FILE
        save_path = os.path.join('static', 'qrcode', filename)

        # SIMPAN QR
        img.save(save_path)

        # SIMPAN NAMA FILE QR KE DATABASE
        cursor.execute(
            """
            UPDATE users
            SET qr_code=%s
            WHERE id=%s
            """,
            (filename, user_id)
        )

        mysql.connection.commit()

        return redirect('/users')

    return render_template('tambah_user.html')


# ======================================
# EDIT USER
# FIX: Sekarang sudah dipisah dari tambah_user
# ======================================
@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):

    if 'login' not in session:
        return redirect('/')

    cursor = mysql.connection.cursor()

    # JIKA FORM DISUBMIT
    if request.method == 'POST':

        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cursor.execute(
            """
            UPDATE users
            SET
                nama=%s,
                username=%s,
                password=%s,
                role=%s
            WHERE id=%s
            """,
            (nama, username, password, role, id)
        )

        mysql.connection.commit()

        return redirect('/users')

    # AMBIL DATA USER
    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id=%s
        """,
        (id,)
    )

    user = cursor.fetchone()

    return render_template('edit_user.html', user=user)


# ======================================
# HAPUS USER
# ======================================
@app.route('/hapus_user/<int:id>')
def hapus_user(id):

    if 'login' not in session:
        return redirect('/')

    cursor = mysql.connection.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (id,))

    mysql.connection.commit()

    return redirect('/users')


# ======================================
# HALAMAN SCAN QR
# ======================================
@app.route('/scan')
def scan():

    if 'login' not in session:
        return redirect('/')

    return render_template('scan.html')


# ======================================
# PROSES ABSENSI
# FIX: Baca JSON bukan form, return JSON bukan string
# ======================================
@app.route('/absen', methods=['POST'])
def absen():

    # FIX: Baca data JSON dari scan.html
    data = request.get_json()

    if not data or 'qr_code' not in data:
        return jsonify({'error': 'Data tidak valid'}), 400

    qr_code = data['qr_code']

    # VALIDASI QR
    if not qr_code.startswith('USER-'):
        return jsonify({'error': 'QR tidak valid'}), 400

    try:
        user_id = int(qr_code.replace('USER-', ''))
    except:
        return jsonify({'error': 'QR tidak valid'}), 400

    tanggal = datetime.now().date()
    jam = datetime.now().strftime('%H:%M:%S')

    cursor = mysql.connection.cursor()

    # CEK USER ADA
    cursor.execute(
        """
        SELECT * FROM users
        WHERE id=%s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({'error': 'User tidak ditemukan'}), 404

    # CEK SUDAH ABSEN
    cursor.execute(
        """
        SELECT * FROM absensi
        WHERE user_id=%s
        AND tanggal=%s
        """,
        (user_id, tanggal)
    )

    cek = cursor.fetchone()

    if cek:
        return jsonify({'error': f'{user[1]} sudah absen hari ini'}), 409

    # SIMPAN ABSENSI
    cursor.execute(
        """
        INSERT INTO absensi(
            user_id,
            tanggal,
            jam_masuk,
            status
        )
        VALUES(%s,%s,%s,%s)
        """,
        (user_id, tanggal, jam, 'Hadir')
    )

    mysql.connection.commit()

    # FIX: Return JSON agar bisa dibaca scan.html
    return jsonify({
        'nama': user[1],
        'jam': jam,
        'status': 'Hadir'
    })


# ======================================
# LAPORAN ABSENSI
# ======================================
@app.route('/laporan')
def laporan():

    if 'login' not in session:
        return redirect('/')

    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        SELECT
            absensi.id,
            users.nama,
            absensi.tanggal,
            absensi.jam_masuk,
            absensi.status

        FROM absensi

        JOIN users
        ON absensi.user_id = users.id

        ORDER BY absensi.id DESC
        """
    )

    data = cursor.fetchall()

    return render_template('laporan.html', data=data)


# ======================================
# EXPORT PDF
# ======================================
@app.route('/export_pdf')
def export_pdf():

    if 'login' not in session:
        return redirect('/')

    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        SELECT
            users.nama,
            absensi.tanggal,
            absensi.jam_masuk,
            absensi.status

        FROM absensi

        JOIN users
        ON absensi.user_id = users.id

        ORDER BY absensi.id DESC
        """
    )

    data = cursor.fetchall()

    # BUFFER PDF
    buffer = BytesIO()

    # BUAT PDF
    p = canvas.Canvas(buffer)

    # JUDUL
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "LAPORAN ABSENSI")

    # HEADER TABEL
    p.setFont("Helvetica-Bold", 10)

    y = 760

    p.drawString(50, y, "Nama")
    p.drawString(200, y, "Tanggal")
    p.drawString(320, y, "Jam Masuk")
    p.drawString(450, y, "Status")

    # DATA
    p.setFont("Helvetica", 10)

    y -= 20

    for row in data:

        p.drawString(50, y, str(row[0]))
        p.drawString(200, y, str(row[1]))
        p.drawString(320, y, str(row[2]))
        p.drawString(450, y, str(row[3]))

        y -= 20

        # PAGE BARU JIKA PENUH
        if y < 50:
            p.showPage()
            y = 800

    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        'attachment; filename=laporan_absensi.pdf'
    )

    return response


# ======================================
# MAIN
# ======================================
if __name__ == '__main__':

    app.run(debug=True)
