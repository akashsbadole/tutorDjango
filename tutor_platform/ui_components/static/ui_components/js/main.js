/**
 * Django Tutor Platform - Main JavaScript
 * Handles UI interactions, HTMX configuration, and Alpine.js components
 */

// ===================================
// HTMX Configuration
// ===================================
htmx.config.globalViewTransitions = true;
htmx.config.useTemplateFragments = true;
htmx.config.defaultSwapStyle = 'innerHTML';
htmx.config.defaultSwapDelay = 0;
htmx.config.defaultSettleDelay = 0;

// ===================================
// Alpine.js Data and Components
// ===================================
document.addEventListener('alpine:init', () => {
    // Theme management component
    Alpine.data('themeManager', () => ({
        theme: localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
        
        init() {
            // Apply theme on initialization
            this.applyTheme();
            
            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.theme = e.matches ? 'dark' : 'light';
                    this.applyTheme();
                }
            });
        },
        
        toggle() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark';
            this.applyTheme();
            localStorage.setItem('theme', this.theme);
        },
        
        applyTheme() {
            document.documentElement.classList.toggle('dark', this.theme === 'dark');
            document.documentElement.setAttribute('data-theme', this.theme);
        }
    }));
    
    // Search component
    Alpine.data('search', () => ({
        query: '',
        results: [],
        loading: false,
        open: false,
        
        search() {
            if (this.query.length < 2) {
                this.results = [];
                this.open = false;
                return;
            }
            
            this.loading = true;
            this.open = true;
            
            // This would typically make an AJAX call
            // For now, we'll just simulate it
            setTimeout(() => {
                this.results = [
                    { title: 'Math Tutoring', type: 'requirement', url: '#' },
                    { title: 'John Doe', type: 'tutor', url: '#' },
                ];
                this.loading = false;
            }, 300);
        },
        
        close() {
            setTimeout(() => {
                this.open = false;
            }, 200);
        }
    }));
    
    // Modal component
    Alpine.data('modal', (initialOpen = false) => ({
        open: initialOpen,
        
        show() {
            this.open = true;
            document.body.style.overflow = 'hidden';
        },
        
        hide() {
            this.open = false;
            document.body.style.overflow = '';
        },
        
        toggle() {
            if (this.open) {
                this.hide();
            } else {
                this.show();
            }
        },
        
        onEscape(event) {
            if (event.key === 'Escape' && this.open) {
                this.hide();
            }
        }
    }));
    
    // Dropdown component
    Alpine.data('dropdown', (initialOpen = false) => ({
        open: initialOpen,
        
        toggle() {
            this.open = !this.open;
        },
        
        close() {
            this.open = false;
        }
    }));
    
    // Toast notification component
    Alpine.store('toast', {
        items: [],
        
        show(message, type = 'info', duration = 5000) {
            const id = Date.now();
            this.items.push({ id, message, type, duration });
            
            if (duration > 0) {
                setTimeout(() => {
                    this.remove(id);
                }, duration);
            }
            
            return id;
        },
        
        remove(id) {
            this.items = this.items.filter(item => item.id !== id);
        },
        
        success(message, duration) {
            return this.show(message, 'success', duration);
        },
        
        error(message, duration) {
            return this.show(message, 'danger', duration);
        },
        
        warning(message, duration) {
            return this.show(message, 'warning', duration);
        },
        
        info(message, duration) {
            return this.show(message, 'info', duration);
        }
    });
});

// ===================================
// HTMX Event Listeners
// ===================================
document.addEventListener('htmx:afterRequest', function(evt) {
    // Re-initialize Bootstrap components after HTMX updates
    if (typeof bootstrap !== 'undefined') {
        // Tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
        
        // Dropdowns
        const dropdownTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="dropdown"]'));
        dropdownTriggerList.map(function (dropdownTriggerEl) {
            return new bootstrap.Dropdown(dropdownTriggerEl);
        });
    }
    
    // Re-initialize Alpine.js components
    if (window.Alpine && window.Alpine.initTree) {
        window.Alpine.initTree(evt.detail.target);
    }
});

