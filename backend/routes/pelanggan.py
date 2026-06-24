from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import mysql, login_required

pelanggan_bp = Blueprint('pelanggan', __name__)


@pelanggan_bp.route('/pelanggan')
@login_required
def daftar_pelanggan():
    """Menampilkan daftar seluruh pelanggan."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM pelanggan
        ORDER BY total_transaksi DESC, tgl_daftar DESC
    """)
    pelanggan_list = cur.fetchall()
    cur.close()

    return render_template('pelanggan.html',
                           page_title='Data Pelanggan',
                           pelanggan_list=pelanggan_list)


@pelanggan_bp.route('/pelanggan/set_vip/<int:id>', methods=['POST'])
@login_required
def set_vip(id):
    """AJAX: Mengubah status VIP pelanggan."""
    # Menerima action dari body JSON atau Form
    data = request.get_json()
    action = data.get('action') if data else request.form.get('action')
    
    if action not in ['reguler', 'VIP']:
        return jsonify({'success': False, 'message': 'Aksi tidak valid'}), 400

    try:
        cur = mysql.connection.cursor()
        # Cek ketersediaan pelanggan
        cur.execute("SELECT nama FROM pelanggan WHERE id_pelanggan = %s", (id,))
        pel = cur.fetchone()
        
        if not pel:
            cur.close()
            return jsonify({'success': False, 'message': 'Pelanggan tidak ditemukan'}), 404

        cur.execute("UPDATE pelanggan SET level_member = %s WHERE id_pelanggan = %s", (action, id))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True, 'message': f"Status {pel['nama']} berhasil diubah menjadi {action}."})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
