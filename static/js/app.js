/* Lavamaster — helpers de interfaz */

function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.messages li').forEach(el => {
        const cls = el.classList.contains('error') ? 'error'
                  : el.classList.contains('warning') ? 'warning' : 'success';
        showToast(el.textContent, cls);
        el.remove();
    });

    document.querySelectorAll('[data-confirm]').forEach(btn => {
        btn.addEventListener('click', e => {
            if (!confirm(btn.dataset.confirm)) e.preventDefault();
        });
    });
});
