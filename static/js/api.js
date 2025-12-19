const API_BASE = '/api';
const token = localStorage.getItem('token');

// Global Auth Check
if (!token && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
    window.location.href = '/login';
}

// Helper fetch wrapper
async function fetchAuth(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${token}`;

    if (!(options.body instanceof FormData)) {
        options.headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url.startsWith('/') ? url : API_BASE + url, options);

    if (res.status === 401) {
        // Token expired
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
    return res;
}

document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('token');
            window.location.href = '/login';
        });
    }
});
