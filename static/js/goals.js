let currentEditId = null;

async function loadGoals() {
    const res = await fetchAuth('/api/goals');
    const goals = await res.json();

    const container = document.getElementById('goals-container');
    if (!container) return;

    // Always attempt to load/clear chart
    loadGoalChart(goals);

    if (goals.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No goals set yet. Click "+ Add Goal" to start.</p>';
        return;
    }

    container.innerHTML = goals.map(g => {
        const progress = Math.min((g.current_amount / g.target_amount) * 100, 100);
        const color = progress >= 100 ? '#00ff88' : '#00d9ff';

        return `
            <div class="card goal-item mb-1">
                <div class="flex-between mb-1" style="align-items: start;">
                    <div>
                        <div class="flex align-center" style="gap: 8px; margin-bottom: 4px;">
                            <h3 style="margin: 0; font-size: 1.1rem;">${g.description}</h3>
                            <div class="goal-actions" style="display: flex; gap: 8px; opacity: 0; transition: opacity 0.2s;">
                                <button onclick="editGoal(${g.id})" style="background:none; border:none; cursor:pointer; font-size: 0.8rem; color: #00d9ff; padding: 0;"><i class="fas fa-edit"></i></button>
                                <button onclick="deleteGoal(${g.id})" style="background:none; border:none; cursor:pointer; font-size: 0.8rem; color: #ff6b6b; padding: 0;"><i class="fas fa-trash"></i></button>
                            </div>
                        </div>
                        <div class="text-muted" style="font-size: 0.8rem;">
                            Due: ${formatDate(g.deadline)}
                        </div>
                    </div>
                    <div class="text-right">
                        <div style="color: ${color}; font-weight: 700; font-size: 1.1rem;">${formatCurrency(g.current_amount)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">of ${formatCurrency(g.target_amount)}</div>
                    </div>
                </div>
                
                <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem;">
                    <div style="height: 100%; width: ${progress}%; background: ${color}; transition: width 0.5s;"></div>
                </div>
                
                <div class="flex-between text-muted" style="font-size: 0.75rem;">
                    <span>${progress.toFixed(0)}% Complete</span>
                    <span>${formatCurrency(g.target_amount - g.current_amount)} remaining</span>
                </div>
            </div>
        `;
    }).join('');

    // Inject hover styles if not present
    if (!document.getElementById('goal-hover-style')) {
        const style = document.createElement('style');
        style.id = 'goal-hover-style';
        style.textContent = `
            .goal-item:hover .goal-actions { opacity: 1 !important; }
        `;
        document.head.appendChild(style);
    }
}

function openGoalModal() {
    currentEditId = null;
    document.getElementById('modal-title').textContent = "Add Goal";
    document.getElementById('desc').value = '';
    document.getElementById('target').value = '';
    document.getElementById('current').value = '0';
    document.getElementById('deadline').value = '';
    setupModal('goal-modal').open();
}

function closeGoalModal() {
    setupModal('goal-modal').close();
}

async function editGoal(id) {
    const res = await fetchAuth('/api/goals');
    const goals = await res.json();
    const g = goals.find(goal => goal.id === id);

    if (g) {
        currentEditId = id;
        document.getElementById('modal-title').textContent = "Edit Goal";
        document.getElementById('desc').value = g.description;
        document.getElementById('target').value = g.target_amount;
        document.getElementById('current').value = g.current_amount;
        document.getElementById('deadline').value = g.deadline || '';
        setupModal('goal-modal').open();
    }
}

async function saveGoal() {
    const description = document.getElementById('desc').value;
    const target_amount = parseFloat(document.getElementById('target').value);
    const current_amount = parseFloat(document.getElementById('current').value);
    const deadline = document.getElementById('deadline').value;

    if (!description || !target_amount) {
        alert('Description and target amount are required');
        return;
    }

    const payload = { description, target_amount, current_amount, deadline: deadline || null };
    const url = currentEditId ? `/api/goals/${currentEditId}` : '/api/goals';
    const method = currentEditId ? 'PUT' : 'POST';

    const res = await fetchAuth(url, {
        method: method,
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        closeGoalModal();
        loadGoals();
    } else {
        alert('Failed to save goal');
    }
}

async function deleteGoal(id) {
    if (!confirm('Are you sure you want to remove this financial goal?')) return;
    const res = await fetchAuth(`/api/goals/${id}`, { method: 'DELETE' });
    if (res.ok) {
        loadGoals();
    } else {
        alert('Failed to delete goal');
    }
}

async function loadGoalChart(goals) {
    const container = document.getElementById('goalChart')?.closest('div.card') || document.getElementById('goalChart')?.parentElement?.parentElement;

    if (!goals || goals.length === 0) {
        if (window.myGoalChart) {
            window.myGoalChart.destroy();
            window.myGoalChart = null;
        }
        if (container) container.style.display = 'none';
        return;
    }

    if (container) container.style.display = 'block';

    const ctx = document.getElementById('goalChart');
    if (!ctx) return;

    // Chart the first active goal with a deadline
    const goal = goals.find(g => g.deadline);
    if (!goal) return;

    let start = new Date(goal.created_at || new Date());
    const end = new Date(goal.deadline);
    let now = new Date();

    // Safety: ensure start is not in the future relative to now (common with UTC mismatch)
    if (start > now) start = new Date(now.getTime());

    // Get formatted labels
    const fmt = { month: 'short', day: 'numeric' };
    const startStr = start.toLocaleDateString('default', fmt);
    const nowStr = now.toLocaleDateString('default', fmt);
    const endStr = end.toLocaleDateString('default', fmt);

    if (window.myGoalChart) window.myGoalChart.destroy();

    // Prepare labels and data. Collapse Start/Today if they are the same day.
    let labels, idealData, actualData;
    if (startStr === nowStr) {
        labels = [startStr, endStr];
        idealData = [0, goal.target_amount];
        actualData = [goal.current_amount, null];
    } else {
        labels = [startStr, nowStr, endStr];
        idealData = [0, null, goal.target_amount];
        actualData = [0, goal.current_amount, null];
    }

    window.myGoalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ideal Path',
                    data: idealData,
                    borderColor: 'rgba(255,255,255,0.2)',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0,
                    spanGaps: true
                },
                {
                    label: 'Actual Progress',
                    data: actualData,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    pointRadius: 6,
                    fill: true,
                    tension: 0.1,
                    spanGaps: true
                }
            ]
        },
        options: getCommonChartOptions('line')
    });
}

document.addEventListener('DOMContentLoaded', loadGoals);