document.addEventListener('htmx:beforeRequest', function(evt) {
    // Show loading state
    const target = evt.detail.target;
    if (target) {
        target.classList.add('htmx-loading');
    }
});

document.addEventListener('htmx:afterRequest', function(evt) {
    // Hide loading state
    const target = evt.detail.target;
    if (target) {
        target.classList.remove('htmx-loading');
    }
});

// ===================================
// Utility Functions
// ===================================
window.UI = {
    // Show a toast notification
    showToast(message, type = 'info', duration = 5000) {
        if (window.Alpine && window.Alpine.store) {
            return window.Alpine.store('toast').show(message, type, duration);
        }
        
        // Fallback for when Alpine is not available
        console.log(`Toast (${type}): ${message}`);
    },
    
    // Show a confirmation dialog
    confirm(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // Format date
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        
        return new Date(date).toLocaleDateString(undefined, { ...defaultOptions, ...options });
    },
    
    // Format time
    formatTime(date, options = {}) {
        const defaultOptions = {
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return new Date(date).toLocaleTimeString(undefined, { ...defaultOptions, ...options });
    },
    
    // Format currency
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },
    
    // Debounce function
    debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },
    
    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Copy to clipboard
    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy: ', err);
                this.showToast('Failed to copy to clipboard', 'error');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showToast('Copied to clipboard!', 'success');
            } catch (err) {
                console.error('Failed to copy: ', err);
                this.showToast('Failed to copy to clipboard', 'error');
            }
            
            document.body.removeChild(textArea);
        }
    },
    
    // Scroll to element
    scrollToElement(element, offset = 0) {
        const target = typeof element === 'string' ? document.querySelector(element) : element;
        if (target) {
            window.scrollTo({
                top: target.offsetTop - offset,
                behavior: 'smooth'
            });
        }
    },
    
    // Get CSRF token
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
};

// ===================================
// Form Enhancements
// ===================================
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            if (typeof bootstrap !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.display = 'none';
            }
        });
    }, 5000);
    
    // Form validation feedback
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea[data-auto-resize]');
    textareas.forEach(textarea => {
        function resize() {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
        
        textarea.addEventListener('input', resize);
        resize(); // Initial resize
    });
    
    // Character counter for text inputs
    const charCounters = document.querySelectorAll('[data-char-counter]');
    charCounters.forEach(input => {
        const counterId = input.getAttribute('data-char-counter');
        const counter = document.getElementById(counterId);
        const maxLength = input.getAttribute('maxlength') || input.getAttribute('data-max-length');
        
        function updateCounter() {
            const current = input.value.length;
            const remaining = maxLength - current;
            
            if (counter) {
                counter.textContent = `${current}/${maxLength}`;
                
                if (remaining < 0) {
                    counter.classList.add('text-danger');
                } else if (remaining < 20) {
                    counter.classList.add('text-warning');
                    counter.classList.remove('text-danger');
                } else {
                    counter.classList.remove('text-warning', 'text-danger');
                }
            }
        }
        
        input.addEventListener('input', updateCounter);
        updateCounter(); // Initial update
    });
    
    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    fileInputs.forEach(input => {
        const previewId = input.getAttribute('data-preview');
        const preview = document.getElementById(previewId);
        
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    if (preview) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    });
});

// ===================================
// Keyboard Shortcuts
// ===================================
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals and dropdowns
    if (e.key === 'Escape') {
        // Close modals
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            if (typeof bootstrap !== 'undefined') {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
        });
        
        // Close dropdowns
        const dropdowns = document.querySelectorAll('.dropdown-menu.show');
        dropdowns.forEach(dropdown => {
            if (typeof bootstrap !== 'undefined') {
                const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
                if (bsDropdown) bsDropdown.hide();
            }
        });
    }
});

// ===================================
// Service Worker Registration (for PWA)
// ===================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// ===================================
// Error Handling
// ===================================
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // You could send this error to a logging service here
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    // You could send this error to a logging service here
});