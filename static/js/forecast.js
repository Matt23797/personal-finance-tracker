async function loadForecast() {
    try {
        const res = await fetchAuth('/api/forecast');
        const data = await res.json();

        // Update basic metrics
        document.getElementById('current-balance').textContent = data.current_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById('daily-burn').textContent = data.daily_burn.toFixed(2);
        document.getElementById('daily-income').textContent = data.daily_income.toFixed(2);

        // Scenario Analysis Impacts (for 90 days)
        const cut10Impact = (data.daily_burn * 0.1 * 90);
        document.getElementById('cut-10-impact').textContent = `+$${cut10Impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

        const extraIncomeImpact = (500 * (90 / 30));
        document.getElementById('add-income-impact').textContent = `+$${extraIncomeImpact.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

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
            labels: projection.map(p => new Date(p.date).toLocaleDateString('default', { month: 'short', day: 'numeric' })),
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
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 13 },
                    callbacks: {
                        label: function (context) {
                            return ` Balance: $${context.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#aaa',
                        callback: (value) => '$' + value.toLocaleString()
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#aaa',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', loadForecast);
