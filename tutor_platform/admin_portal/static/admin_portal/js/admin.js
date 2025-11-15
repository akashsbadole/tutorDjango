/**
 * Django Tutor Platform Admin Portal JavaScript
 */

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Utility functions
function showLoadingSpinner(element) {
    element.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
}

function hideLoadingSpinner(element, originalContent) {
    element.innerHTML = originalContent;
}

function confirmAction(message) {
    return confirm(message);
}

function showNotification(message, type = 'info') {
    var alertClass = 'alert-' + type;
    var alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    var container = document.querySelector('.container-fluid');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
    }
}

// AJAX helper functions
function makeAjaxRequest(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: data ? JSON.stringify(data) : null
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Bulk actions
function selectAllCheckboxes() {
    var checkboxes = document.querySelectorAll('input[name="selected_items"]');
    var selectAll = document.getElementById('select_all');
    
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = selectAll.checked;
    });
    
    updateBulkActions();
}

function updateBulkActions() {
    var checkboxes = document.querySelectorAll('input[name="selected_items"]:checked');
    var bulkActions = document.getElementById('bulk_actions');
    
    if (checkboxes.length > 0) {
        bulkActions.style.display = 'block';
    } else {
        bulkActions.style.display = 'none';
    }
}

function performBulkAction(action) {
    var checkboxes = document.querySelectorAll('input[name="selected_items"]:checked');
    var selectedIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedIds.length === 0) {
        showNotification('Please select at least one item', 'warning');
        return;
    }
    
    if (!confirmAction(`Are you sure you want to ${action} ${selectedIds.length} item(s)?`)) {
        return;
    }
    
    var data = {
        'action': action,
        'user_ids': selectedIds
    };
    
    makeAjaxRequest('/admin-panel/users/bulk-action/', 'POST', data)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred while performing the action', 'danger');
        });
}

// Chart utilities
function updateChart(chart, data) {
    chart.data.labels = data.labels;
    chart.data.datasets[0].data = data.values;
    chart.update();
}

function resizeCharts() {
    var charts = document.querySelectorAll('canvas');
    charts.forEach(function(chart) {
        chart.style.height = 'auto';
    });
}

// Table utilities
function sortTable(table, column, direction = 'asc') {
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    var columnIndex = Array.from(table.querySelectorAll('th')).findIndex(th => th.dataset.column === column);
    
    rows.sort(function(a, b) {
        var aValue = a.children[columnIndex].textContent.trim();
        var bValue = b.children[columnIndex].textContent.trim();
        
        if (direction === 'asc') {
            return aValue.localeCompare(bValue);
        } else {
            return bValue.localeCompare(aValue);
        }
    });
    
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
}

function filterTable(table, searchTerm) {
    var tbody = table.querySelector('tbody');
    var rows = tbody.querySelectorAll('tr');
    
    rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        if (text.includes(searchTerm.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Export utilities
function exportData(format, filters) {
    var data = {
        'format': format,
        'filters': filters
    };
    
    makeAjaxRequest('/admin-panel/export/', 'POST', data)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Download the file
                window.location.href = data.download_url;
            } else {
                showNotification(data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred while exporting data', 'danger');
        });
}

// System utilities
function runSystemCleanup() {
    if (!confirmAction('Are you sure you want to run system cleanup? This action cannot be undone.')) {
        return;
    }
    
    showLoadingSpinner(document.getElementById('cleanup_button'));
    
    makeAjaxRequest('/admin-panel/api/system-cleanup/', 'POST')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('System cleanup completed successfully', 'success');
            } else {
                showNotification(data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred during system cleanup', 'danger');
        })
        .finally(() => {
            hideLoadingSpinner(document.getElementById('cleanup_button'), 'Run System Cleanup');
        });
}

// Date utilities
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function getRelativeTime(dateString) {
    var date = new Date(dateString);
    var now = new Date();
    var diff = now - date;
    
    var seconds = Math.floor(diff / 1000);
    var minutes = Math.floor(seconds / 60);
    var hours = Math.floor(minutes / 60);
    var days = Math.floor(hours / 24);
    
    if (days > 0) {
        return days + ' days ago';
    } else if (hours > 0) {
        return hours + ' hours ago';
    } else if (minutes > 0) {
        return minutes + ' minutes ago';
    } else {
        return 'Just now';
    }
}

// Form utilities
function validateForm(form) {
    var inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    var isValid = true;
    
    inputs.forEach(function(input) {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

function clearForm(form) {
    form.reset();
    var inputs = form.querySelectorAll('.is-invalid');
    inputs.forEach(function(input) {
        input.classList.remove('is-invalid');
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        var saveButton = document.querySelector('button[type="submit"]');
        if (saveButton) {
            saveButton.click();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        var modals = document.querySelectorAll('.modal.show');
        modals.forEach(function(modal) {
            var bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Responsive utilities
function handleResize() {
    var width = window.innerWidth;
    var isMobile = width < 768;
    
    // Toggle mobile-specific elements
    var mobileElements = document.querySelectorAll('.mobile-only');
    var desktopElements = document.querySelectorAll('.desktop-only');
    
    mobileElements.forEach(function(element) {
        element.style.display = isMobile ? '' : 'none';
    });
    
    desktopElements.forEach(function(element) {
        element.style.display = isMobile ? 'none' : '';
    });
    
    // Resize charts
    resizeCharts();
}

window.addEventListener('resize', handleResize);

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    handleResize();
    
    // Initialize date pickers
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        input.flatpickr = flatpickr(input, {
            dateFormat: 'Y-m-d',
            allowInput: true
        });
    });
    
    // Initialize select2 for enhanced selects
    var enhancedSelects = document.querySelectorAll('select.enhanced');
    enhancedSelects.forEach(function(select) {
        jQuery(select).select2({
            theme: 'bootstrap4',
            width: '100%'
        });
    });
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showNotification('An unexpected error occurred. Please try again.', 'danger');
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showNotification('An unexpected error occurred. Please try again.', 'danger');
});