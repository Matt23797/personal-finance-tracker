let categoryChart = null;

async function loadDashboard() {
    const periodSelector = document.getElementById('period-selector');
    if (!periodSelector) return;

    const period = periodSelector.value;
    let startDate = '', endDate = '';

    const now = new Date();
    if (period === 'this-month') {
        startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
        endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
    } else if (period === 'last-30') {
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(now.getDate() - 30);
        startDate = thirtyDaysAgo.toISOString().split('T')[0];
        endDate = now.toISOString().split('T')[0];
    }

    const queryParams = startDate ? `?start_date=${startDate}&end_date=${endDate}` : '';

    try {
        // Summary
        const summaryRes = await fetchAuth(`/api/summary${queryParams}`);
        const summary = await summaryRes.json();

        document.getElementById('total-income').textContent = formatCurrency(summary.total_income).slice(1);
        document.getElementById('total-expense').textContent = formatCurrency(summary.total_expense).slice(1);
        const netFlow = summary.total_income - summary.total_expense;
        const netFlowEl = document.getElementById('net-flow');
        netFlowEl.textContent = formatCurrency(netFlow).slice(1);
        netFlowEl.style.color = netFlow >= 0 ? '#00ff88' : '#ff6b6b';

        // Goals Preview
        loadGoalsPreview();

        // Chart
        const catRes = await fetchAuth(`/api/expenses/by-category${queryParams}`);
        const breakdown = await catRes.json();
        renderChart(breakdown);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadGoalsPreview() {
    const goalsRes = await fetchAuth('/api/goals');
    const goals = await goalsRes.json();
    const goalsContainer = document.getElementById('goals-preview');
    if (!goalsContainer) return;

    if (goals.length === 0) {
        goalsContainer.innerHTML = '<p style="color: var(--text-muted);">No goals set.</p>';
    } else {
        goalsContainer.innerHTML = goals.slice(0, 3).map(g => {
            const progress = Math.min((g.current_amount / g.target_amount) * 100, 100);
            return `
                <div class="mb-1" style="background: rgba(255,255,255,0.03); padding: 0.8rem; border-radius: 8px;">
                    <div class="flex-between mb-1">
                        <strong>${g.description}</strong>
                        <span class="text-primary">${formatCurrency(g.current_amount).replace('.00', '')} / ${formatCurrency(g.target_amount).replace('.00', '')}</span>
                    </div>
                    <div style="height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: ${progress}%; background: linear-gradient(90deg, var(--primary), var(--secondary));"></div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function renderChart(breakdown) {
    const canvas = document.getElementById('categoryChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = Object.keys(breakdown);
    const data = Object.values(breakdown);
    const colors = ['#00d9ff', '#00ff88', '#feca57', '#ff6b6b', '#5f27cd', '#ff9ff3', '#54a0ff'];

    if (categoryChart) categoryChart.destroy();

    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            ...getCommonChartOptions('doughnut'),
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const category = labels[index];
                    window.location.href = `/transactions?category=${encodeURIComponent(category)}`;
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const periodSelector = document.getElementById('period-selector');
    if (periodSelector) {
        periodSelector.addEventListener('change', loadDashboard);
        loadDashboard();
        loadAccountsPreview();
    }
});

async function loadAccountsPreview() {
    const container = document.getElementById('accounts-preview');
    const totalEl = document.getElementById('total-accounts-balance');
    if (!container) return;

    try {
        const res = await fetchAuth('/api/accounts');
        if (res.ok) {
            const accounts = await res.json();

            if (accounts.length === 0) {
                container.innerHTML = '<p class="text-muted">No accounts connected.</p>';
                totalEl.textContent = formatCurrency(0);
                return;
            }

            const total = accounts.reduce((sum, acc) => sum + parseFloat(acc.balance), 0);
            totalEl.textContent = formatCurrency(total);

            container.innerHTML = accounts.map(acc => `
                <div class="flex-between mb-2" style="padding: 0.8rem; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <div>
                        <div style="font-weight: 600;">${acc.name}</div>
                        <div style="font-size: 0.8rem; color: #aaa;">${acc.type} ${acc.is_manual ? '(manual)' : ''}</div>
                    </div>
                    <div style="font-weight: 600; color: #fff;">${formatCurrency(acc.balance)}</div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading accounts:', e);
        container.innerHTML = '<p class="text-danger">Failed to load accounts.</p>';
    }
}
