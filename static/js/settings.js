let categoriesExtended = [];

async function checkStatus() {
    const res = await fetchAuth('/api/simplefin/status');
    const data = await res.json();

    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    if (data.connected) {
        dot.style.background = '#00ff88';
        text.textContent = 'Connected to SimpleFin';
        document.getElementById('connect-form').style.display = 'none';
        document.getElementById('manage-form').style.display = 'block';
    } else {
        dot.style.background = '#ff6b6b';
        text.textContent = 'Not connected';
        document.getElementById('connect-form').style.display = 'block';
        document.getElementById('manage-form').style.display = 'none';
    }
}

async function loadCategories() {
    const res = await fetchAuth('/api/categories/extended');
    if (res.ok) {
        categoriesExtended = await res.json();
        renderCategories();
    }
}

function renderCategories() {
    const select = document.getElementById('manage-category-select');
    if (!select) return;

    if (categoriesExtended.length === 0) {
        select.innerHTML = `<option value="">No categories found</option>`;
        return;
    }

    select.innerHTML = categoriesExtended.map(c => `
    <option value="${c.id}" data-name="${c.name.replace(/"/g, '&quot;')}">${c.name}</option>
`).join('');

    updateManageButtons();
}

function updateManageButtons() {
    const select = document.getElementById('manage-category-select');
    const deleteBtn = document.getElementById('delete-current-btn');
    if (!select || !deleteBtn) return;

    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption) return;

    const name = selectedOption.getAttribute('data-name');
    deleteBtn.disabled = (name === 'Other');
    deleteBtn.style.opacity = (name === 'Other') ? '0.5' : '1';
}

function renameCurrent() {
    const select = document.getElementById('manage-category-select');
    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption) return;

    const id = selectedOption.value;
    const name = selectedOption.getAttribute('data-name');
    renameCategory(id, name);
}

function deleteCurrent() {
    const select = document.getElementById('manage-category-select');
    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption) return;

    const id = selectedOption.value;
    const name = selectedOption.getAttribute('data-name');
    if (name === 'Other') return;
    deleteCategory(id);
}

async function addCategory() {
    const input = document.getElementById('new-cat-name');
    const name = input.value.trim();
    if (!name) return;

    const res = await fetchAuth('/api/categories', {
        method: 'POST',
        body: JSON.stringify({ name })
    });

    if (res.ok) {
        input.value = '';
        loadCategories();
    } else {
        const data = await res.json();
        alert(data.message || 'Error adding category');
    }
}

async function renameCategory(id, oldName) {
    const newName = prompt(`Enter new name for "${oldName}":`, oldName);
    if (!newName || newName.trim() === '' || newName === oldName) return;

    const res = await fetchAuth(`/api/categories/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ name: newName.trim() })
    });

    if (res.ok) {
        loadCategories();
    } else {
        const data = await res.json();
        alert(data.message || 'Error renaming category');
    }
}

async function deleteCategory(id) {
    if (!confirm('Are you sure? This will move all transactions in this category to "Other".')) return;

    const res = await fetchAuth(`/api/categories/${id}`, {
        method: 'DELETE'
    });

    if (res.ok) {
        loadCategories();
    } else {
        const data = await res.json();
        alert(data.message || 'Error deleting category');
    }
}

async function connect() {
    const key = document.getElementById('simplefin-key').value;
    if (!key) { alert('Please enter key'); return; }

    const res = await fetchAuth('/api/simplefin/save-key', {
        method: 'POST',
        body: JSON.stringify({ access_key: key })
    });

    if (res.ok) {
        alert('Connected!');
        checkStatus();
    } else {
        const data = await res.json();
        alert('Failed: ' + (data.message || 'Unknown error'));
    }
}

async function disconnect() {
    if (!confirm('Are you sure?')) return;
    await fetchAuth('/api/simplefin/disconnect', { method: 'POST' });
    checkStatus();
}

async function syncBank() {
    const btn = document.getElementById('sync-btn');
    const resDiv = document.getElementById('sync-result');

    btn.disabled = true;
    btn.textContent = '⏳ Syncing...';
    resDiv.style.display = 'none';

    try {
        const res = await fetchAuth('/api/simplefin/sync', { method: 'POST' });
        const data = await res.json();

        resDiv.style.display = 'block';
        if (res.ok) {
            resDiv.innerHTML = `
            <div style="color: #00ff88; background: rgba(0,255,136,0.1); padding: 1rem; border-radius: 8px;">
                ✓ Sync Complete. Found ${data.accounts.length} accounts.<br>
                ${data.new_transactions ? `+ ${data.new_transactions} new transactions.` : ''}
            </div>
        `;
        } else {
            resDiv.innerHTML = `<div style="color: #ff6b6b;">Error: ${data.message}</div>`;
        }
    } catch (e) {
        resDiv.style.display = 'block';
        resDiv.innerHTML = `<div style="color: #ff6b6b;">Network Error</div>`;
    }

    btn.disabled = false;
    btn.textContent = 'Sync Now';
}

async function loadAccounts() {
    try {
        const res = await fetchAuth('/api/accounts');
        if (res.ok) {
            const accounts = await res.json();
            renderAccounts(accounts);
        }
    } catch (e) {
        console.error(e);
    }
}

function renderAccounts(accounts) {
    const list = document.getElementById('accounts-list');
    if (!list) return;

    if (accounts.length === 0) {
        list.innerHTML = '<p class="text-muted">No accounts found.</p>';
        return;
    }

    list.innerHTML = accounts.map(acc => `
        <div class="account-item flex align-center mb-2">
            <div style="flex-grow: 1;">
                <strong>${acc.name}</strong> <span class="text-muted">(${acc.type})</span>
                ${acc.is_manual ? '<span class="badge">Manual</span>' : '<span class="text-muted"> synced</span>'}
            </div>
            <div class="mr-2" style="font-size: 1.1rem;">
                ${formatCurrency(acc.balance)}
            </div>
            <button class="btn-icon-delete" onclick="deleteAccount(${acc.id})"><i class="fas fa-trash"></i></button>
        </div>
    `).join('');
}

async function addAccount() {
    const name = document.getElementById('new-account-name').value;
    const balance = document.getElementById('new-account-balance').value;
    const type = document.getElementById('new-account-type').value;

    if (!name) return alert('Name is required');

    const res = await fetchAuth('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({ name, balance: balance || 0, type })
    });

    if (res.ok) {
        document.getElementById('new-account-name').value = '';
        document.getElementById('new-account-balance').value = '';
        loadAccounts();
    } else {
        alert('Failed to add account');
    }
}

async function deleteAccount(id) {
    if (!confirm('Delete this account? Associated transactions will NOT be deleted, but unlinked.')) return;
    const res = await fetchAuth(`/api/accounts/${id}`, { method: 'DELETE' });
    if (res.ok) loadAccounts();
}


async function exportData() {
    // Direct download using fetchAuth to get token, then blob
    try {
        const res = await fetchAuth('/api/export/transactions');
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'finance_export.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } else {
            alert('Export failed');
        }
    } catch (e) {
        console.error(e);
        alert('Export failed');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadCategories();
    loadAccounts();
});
