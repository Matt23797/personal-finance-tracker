async function loadForecast() {
    try {
        const res = await fetchAuth('/api/forecast');
        const data = await res.json();

        // Update basic metrics
        document.getElementById('current-balance').textContent = formatCurrency(data.current_balance).slice(1);
        document.getElementById('daily-burn').textContent = formatCurrency(data.daily_burn).slice(1);
        document.getElementById('daily-income').textContent = formatCurrency(data.daily_income).slice(1);

        // Scenario Analysis Impacts (for 90 days)
        const cut10Impact = (data.daily_burn * 0.1 * 90);
        document.getElementById('cut-10-impact').textContent = `+${formatCurrency(cut10Impact).replace('.00', '')}`;

        const extraIncomeImpact = (500 * (90 / 30));
        document.getElementById('add-income-impact').textContent = `+${formatCurrency(extraIncomeImpact).replace('.00', '')}`;

        renderChart(data.projection);
    } catch (error) {
        console.error('Error loading forecast:', error);
    }
}

function renderChart(projection) {
    const ctx = document.getElementById('forecastChart').getContext('2d');

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 217, 255, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 217, 255, 0)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: projection.map(p => formatDate(p.date)),
            datasets: [{
                label: 'Projected Balance',
                data: projection.map(p => p.balance),
                borderColor: '#00d9ff',
                borderWidth: 3,
                pointRadius: 0,
                pointHoverRadius: 6,
                fill: true,
                backgroundColor: gradient,
                tension: 0.4
            }]
        },
        options: getCommonChartOptions('line')
    });
}

document.addEventListener('DOMContentLoaded', loadForecast);
