let allTxns = [];
let currentType = 'expense';
let categories = [];

async function loadData() {
    // Fetch Categories
    const catRes = await fetchAuth('/api/categories');
    categories = await catRes.json();

    // Populate filter & bulk dropdowns
    const filterCat = document.getElementById('filter-category');
    const bulkCat = document.getElementById('bulk-category');
    if (filterCat && bulkCat) {
        const options = categories.map(c => `<option value="${c}">${c}</option>`).join('');
        filterCat.innerHTML = '<option value="all">All Categories</option>' + options;
        bulkCat.innerHTML = options;
    }

    // Fetch Incomes & Expenses
    const [incRes, expRes] = await Promise.all([
        fetchAuth('/api/incomes'),
        fetchAuth('/api/expenses')
    ]);

    const incomes = await incRes.json();
    const expenses = await expRes.json();

    // Merge and Sort
    allTxns = [
        ...incomes.map(i => ({ ...i, type: 'income', desc: i.source })),
        ...expenses.map(e => ({ ...e, type: 'expense', desc: e.description || e.category }))
    ].sort((a, b) => new Date(b.date) - new Date(a.date));

    filterData();
}

function filterData() {
    const searchInput = document.getElementById('filter-search');
    const catSelect = document.getElementById('filter-category');
    const typeSelect = document.getElementById('filter-type');
    const minInput = document.getElementById('filter-min');
    const maxInput = document.getElementById('filter-max');

    if (!searchInput || !catSelect || !typeSelect || !minInput || !maxInput) return;

    const searchText = searchInput.value.toLowerCase();
    const category = catSelect.value;
    const type = typeSelect.value;
    const min = parseFloat(minInput.value) || 0;
    const max = parseFloat(maxInput.value) || Infinity;

    const filtered = allTxns.filter(t => {
        const matchesSearch = t.desc.toLowerCase().includes(searchText);
        const matchesCat = category === 'all' || t.category === category || (t.type === 'income' && category === 'Income');
        const matchesType = type === 'all' || t.type === type;
        const matchesAmount = t.amount >= min && t.amount <= max;
        return matchesSearch && matchesCat && matchesType && matchesAmount;
    });

    renderTable(filtered);
}

function renderTable(txns) {
    const tbody = document.getElementById('transaction-table');
    if (!tbody) return;

    if (txns.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">No transactions found.</td></tr>';
        return;
    }

    tbody.innerHTML = txns.map(t => {
        const date = new Date(t.date).toLocaleDateString();
        const color = t.type === 'income' ? '#00ff88' : '#ff6b6b';
        const sign = t.type === 'income' ? '+' : '-';

        let catCell = '';
        if (t.type === 'income') {
            catCell = '<span style="display: inline-block; width: 100%; color: #00ff88; background: rgba(0,255,136,0.1); padding: 0.5rem; border-radius: 8px; font-size: 0.9rem; text-align: left; border: 1px solid rgba(0,255,136,0.2);">Income</span>';
        } else {
            // Dropdown for Expenses
            const options = categories.map(c => `<option value="${c}" ${c === t.category ? 'selected' : ''}>${c}</option>`).join('');
            catCell = `<select onchange="updateCategory(${t.id}, this.value)" style="width: 100%;">
                ${options}
            </select>`;
        }

        return `
            <tr class="border-bottom">
                <td style="padding: 1rem;">
                    <input type="checkbox" class="txn-check" data-id="${t.id}" data-type="${t.type}" onchange="updateBulkBar()">
                </td>
                <td style="padding: 1rem;">${formatDate(t.date)}</td>
                <td style="padding: 1rem;">${t.desc}</td>
                <td style="padding: 1rem; color: ${color}; font-weight: 600;">${sign}${formatCurrency(t.amount)}</td>
                <td style="padding: 1rem;">${catCell}</td>
            </tr>
        `;
    }).join('');
    updateBulkBar();
}

