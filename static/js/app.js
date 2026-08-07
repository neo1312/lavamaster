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

function openModal(id) {
    const el = document.querySelector(id);
    if (!el) return;
    el.classList.remove('hidden');
    el.setAttribute('aria-hidden', 'false');
    const firstInput = el.querySelector('input[name="name"], input[type="text"]');
    if (firstInput) firstInput.focus();
}

function closeModal(el) {
    el.classList.add('hidden');
    el.setAttribute('aria-hidden', 'true');
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

    document.querySelectorAll('[data-modal-open]').forEach(btn => {
        btn.addEventListener('click', () => openModal(btn.dataset.modalOpen));
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', () => closeModal(overlay));
        });
        overlay.addEventListener('click', e => {
            if (e.target === overlay) closeModal(overlay);
        });
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay:not(.hidden)')
                .forEach(closeModal);
        }
    });
});
