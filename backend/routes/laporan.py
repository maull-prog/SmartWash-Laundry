from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from app import mysql, login_required, owner_required
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io
import os

laporan_bp = Blueprint('laporan', __name__)


def format_rupiah(value):
    """Format angka ke format Rupiah."""
    try:
        val = float(value)
        return f"Rp {val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "Rp 0"


@laporan_bp.route('/transaksi/cetak/<kode_transaksi>')
@login_required
def cetak_nota(kode_transaksi):
    """Generate PDF nota individual."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan, p.alamat,
               pg.nama_lengkap AS nama_kasir, pr.nama_promo
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN pengguna pg ON t.id_kasir = pg.id_pengguna
        LEFT JOIN promo pr ON t.id_promo = pr.id_promo
        WHERE t.kode_transaksi = %s
    """, (kode_transaksi,))
    trx = cur.fetchone()

    if not trx:
        flash('Transaksi tidak ditemukan.', 'error')
        return redirect(url_for('transaksi.riwayat_transaksi'))

    cur.execute("""
        SELECT dt.*, l.nama_layanan, l.kategori
        FROM detail_transaksi dt
        LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
        WHERE dt.id_transaksi = %s
    """, (trx['id_transaksi'],))
    details = cur.fetchall()
    cur.close()

    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterBold', alignment=TA_CENTER, fontSize=14, spaceAfter=4, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CenterSmall', alignment=TA_CENTER, fontSize=9, spaceAfter=2))
    styles.add(ParagraphStyle(name='LeftNormal', alignment=TA_LEFT, fontSize=10, spaceAfter=2))
    styles.add(ParagraphStyle(name='RightBold', alignment=TA_RIGHT, fontSize=12, fontName='Helvetica-Bold'))

    elements = []

    # Header
    elements.append(Paragraph("SMART WASH LAUNDRY", styles['CenterBold']))
    elements.append(Paragraph("Jl. Contoh No. 123, Kota Bandung", styles['CenterSmall']))
    elements.append(Paragraph("Telp: 0812-3456-7890", styles['CenterSmall']))
    elements.append(Spacer(1, 8 * mm))

    # Info Transaksi
    tgl_masuk = trx['tgl_masuk'].strftime('%d/%m/%Y %H:%M') if trx['tgl_masuk'] else '-'
    tgl_estimasi = trx['tgl_estimasi_selesai'].strftime('%d/%m/%Y') if trx['tgl_estimasi_selesai'] else '-'

    info_data = [
        ['ID Nota', f': {trx["kode_transaksi"]}', 'Tanggal', f': {tgl_masuk}'],
        ['Kasir', f': {trx.get("nama_kasir", "-")}', 'Estimasi', f': {tgl_estimasi}'],
        ['Pelanggan', f': {trx.get("nama_pelanggan", "-")}', 'No HP', f': {trx.get("no_hp_pelanggan", "-")}'],
        ['Berat', f': {trx["berat_kg"]} Kg', '', ''],
    ]
    info_table = Table(info_data, colWidths=[70, 130, 60, 130])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6 * mm))

    # Tabel layanan
    table_data = [['Layanan', 'Berat/Qty', 'Harga Satuan', 'Subtotal']]
    for d in details:
        if d['kategori'] == 'Layanan':
            berat_qty = f"{d['berat_kg']} Kg"
        else:
            berat_qty = f"{d['qty']} pcs"
        table_data.append([
            d['nama_layanan'],
            berat_qty,
            format_rupiah(d['harga_saat_transaksi']),
            format_rupiah(d['subtotal'])
        ])

    detail_table = Table(table_data, colWidths=[150, 80, 90, 90])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A56DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F7FA')]),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 4 * mm))

    # Total
    subtotal = sum(float(d['subtotal']) for d in details)
    diskon = float(trx['diskon']) if trx['diskon'] else 0
    total_bayar = float(trx['total_harga']) if trx['total_harga'] else 0

    total_data = [
        ['', '', 'Subtotal', format_rupiah(subtotal)],
        ['', '', 'Diskon', f"- {format_rupiah(diskon)}"],
        ['', '', 'TOTAL BAYAR', format_rupiah(total_bayar)],
    ]
    total_table = Table(total_data, colWidths=[150, 80, 90, 90])
    total_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (2, -1), (3, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (2, -1), (3, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 10 * mm))

    # Footer
    elements.append(Paragraph("Terima kasih telah menggunakan Smart Wash Laundry!", styles['CenterSmall']))
    elements.append(Paragraph("Barang yang tidak diambil dalam 30 hari bukan tanggung jawab kami.", styles['CenterSmall']))

    doc.build(elements)
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=nota_{kode_transaksi}.pdf'
    return response