function updateBulkBar() {
    const selected = Array.from(document.querySelectorAll('.txn-check:checked'))
        .filter(cb => cb.getAttribute('data-type') === 'expense'); // only expenses for bulk categorize
    const bar = document.getElementById('bulk-bar');
    const count = document.getElementById('bulk-count');

    if (!bar || !count) return;

    if (selected.length > 0) {
        bar.classList.add('active');
        count.textContent = selected.length;
    } else {
        bar.classList.remove('active');
    }
}

function toggleSelectAll() {
    const selectAllCb = document.getElementById('select-all');
    if (!selectAllCb) return;

    const checked = selectAllCb.checked;
    document.querySelectorAll('.txn-check').forEach(cb => {
        cb.checked = checked;
    });
    updateBulkBar();
}

function deselectAll() {
    const selectAllCb = document.getElementById('select-all');
    if (selectAllCb) selectAllCb.checked = false;
    document.querySelectorAll('.txn-check').forEach(cb => cb.checked = false);
    updateBulkBar();
}

async function applyBulkUpdate() {
    const selectedIds = Array.from(document.querySelectorAll('.txn-check:checked'))
        .filter(cb => cb.getAttribute('data-type') === 'expense')
        .map(cb => parseInt(cb.getAttribute('data-id')));
    const bulkCatSelect = document.getElementById('bulk-category');
    if (!bulkCatSelect) return;

    const newCat = bulkCatSelect.value;

    if (selectedIds.length === 0) return;

    const res = await fetchAuth('/api/expenses/bulk-update', {
        method: 'POST',
        body: JSON.stringify({ ids: selectedIds, category: newCat })
    });

    if (res.ok) {
        deselectAll();
        loadData();
    } else {
        alert('Bulk update failed');
    }
}

