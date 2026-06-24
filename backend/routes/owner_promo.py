from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import mysql, owner_required

owner_promo_bp = Blueprint('owner_promo', __name__)


@owner_promo_bp.route('/owner/promo')
@owner_required
def promo_list():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM promo ORDER BY id_promo")
    promo = cur.fetchall()
    cur.close()
    return render_template('owner/promo.html',
                           page_title='Kelola Promo',
                           promo=promo)


@owner_promo_bp.route('/owner/promo/tambah', methods=['GET', 'POST'])
@owner_required
def promo_tambah():
    if request.method == 'POST':
        nama = request.form.get('nama_promo', '').strip()
        syarat_min_kg = request.form.get('syarat_min_kg', '0')
        nominal_potongan = request.form.get('nominal_potongan', '0')
        aktif = 1 if request.form.get('aktif') else 0

        if not nama:
            flash('Nama promo wajib diisi.', 'error')
            return render_template('owner/promo_form.html', page_title='Tambah Promo', mode='tambah')

        try:
            syarat_min_kg = float(syarat_min_kg)
            nominal_potongan = float(nominal_potongan)
        except ValueError:
            flash('Format angka tidak valid.', 'error')
            return render_template('owner/promo_form.html', page_title='Tambah Promo', mode='tambah')

        if syarat_min_kg <= 0 or nominal_potongan <= 0:
            flash('Syarat minimal kg dan nominal potongan harus lebih dari 0.', 'error')
            return render_template('owner/promo_form.html', page_title='Tambah Promo', mode='tambah')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO promo (nama_promo, syarat_min_kg, nominal_potongan, aktif)
            VALUES (%s, %s, %s, %s)
        """, (nama, syarat_min_kg, nominal_potongan, aktif))
        mysql.connection.commit()
        cur.close()

        flash('Promo berhasil ditambahkan!', 'success')
        return redirect(url_for('owner_promo.promo_list'))

    return render_template('owner/promo_form.html', page_title='Tambah Promo', mode='tambah')


@owner_promo_bp.route('/owner/promo/edit/<int:id>', methods=['GET', 'POST'])
@owner_required
def promo_edit(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form.get('nama_promo', '').strip()
        syarat_min_kg = request.form.get('syarat_min_kg', '0')
        nominal_potongan = request.form.get('nominal_potongan', '0')
        aktif = 1 if request.form.get('aktif') else 0

        if not nama:
            flash('Nama promo wajib diisi.', 'error')
            cur.execute("SELECT * FROM promo WHERE id_promo = %s", (id,))
            promo = cur.fetchone()
            cur.close()
            return render_template('owner/promo_form.html', page_title='Edit Promo', mode='edit', promo=promo)

        try:
            syarat_min_kg = float(syarat_min_kg)
            nominal_potongan = float(nominal_potongan)
        except ValueError:
            flash('Format angka tidak valid.', 'error')
            return redirect(url_for('owner_promo.promo_edit', id=id))

        cur.execute("""
            UPDATE promo SET nama_promo=%s, syarat_min_kg=%s, nominal_potongan=%s, aktif=%s
            WHERE id_promo=%s
        """, (nama, syarat_min_kg, nominal_potongan, aktif, id))
        mysql.connection.commit()
        cur.close()

        flash('Promo berhasil diperbarui!', 'success')
        return redirect(url_for('owner_promo.promo_list'))

    cur.execute("SELECT * FROM promo WHERE id_promo = %s", (id,))
    promo = cur.fetchone()
    cur.close()

    if not promo:
        flash('Promo tidak ditemukan.', 'error')
        return redirect(url_for('owner_promo.promo_list'))

    return render_template('owner/promo_form.html', page_title='Edit Promo', mode='edit', promo=promo)


@owner_promo_bp.route('/owner/promo/toggle_aktif/<int:id>', methods=['POST'])
@owner_required
def promo_toggle_aktif(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT aktif FROM promo WHERE id_promo = %s", (id,))
    promo = cur.fetchone()

    if not promo:
        flash('Promo tidak ditemukan.', 'error')
    else:
        new_status = 0 if promo['aktif'] else 1
        cur.execute("UPDATE promo SET aktif = %s WHERE id_promo = %s", (new_status, id))
        mysql.connection.commit()
        status_text = 'diaktifkan' if new_status else 'dinonaktifkan'
        flash(f'Promo berhasil {status_text}.', 'success')

    cur.close()
    return redirect(url_for('owner_promo.promo_list'))
