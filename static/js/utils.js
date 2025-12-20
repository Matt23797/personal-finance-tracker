/**
 * Common Frontend Utilities
 */

// Formatting
const formatCurrency = (amount) => {
    return '$' + parseFloat(amount).toFixed(2);
};

const formatDate = (dateStr) => {
    if (!dateStr) return 'No date';
    return new Date(dateStr).toLocaleDateString('default', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
};

// Modal Helper
const setupModal = (modalId) => {
    const el = document.getElementById(modalId);
    if (!el) return null;

    return {
        open: () => el.classList.add('active'),
        close: () => el.classList.remove('active'),
        toggle: () => el.classList.toggle('active'),
        isActive: () => el.classList.contains('active')
    };
};

// Chart UI Defaults
const getCommonChartOptions = (chartType = 'line', title) => {
    const isRadial = ['doughnut', 'pie', 'polarArea'].includes(chartType);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#fff',
                    font: { family: 'Inter', size: 12 }
                }
            },
            title: {
                display: !!title,
                text: title,
                color: '#fff'
            },
            tooltip: {
                backgroundColor: '#1a1a2e',
                titleColor: '#fff',
                bodyColor: '#aaa',
                borderColor: 'rgba(255,255,255,0.1)',
                borderWidth: 1
            }
        }
    };

    if (!isRadial) {
        options.scales = {
            x: {
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: { color: '#aaa' }
            },
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: { color: '#aaa' }
            }
        };
    }

    return options;
};