async function updateCategory(id, newCat) {
    const txn = allTxns.find(t => t.id === id && t.type === 'expense');
    if (!txn) return;

    const oldCat = txn.category;

    // Optimistic Update
    txn.category = newCat;
    // We don't necessarily need to re-render if the user just changed the select,
    // but doing so ensures the internal state and UI are perfectly synced.
    // filterData(); 

    try {
        const res = await fetchAuth(`/api/expenses/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ category: newCat })
        });

        if (!res.ok) {
            throw new Error('Failed to update');
        }
    } catch (e) {
        alert('Failed to update category. Rolling back.');
        txn.category = oldCat;
        filterData(); // Revert UI
    }
}

// Modal Logic
async function openAddModal(type) {
    currentType = type;
    const modalTitle = document.getElementById('modal-title');
    const catGroup = document.getElementById('cat-group');
    const catSelect = document.getElementById('txn-category');
    const txnDate = document.getElementById('txn-date');

    if (modalTitle) modalTitle.textContent = type === 'income' ? 'Add Income' : 'Add Expense';
    if (catGroup) catGroup.style.display = type === 'income' ? 'none' : 'block';

    if (catSelect) {
        catSelect.innerHTML = categories.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    // Load Accounts
    const accSelect = document.getElementById('txn-account');
    if (accSelect) {
        try {
            const res = await fetchAuth('/api/accounts');
            if (res.ok) {
                const accounts = await res.json();
                accSelect.innerHTML = '<option value="">-- None --</option>' +
                    accounts.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
            }
        } catch (e) {
            console.error('Failed to load accounts for modal');
        }
    }

    if (txnDate) txnDate.valueAsDate = new Date();

    setupModal('add-modal').open();
    hideSmartBadge();
}

function closeAddModal() {
    setupModal('add-modal').close();

    const amountInput = document.getElementById('txn-amount');
    const descInput = document.getElementById('txn-desc');

    if (amountInput) amountInput.value = '';
    if (descInput) descInput.value = '';
}

async function submitTransaction() {
    const amountInput = document.getElementById('txn-amount');
    const descInput = document.getElementById('txn-desc');
    const dateInput = document.getElementById('txn-date');
    const catSelect = document.getElementById('txn-category');

    if (!amountInput || !descInput || !dateInput) return;

    const amount = parseFloat(amountInput.value);
    const description = descInput.value;
    const date = dateInput.value;

    if (!amount || !description || !date) { alert('Please fill all fields'); return; }

    const endpoint = currentType === 'income' ? '/api/incomes' : '/api/expenses';
    const body = { amount, date };

    const accSelect = document.getElementById('txn-account');
    if (accSelect && accSelect.value) {
        body.account_id = accSelect.value;
    }

    if (currentType === 'income') {
        body.source = description;
    } else {
        body.description = description;
        if (catSelect) body.category = catSelect.value;
    }

    const res = await fetchAuth(endpoint, {
        method: 'POST',
        body: JSON.stringify(body)
    });

    if (res.ok) {
        closeAddModal();
        loadData();
    } else {
        alert('Failed to save');
    }
}

// Import Modal Logic
async function openImportModal() {
    setupModal('import-modal').open();
    document.getElementById('import-status').style.display = 'none';
    document.getElementById('import-btn').disabled = false;
    document.getElementById('import-file').value = '';

    // Load accounts for dropdown
    const accountSelect = document.getElementById('import-account');
    if (accountSelect) {
        try {
            const res = await fetchAuth('/api/accounts');
            if (res.ok) {
                const accounts = await res.json();
                accountSelect.innerHTML = '<option value="">-- No specific account --</option>' +
                    accounts.map(a => `<option value="${a.id}">${a.name} (${a.type})</option>`).join('');
            }
        } catch (e) { console.error('Error loading accounts', e); }
    }
}

function closeImportModal() {
    setupModal('import-modal').close();
}

async function processImport() {
    const fileInput = document.getElementById('import-file');
    const accountSelect = document.getElementById('import-account');
    const statusDiv = document.getElementById('import-status');
    const statusText = document.getElementById('import-status-text');
    const importBtn = document.getElementById('import-btn');

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a file first.');
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    if (accountSelect && accountSelect.value) {
        formData.append('account_id', accountSelect.value);
    }

    statusDiv.style.display = 'block';
    importBtn.disabled = true;
    statusText.textContent = 'Uploading and processing file...';

    try {
        const res = await fetchAuth('/api/transactions/import', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (res.ok) {
            statusText.textContent = `Success! ${data.message} (${data.duplicates} duplicates skipped)`;
            setTimeout(() => {
                closeImportModal();
                loadData();
            }, 2000);
        } else {
            alert('Import failed: ' + (data.error || 'Unknown error'));
            statusDiv.style.display = 'none';
            importBtn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        alert('An error occurred during import.');
        statusDiv.style.display = 'none';
        importBtn.disabled = false;
    }
}

// Smart Suggestion Logic
let suggestTimeout;
async function suggestCategory(desc) {
    if (!desc || desc.length < 3) {
        hideSmartBadge();
        return;
    }

    try {
        const res = await fetchAuth('/api/categories/suggest', {
            method: 'POST',
            body: JSON.stringify({ description: desc })
        });
        const data = await res.json();

        if (data.suggested_category) {
            const catSelect = document.getElementById('txn-category');
            if (catSelect) {
                catSelect.value = data.suggested_category;
                showSmartBadge();
            }
        } else {
            hideSmartBadge();
        }
    } catch (e) {
        console.error(e);
    }
}

function showSmartBadge() {
    const badge = document.getElementById('smart-badge');
    if (badge) {
        badge.style.display = 'inline-block';
        badge.classList.add('pop-in');
    }
}

function hideSmartBadge() {
    const badge = document.getElementById('smart-badge');
    if (badge) badge.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    loadData();

    // Smart Categorization Listener
    const descInput = document.getElementById('txn-desc');
    if (descInput) {
        descInput.addEventListener('input', (e) => {
            clearTimeout(suggestTimeout);
            suggestTimeout = setTimeout(() => {
                if (currentType === 'expense') suggestCategory(e.target.value);
            }, 500);
        });
    }
});
