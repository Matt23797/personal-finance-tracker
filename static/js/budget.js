const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM

async function loadBudget() {
    const monthDisplay = document.getElementById('month-display');
    if (monthDisplay) {
        monthDisplay.textContent = new Date().toLocaleString('default', { month: 'long', year: 'numeric' });
    }

    try {
        // Get status
        const statusRes = await fetchAuth(`/api/budget/status?month=${currentMonth}`);
        const status = await statusRes.json();

        // Get projection
        const projRes = await fetchAuth('/api/budget/projection');
        const proj = await projRes.json();

        const projectedIncome = proj.projected_income;
        const totalBudgeted = status.total_budget;

        const projectedIncomeEl = document.getElementById('projected-income');
        const leftToBudgetEl = document.getElementById('left-to-budget');
        const sourceTextEl = document.getElementById('income-source-text');

        if (projectedIncomeEl) {
            projectedIncomeEl.textContent = projectedIncome.toFixed(2);
            projectedIncomeEl.style.color = proj.is_manual ? '#00ff88' : '#aaa'; // Dimm if not manual
        }
        if (leftToBudgetEl) leftToBudgetEl.textContent = (projectedIncome - totalBudgeted).toFixed(2);

        if (sourceTextEl) {
            if (proj.is_manual) {
                sourceTextEl.textContent = "Manually set by you";
                sourceTextEl.style.color = "#00d9ff";
            } else {
                sourceTextEl.textContent = `Suggested (avg of ${proj.months_analyzed} month(s))`;
                sourceTextEl.style.color = "var(--text-muted)";
            }
        }

        const container = document.getElementById('budget-list');
        if (!container) return;

        // Filter to only show categories with a manual budget limit
        const budgetedCategories = status.categories.filter(c => c.budget > 0);

        if (budgetedCategories.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No budgets set for this month. Click "Set Budget" to start.</p>';
            return;
        }

        const today = new Date();
        const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
        const currentDay = today.getDate();
        const monthProgress = currentDay / daysInMonth;

        container.innerHTML = budgetedCategories.map(c => {
            const percent = Math.min(c.percent, 100);
            const color = percent > 100 ? '#ff6b6b' : (percent > 90 ? '#feca57' : '#00d9ff');

            // Burn rate calculation: compare spending progress to time progress
            const spendingProgress = c.budget > 0 ? (c.spent / c.budget) : 0;
            let burnMessage = '';
            let burnColor = 'var(--text-muted)';

            if (c.budget > 0) {
                const diff = spendingProgress - monthProgress;
                if (diff > 0.1) {
                    burnMessage = `⚠ Trending ${Math.round(diff * 100)}% over pace`;
                    burnColor = '#ff6b6b';
                } else if (diff < -0.1 && spendingProgress > 0) {
                    burnMessage = `✨ Trending under pace`;
                    burnColor = '#00ff88';
                } else {
                    burnMessage = `On track for ${new Date().toLocaleString('default', { month: 'short' })}`;
                }
            }

            return `
                <div style="margin-bottom: 1.5rem; position: relative;" class="budget-item" data-category="${c.category}">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <strong>${c.category}</strong>
                            <div class="budget-actions" style="display: flex; gap: 5px; opacity: 0; transition: opacity 0.2s;">
                                <button onclick="editBudget('${c.category}', ${c.budget})" style="background:none; border:none; cursor:pointer; font-size: 0.8rem; color: #00d9ff; padding: 0;">✎</button>
                                <button onclick="deleteBudget('${c.category}')" style="background:none; border:none; cursor:pointer; font-size: 0.8rem; color: #ff6b6b; padding: 0;">✕</button>
                            </div>
                        </div>
                        <span>
                            <span style="color: ${color}; font-weight: bold;">$${c.spent.toFixed(0)}</span>
                            <span style="color: var(--text-muted);"> / $${c.budget.toFixed(0)}</span>
                        </span>
                    </div>
                    <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: ${percent}%; background: ${color}; transition: width 0.5s;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-top: 0.3rem;">
                        <span style="color: ${burnColor}; font-weight: 500;">${burnMessage}</span>
                        <span style="color: var(--text-muted);">
                            ${c.remaining >= 0 ? `$${c.remaining.toFixed(0)} left` : `$${Math.abs(c.remaining).toFixed(0)} over`}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

        // Add hover effect via CSS injection if not present
        if (!document.getElementById('budget-hover-style')) {
            const style = document.createElement('style');
            style.id = 'budget-hover-style';
            style.textContent = `
                .budget-item:hover .budget-actions { opacity: 1 !important; }
            `;
            document.head.appendChild(style);
        }

    } catch (error) {
        console.error('Error loading budget:', error);
    }
}

function editBudget(category, amount) {
    const catSelect = document.getElementById('budget-category');
    const amountInput = document.getElementById('budget-amount');

    // Check if category exists in dropdown
    let exists = false;
    for (let i = 0; i < catSelect.options.length; i++) {
        if (catSelect.options[i].value === category) {
            catSelect.value = category;
            exists = true;
            break;
        }
    }

    if (!exists) {
        catSelect.value = "Custom";
        const customInput = document.getElementById('custom-category-input');
        customInput.style.display = 'block';
        customInput.value = category;
    } else {
        checkCustomCategory(catSelect);
    }

    amountInput.value = amount;
    openBudgetModal();
}

async function deleteBudget(category) {
    if (!confirm(`Are you sure you want to remove the budget for ${category}?`)) return;

    const res = await fetchAuth(`/api/budget/${encodeURIComponent(category)}?month=${currentMonth}`, {
        method: 'DELETE'
    });

    if (res.ok) {
        loadBudget();
    } else {
        alert('Failed to delete budget');
    }
}

function openBudgetModal() {
    const modal = document.getElementById('budget-modal');
    if (modal) modal.classList.add('active');
}

function closeBudgetModal() {
    const modal = document.getElementById('budget-modal');
    if (modal) modal.classList.remove('active');

    // Reset inputs
    const select = document.getElementById('budget-category');
    const customInput = document.getElementById('custom-category-input');
    if (select) select.value = "Housing";
    if (customInput) {
        customInput.style.display = 'none';
        customInput.value = '';
    }
}

function checkCustomCategory(select) {
    const customInput = document.getElementById('custom-category-input');
    if (!customInput) return;

    if (select.value === 'Custom') {
        customInput.style.display = 'block';
        customInput.focus();
    } else {
        customInput.style.display = 'none';
    }
}

async function saveBudget() {
    const catSelect = document.getElementById('budget-category');
    const customInput = document.getElementById('custom-category-input');
    const amountInput = document.getElementById('budget-amount');

    if (!catSelect || !amountInput) return;

    let category = catSelect.value;
    if (category === 'Custom' && customInput) {
        category = customInput.value.trim();
    }

    const amount = parseFloat(amountInput.value);

    if (!category || (amount !== 0 && !amount)) return; // Allow 0, check for NaN

    const res = await fetchAuth('/api/budget', {
        method: 'POST',
        body: JSON.stringify({ category, amount, month: currentMonth })
    });

    if (res.ok) {
        closeBudgetModal();
        loadBudget();
    }
}

function openIncomeModal() {
    const modal = document.getElementById('income-modal');
    if (modal) modal.classList.add('active');
}

function closeIncomeModal() {
    const modal = document.getElementById('income-modal');
    if (modal) modal.classList.remove('active');
}

async function saveIncome() {
    const amountInput = document.getElementById('manual-income-amount');
    if (!amountInput) return;

    const amount = parseFloat(amountInput.value);
    if (!amount && amount !== 0) return;

    const res = await fetchAuth('/api/budget/income', {
        method: 'POST',
        body: JSON.stringify({ amount, month: currentMonth })
    });

    if (res.ok) {
        closeIncomeModal();
        loadBudget();
    }
}

document.addEventListener('DOMContentLoaded', loadBudget);