# === OWNER RIWAYAT ===

@laporan_bp.route('/owner/riwayat')
@owner_required
def riwayat_owner():
    q = request.args.get('q', '').strip()
    dari = request.args.get('dari', '').strip()
    sampai = request.args.get('sampai', '').strip()

    cur = mysql.connection.cursor()

    query = """
        SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan,
               pg.nama_lengkap AS nama_kasir
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN pengguna pg ON t.id_kasir = pg.id_pengguna
        WHERE 1=1
    """
    params = []

    if q:
        query += " AND (t.kode_transaksi LIKE %s OR p.nama LIKE %s)"
        params.extend([f'%{q}%', f'%{q}%'])

    if dari:
        query += " AND DATE(t.tgl_masuk) >= %s"
        params.append(dari)

    if sampai:
        query += " AND DATE(t.tgl_masuk) <= %s"
        params.append(sampai)

    query += " ORDER BY t.tgl_masuk DESC LIMIT 200"
    cur.execute(query, params)
    transaksi_list = cur.fetchall()
    cur.close()

    return render_template('owner/riwayat_owner.html',
                           page_title='Riwayat Transaksi',
                           transaksi_list=transaksi_list,
                           q=q, dari=dari, sampai=sampai)


@laporan_bp.route('/owner/riwayat/export')
@owner_required
def export_riwayat_pdf():
    """Export rekap transaksi ke PDF sesuai filter."""
    q = request.args.get('q', '').strip()
    dari = request.args.get('dari', '').strip()
    sampai = request.args.get('sampai', '').strip()

    cur = mysql.connection.cursor()

    query = """
        SELECT t.*, p.nama AS nama_pelanggan, pg.nama_lengkap AS nama_kasir
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN pengguna pg ON t.id_kasir = pg.id_pengguna
        WHERE 1=1
    """
    params = []
    if q:
        query += " AND (t.kode_transaksi LIKE %s OR p.nama LIKE %s)"
        params.extend([f'%{q}%', f'%{q}%'])
    if dari:
        query += " AND DATE(t.tgl_masuk) >= %s"
        params.append(dari)
    if sampai:
        query += " AND DATE(t.tgl_masuk) <= %s"
        params.append(sampai)
    query += " ORDER BY t.tgl_masuk DESC"
    cur.execute(query, params)
    transaksi_list = cur.fetchall()
    cur.close()

    # Generate PDF rekap
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2', alignment=TA_CENTER, fontSize=16, spaceAfter=4, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Sub2', alignment=TA_CENTER, fontSize=10, spaceAfter=8))
    styles.add(ParagraphStyle(name='Right2', alignment=TA_RIGHT, fontSize=11, fontName='Helvetica-Bold'))

    elements = []
    elements.append(Paragraph("LAPORAN REKAP TRANSAKSI", styles['Title2']))
    elements.append(Paragraph("Smart Wash Laundry", styles['Sub2']))

    filter_text = "Semua transaksi"
    if dari and sampai:
        filter_text = f"Periode: {dari} s/d {sampai}"
    elif dari:
        filter_text = f"Dari: {dari}"
    elif sampai:
        filter_text = f"Sampai: {sampai}"
    elements.append(Paragraph(filter_text, styles['Sub2']))
    elements.append(Spacer(1, 5 * mm))

    # Tabel
    table_data = [['No', 'Tanggal', 'ID Nota', 'Pelanggan', 'Kasir', 'Total', 'Status']]
    total_omzet = 0
    for i, t in enumerate(transaksi_list):
        tgl = t['tgl_masuk'].strftime('%d/%m/%Y') if t['tgl_masuk'] else '-'
        total = float(t['total_harga']) if t['total_harga'] else 0
        total_omzet += total
        status_label = {
            'antrian': 'Antrian',
            'sedang_dicuci': 'Dicuci',
            'siap_diambil': 'Siap Ambil',
            'selesai': 'Selesai'
        }.get(t['status_cucian'], t['status_cucian'])
        table_data.append([
            str(i + 1),
            tgl,
            t['kode_transaksi'],
            t.get('nama_pelanggan', '-') or '-',
            t.get('nama_kasir', '-') or '-',
            format_rupiah(total),
            status_label
        ])

    col_widths = [25, 65, 70, 90, 80, 75, 60]
    detail_table = Table(table_data, colWidths=col_widths)
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A56DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F7FA')]),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph(f"Total Omzet: {format_rupiah(total_omzet)}", styles['Right2']))
    elements.append(Paragraph(f"Jumlah Transaksi: {len(transaksi_list)}", styles['Right2']))

    doc.build(elements)
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=laporan_rekap_transaksi.pdf'
    return response
