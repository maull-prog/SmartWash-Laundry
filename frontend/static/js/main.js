/* ============================================
   Smart Wash Laundry — Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
    // ── Auto-dismiss flash messages ──
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-12px)';
            setTimeout(function () { msg.remove(); }, 300);
        }, 5000);
    });

    // ── Logout confirmation ──
    const logoutBtns = document.querySelectorAll('.btn-logout');
    logoutBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            if (confirm('Apakah Anda yakin ingin logout?')) {
                window.location.href = btn.getAttribute('href') || '/logout';
            }
        });
    });

    // ── Confirm delete/deactivate buttons ──
    document.querySelectorAll('[data-confirm]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm(btn.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

    // ── Dashboard: Update status buttons (AJAX) ──
    document.querySelectorAll('.btn-update-status').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const id = btn.getAttribute('data-id');
            const row = btn.closest('tr');

            btn.disabled = true;
            btn.textContent = 'Memproses...';

            fetch('/transaksi/update_status/' + id, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.success) {
                        // Reload page to reflect changes
                        window.location.reload();
                    } else {
                        alert(data.message || 'Gagal memperbarui status.');
                        btn.disabled = false;
                        btn.textContent = 'Coba Lagi';
                    }
                })
                .catch(function (err) {
                    alert('Terjadi kesalahan. Silakan coba lagi.');
                    btn.disabled = false;
                    btn.textContent = 'Coba Lagi';
                });
        });
    });

    // ── Riwayat: Search real-time ──
    const searchInput = document.getElementById('searchRiwayat');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                const q = searchInput.value.trim();
                // For kasir: use AJAX search
                const tableBody = document.getElementById('riwayatTableBody');
                if (tableBody) {
                    fetch('/transaksi/search?q=' + encodeURIComponent(q))
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            tableBody.innerHTML = '';
                            if (data.length === 0) {
                                tableBody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding:30px;color:#9CA3AF;">Tidak ada data ditemukan</td></tr>';
                                return;
                            }
                            data.forEach(function (t) {
                                var statusClass = 'badge-' + t.status_cucian;
                                var statusLabel = {
                                    'antrian': 'Antrian',
                                    'sedang_dicuci': 'Sedang Dicuci',
                                    'siap_diambil': 'Siap Diambil',
                                    'selesai': 'Selesai'
                                }[t.status_cucian] || t.status_cucian;

                                var row = '<tr>' +
                                    '<td><span class="link-nota">' + t.kode_transaksi + '</span></td>' +
                                    '<td>' + t.tgl_masuk + '</td>' +
                                    '<td>' + t.nama_pelanggan + '</td>' +
                                    '<td>' + t.no_hp_pelanggan + '</td>' +
                                    '<td><span class="badge ' + statusClass + '">' + statusLabel + '</span></td>' +
                                    '<td>' +
                                    '<button class="btn-action btn-action-view btn-detail-view" data-id="' + t.id_transaksi + '" title="Detail"></button> ' +
                                    '<a href="/transaksi/cetak/' + t.kode_transaksi + '" class="btn-action btn-action-print" target="_blank" title="Cetak"></a>' +
                                    '</td>' +
                                    '</tr>';
                                tableBody.innerHTML += row;
                            });
                            // Re-bind detail view buttons
                            bindDetailButtons();
                        });
                }
            }, 400);
        });
    }

    // ── Transaksi Baru: Service card selection ──
    document.querySelectorAll('.layanan-card').forEach(function (card) {
        card.addEventListener('click', function () {
            card.classList.toggle('selected');
            updateOrderSummary();
        });
    });

    // ── Transaksi Baru: Weight stepper ──
    const weightInput = document.getElementById('beratKg');
    const btnMinus = document.getElementById('weightMinus');
    const btnPlus = document.getElementById('weightPlus');

    if (weightInput && btnMinus && btnPlus) {
        btnMinus.addEventListener('click', function () {
            var val = parseFloat(weightInput.value) || 1;
            if (val > 0.5) {
                weightInput.value = (val - 0.5).toFixed(1);
                updateOrderSummary();
            }
        });

        btnPlus.addEventListener('click', function () {
            var val = parseFloat(weightInput.value) || 0;
            weightInput.value = (val + 0.5).toFixed(1);
            updateOrderSummary();
        });

        weightInput.addEventListener('change', function () {
            var val = parseFloat(weightInput.value);
            if (isNaN(val) || val < 0.5) weightInput.value = '0.5';
            updateOrderSummary();
        });
    }

    // ── Transaksi Baru: Check VIP customer ──
    const namaInput = document.getElementById('namaPelanggan');
    const noHpInput = document.getElementById('noHpPelanggan');
    if (namaInput) {
        namaInput.addEventListener('blur', checkVipCustomer);
    }
    if (noHpInput) {
        noHpInput.addEventListener('blur', checkVipCustomer);
    }

    const promoSelect = document.getElementById('promoSelect');
    if (promoSelect) {
        promoSelect.addEventListener('change', updateOrderSummary);
    }

    const tukarPoin = document.getElementById('tukarPoin');
    if (tukarPoin) {
        tukarPoin.addEventListener('input', function() {
            if (parseInt(tukarPoin.value) > customerPoin) {
                alert('Poin tidak mencukupi! Poin pelanggan saat ini: ' + customerPoin);
                tukarPoin.value = customerPoin;
            }
            updateOrderSummary();
        });
    }

    // ── Transaksi: Form submit with loading ──
    const transaksiForm = document.getElementById('formTransaksi');
    if (transaksiForm) {
        transaksiForm.addEventListener('submit', function (e) {
            // Add selected layanan to form
            var selectedCards = document.querySelectorAll('.layanan-card.selected');
            if (selectedCards.length === 0) {
                e.preventDefault();
                alert('Minimal pilih 1 layanan.');
                return;
            }

            // Remove old hidden inputs
            document.querySelectorAll('.hidden-layanan-input').forEach(function (el) { el.remove(); });

            selectedCards.forEach(function (card) {
                var input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'layanan_ids[]';
                input.value = card.getAttribute('data-id');
                input.className = 'hidden-layanan-input';
                transaksiForm.appendChild(input);
            });

            // Cegah submit langsung, tampilkan modal pembayaran
            e.preventDefault();
            document.getElementById('paymentModal').style.display = 'flex';
        });
    }

    // ── Detail Modal ──
    bindDetailButtons();

    // Close modal
    document.querySelectorAll('.modal-close, .modal-overlay').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (e.target === el) {
                document.getElementById('modalDetail').classList.remove('show');
            }
        });
    });

    // ── Layanan Form: Toggle price fields by kategori ──
    const kategoriSelect = document.getElementById('kategoriLayanan');
    if (kategoriSelect) {
        kategoriSelect.addEventListener('change', togglePriceFields);
        togglePriceFields();
    }

    // ── Owner Riwayat: Filter form ──
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function (e) {
            // normal form submit, GET params
        });
    }
});

// ── Functions ──

function formatRupiah(value) {
    return 'Rp ' + Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

var isVip = false;
var customerPoin = 0;

function checkVipCustomer() {
    var nama = document.getElementById('namaPelanggan');
    var noHp = document.getElementById('noHpPelanggan');
    if (!nama || !nama.value.trim()) return;

    var url = '/transaksi/cek_pelanggan?nama=' + encodeURIComponent(nama.value.trim());
    if (noHp && noHp.value.trim()) {
        url += '&no_hp=' + encodeURIComponent(noHp.value.trim());
    }

    fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var vipBadge = document.getElementById('vipBadge');
            var poinBadge = document.getElementById('poinBadge');
            var poinValue = document.getElementById('poinValue');
            
            if (data.found) {
                customerPoin = data.poin_loyalitas || 0;
                if (poinBadge && poinValue) {
                    poinValue.textContent = customerPoin;
                    poinBadge.style.display = 'inline-block';
                }
                
                if (data.level_member === 'VIP') {
                    isVip = true;
                    if (vipBadge) vipBadge.style.display = 'inline-block';
                } else {
                    isVip = false;
                    if (vipBadge) vipBadge.style.display = 'none';
                }
            } else {
                isVip = false;
                customerPoin = 0;
                if (vipBadge) vipBadge.style.display = 'none';
                if (poinBadge) poinBadge.style.display = 'none';
            }
            
            // Cek batasan input poin
            var tukarPoinInput = document.getElementById('tukarPoin');
            if (tukarPoinInput && parseInt(tukarPoinInput.value) > customerPoin) {
                tukarPoinInput.value = customerPoin;
            }
            
            updateOrderSummary();
        })
        .catch(function () { });
}

function updateOrderSummary() {
    var selectedCards = document.querySelectorAll('.layanan-card.selected');
    var berat = parseFloat(document.getElementById('beratKg')?.value) || 0;
    var orderItemsContainer = document.getElementById('orderItems');
    var subtotalEl = document.getElementById('orderSubtotal');
    var diskonEl = document.getElementById('orderDiskon');
    var totalEl = document.getElementById('orderTotal');

    if (!orderItemsContainer) return;

    orderItemsContainer.innerHTML = '';
    var subtotal = 0;

    selectedCards.forEach(function (card) {
        var nama = card.getAttribute('data-nama');
        var kategori = card.getAttribute('data-kategori');
        var hargaKg = parseFloat(card.getAttribute('data-harga-kg')) || 0;
        var hargaSatuan = parseFloat(card.getAttribute('data-harga-satuan')) || 0;

        var itemTotal = 0;
        var desc = '';

        if (kategori === 'Layanan') {
            itemTotal = hargaKg * berat;
            desc = berat.toFixed(1) + ' kg × ' + formatRupiah(hargaKg);
        } else {
            itemTotal = hargaSatuan;
            desc = '1 × ' + formatRupiah(hargaSatuan);
        }

        subtotal += itemTotal;

        var div = document.createElement('div');
        div.className = 'order-item';
        div.innerHTML = '<div><div class="order-item-name">' + nama + '</div>' +
            '<div style="font-size:11px;color:#9CA3AF;">' + desc + '</div></div>' +
            '<div class="order-item-price">' + formatRupiah(itemTotal) + '</div>';
        orderItemsContainer.appendChild(div);
    });

    if (selectedCards.length === 0) {
        orderItemsContainer.innerHTML = '<div class="empty-state" style="padding:20px"><div style="font-size:24px;margin-bottom:8px"></div><div style="font-size:12px;color:#9CA3AF">Belum ada layanan dipilih</div></div>';
    }

    // Promo discount (manual)
    var diskonPromo = 0;
    var promoName = '';
    var promoSelect = document.getElementById('promoSelect');
    if (promoSelect && promoSelect.value) {
        var selectedOpt = promoSelect.options[promoSelect.selectedIndex];
        var minKg = parseFloat(selectedOpt.getAttribute('data-min-kg'));
        if (berat >= minKg) {
            diskonPromo = parseFloat(selectedOpt.getAttribute('data-diskon'));
            promoName = selectedOpt.text.split('(')[0].trim();
        } else {
            // Revert selection if kg is insufficient
            promoSelect.value = '';
            alert('Syarat minimal berat promo ini adalah ' + minKg + ' Kg');
        }
    }

    // Tukar Poin discount
    var diskonPoin = 0;
    var tukarPoinInput = document.getElementById('tukarPoin');
    if (tukarPoinInput) {
        var tukarPoin = parseInt(tukarPoinInput.value) || 0;
        if (tukarPoin > customerPoin) {
            tukarPoin = customerPoin;
            tukarPoinInput.value = customerPoin;
        }
        diskonPoin = tukarPoin * 1000;
    }

    // VIP discount 10%
    var diskonVip = 0;
    if (isVip) {
        diskonVip = subtotal * 0.10;
    }

    var totalDiskon = diskonPromo + diskonPoin + diskonVip;
    var grandTotal = Math.max(subtotal - totalDiskon, 0);

    if (subtotalEl) subtotalEl.textContent = formatRupiah(subtotal);

    // Baris Diskon VIP (terpisah)
    var rowVip = document.getElementById('rowDiskonVip');
    var diskonVipEl = document.getElementById('orderDiskonVip');
    if (rowVip && diskonVipEl) {
        if (diskonVip > 0) {
            diskonVipEl.textContent = '- ' + formatRupiah(diskonVip);
            rowVip.style.display = 'flex';
        } else {
            rowVip.style.display = 'none';
        }
    }

    // Baris Diskon Promo
    var rowPromo = document.getElementById('rowDiskonPromo');
    if (diskonEl && rowPromo) {
        if (diskonPromo > 0 || diskonPoin > 0) {
            var diskonTexts = [];
            if (diskonPromo > 0) diskonTexts.push('Promo');
            if (diskonPoin > 0) diskonTexts.push('Poin');
            diskonEl.textContent = '- ' + formatRupiah(diskonPromo + diskonPoin);
            rowPromo.style.display = 'flex';
        } else {
            rowPromo.style.display = 'none';
        }
    }

    if (totalEl) totalEl.textContent = formatRupiah(grandTotal);
}

// Alias agar bisa dipanggil dari inline script di template
var recalcTotal = updateOrderSummary;

function bindDetailButtons() {
    document.querySelectorAll('.btn-detail-view').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var id = btn.getAttribute('data-id');
            var modal = document.getElementById('modalDetail');
            var modalBody = document.getElementById('modalDetailBody');

            if (!modal || !modalBody) return;

            modalBody.innerHTML = '<div class="text-center" style="padding:30px;color:#9CA3AF;">Memuat data...</div>';
            modal.classList.add('show');

            fetch('/transaksi/detail/' + id)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.error) {
                        modalBody.innerHTML = '<div class="text-center" style="padding:30px;color:#EF4444;">' + data.error + '</div>';
                        return;
                    }

                    var statusClass = 'badge-' + data.status_cucian;
                    var statusLabel = {
                        'antrian': 'Antrian',
                        'sedang_dicuci': 'Sedang Dicuci',
                        'siap_diambil': 'Siap Diambil',
                        'selesai': 'Selesai'
                    }[data.status_cucian] || data.status_cucian;

                    var bayarLabel = data.status_bayar === 'lunas' ? '<span class="badge badge-aktif">Lunas</span>' : '<span class="badge badge-nonaktif">Belum</span>';

                    var html = '<div class="detail-row"><span class="detail-row-label">ID Nota</span><span class="detail-row-value">' + data.kode_transaksi + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Tanggal Masuk</span><span class="detail-row-value">' + data.tgl_masuk + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Estimasi Selesai</span><span class="detail-row-value">' + data.tgl_estimasi_selesai + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Pelanggan</span><span class="detail-row-value">' + data.nama_pelanggan + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">No HP</span><span class="detail-row-value">' + data.no_hp_pelanggan + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Kasir</span><span class="detail-row-value">' + data.nama_kasir + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Berat</span><span class="detail-row-value">' + data.berat_kg + ' Kg</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Status Cucian</span><span class="badge ' + statusClass + '">' + statusLabel + '</span></div>' +
                        '<div class="detail-row"><span class="detail-row-label">Status Bayar</span>' + bayarLabel + '</div>';

                    if (data.nama_promo && data.nama_promo !== '-') {
                        html += '<div class="detail-row"><span class="detail-row-label">Promo</span><span class="detail-row-value text-green">' + data.nama_promo + '</span></div>';
                    }

                    html += '<h4 style="font-size:14px;font-weight:600;margin:16px 0 8px;">Detail Layanan</h4>';
                    html += '<table class="data-table" style="margin-bottom:12px;"><thead><tr><th>Layanan</th><th>Berat/Qty</th><th>Harga</th><th>Subtotal</th></tr></thead><tbody>';
                    data.details.forEach(function (d) {
                        var bq = d.kategori === 'Layanan' ? d.berat_kg + ' kg' : d.qty + ' pcs';
                        html += '<tr><td>' + d.nama_layanan + '</td><td>' + bq + '</td><td>' + formatRupiah(d.harga_saat_transaksi) + '</td><td>' + formatRupiah(d.subtotal) + '</td></tr>';
                    });
                    html += '</tbody></table>';

                    html += '<div class="order-totals">';
                    if (data.diskon > 0) {
                        html += '<div class="order-total-row"><span>Diskon</span><span class="order-discount">- ' + formatRupiah(data.diskon) + '</span></div>';
                    }
                    html += '<div class="order-grand-total"><span class="order-grand-total-label">TOTAL BAYAR</span><span class="order-grand-total-value">' + formatRupiah(data.total_harga) + '</span></div>';
                    html += '</div>';

                    modalBody.innerHTML = html;
                })
                .catch(function () {
                    modalBody.innerHTML = '<div class="text-center" style="padding:30px;color:#EF4444;">Gagal memuat data.</div>';
                });
        });
    });
}

function togglePriceFields() {
    var kategori = document.getElementById('kategoriLayanan');
    var hargaKgGroup = document.getElementById('groupHargaKg');
    var hargaSatuanGroup = document.getElementById('groupHargaSatuan');

    if (!kategori) return;

    if (kategori.value === 'Add-on') {
        if (hargaKgGroup) hargaKgGroup.style.display = 'none';
        if (hargaSatuanGroup) hargaSatuanGroup.style.display = 'block';
    } else {
        if (hargaKgGroup) hargaKgGroup.style.display = 'block';
        if (hargaSatuanGroup) hargaSatuanGroup.style.display = 'none';
    }
}

// ── Payment & Invoice Modals ──

function closePaymentModal() {
    document.getElementById('paymentModal').style.display = 'none';
}

function submitOrder(statusBayar) {
    document.getElementById('statusBayar').value = statusBayar;
    closePaymentModal();
    
    var form = document.getElementById('formTransaksi');
    var submitBtn = form.querySelector('.btn-confirm');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = ' Menyimpan...';
    }

    var formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadInvoice(data.id_transaksi);
        } else {
            alert(data.message || 'Gagal menyimpan transaksi.');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = ' Konfirmasi Pesanan';
            }
        }
    })
    .catch(err => {
        console.error(err);
        alert('Terjadi kesalahan jaringan.');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = ' Konfirmasi Pesanan';
        }
    });
}

function loadInvoice(id_transaksi) {
    fetch('/transaksi/invoice/' + id_transaksi)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                window.location.href = '/transaksi/baru';
                return;
            }
            renderInvoice(data);
            document.getElementById('invoiceModal').style.display = 'flex';
        })
        .catch(err => {
            console.error(err);
            window.location.href = '/transaksi/baru';
        });
}

function renderInvoice(data) {
    let detailsHtml = '';
    data.details.forEach(d => {
        let qtyStr = d.kategori === 'Layanan' ? d.berat_kg + ' Kg' : d.qty;
        detailsHtml += `
            <div class="invoice-row">
                <div class="inv-col-nama">
                    ${d.nama_layanan}
                </div>
                <div class="inv-col-qty">${qtyStr}</div>
                <div class="inv-col-harga">${formatRupiah(d.harga_saat_transaksi)}</div>
                <div class="inv-col-total">${formatRupiah(d.subtotal)}</div>
            </div>
        `;
    });

    const statusLabel = data.status_bayar === 'lunas' ? 'LUNAS' : 'BELUM LUNAS';
    
    document.getElementById('invoicePrintArea').innerHTML = `
        <div class="invoice-header">
            <h2>Invoice</h2>
            <p>Smartwash Laundry</p>
        </div>
        <div class="invoice-meta">
            <div>
                Kasir : ${data.nama_kasir}<br>
                Pelanggan : ${data.nama_pelanggan}
            </div>
            <div style="text-align: right;">
                Receipt #${data.kode_transaksi}<br>
                Receipt date ${data.tgl_masuk}
            </div>
        </div>
        
        <div class="invoice-table">
            <div class="invoice-row invoice-th">
                <div class="inv-col-nama">NAMA LAYANAN</div>
                <div class="inv-col-qty">KUANTITI</div>
                <div class="inv-col-harga">HARGA</div>
                <div class="inv-col-total">TOTAL</div>
            </div>
            ${detailsHtml}
        </div>
        
        <div class="invoice-summary">
            <div class="invoice-summary-row">
                <span>Subtotal :</span>
                <span>${formatRupiah(data.subtotal)}</span>
            </div>
            <div class="invoice-summary-row">
                <span>Diskon :</span>
                <span>${data.diskon > 0 ? formatRupiah(data.diskon) : '-'}</span>
            </div>
            <div class="invoice-summary-row invoice-grand-total">
                <span>TOTAL :</span>
                <span>${formatRupiah(data.total_harga)}</span>
            </div>
        </div>
        
        <div class="invoice-status ${data.status_bayar === 'lunas' ? 'status-lunas' : 'status-belum'}">
            ${statusLabel}
        </div>
    `;
}

function closeInvoice() {
    document.getElementById('invoiceModal').style.display = 'none';
    window.location.href = '/dashboard';
}
