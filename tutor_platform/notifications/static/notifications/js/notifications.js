// Notification JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Mark all as read functionality
    const markAllReadBtn = document.getElementById('mark-all-read-btn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', markAllNotificationsAsRead);
    }
    
    // Delete read notifications functionality
    const deleteReadBtn = document.getElementById('delete-read-btn');
    if (deleteReadBtn) {
        deleteReadBtn.addEventListener('click', deleteReadNotifications);
    }
    
    // Individual notification actions
    const markReadButtons = document.querySelectorAll('.mark-read-btn');
    markReadButtons.forEach(button => {
        button.addEventListener('click', function() {
            markNotificationAsRead(this.dataset.notificationId);
        });
    });
    
    const markUnreadButtons = document.querySelectorAll('.mark-unread-btn');
    markUnreadButtons.forEach(button => {
        button.addEventListener('click', function() {
            markNotificationAsUnread(this.dataset.notificationId);
        });
    });
    
    const deleteButtons = document.querySelectorAll('.delete-notification-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            deleteNotification(this.dataset.notificationId);
        });
    });
    
    // System notification dismiss buttons
    const dismissButtons = document.querySelectorAll('.dismiss-notification-btn');
    dismissButtons.forEach(button => {
        button.addEventListener('click', function() {
            dismissSystemNotification(this.dataset.notificationId);
        });
    });
    
    // Notification filters
    const filterForm = document.getElementById('notification-filters');
    if (filterForm) {
        filterForm.addEventListener('change', function() {
            filterForm.submit();
        });
    }
    
    // Bulk actions
    const bulkActionForm = document.getElementById('bulk-action-form');
    if (bulkActionForm) {
        const selectAllCheckbox = document.getElementById('select-all-notifications');
        const notificationCheckboxes = document.querySelectorAll('.notification-checkbox');
        
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                notificationCheckboxes.forEach(checkbox => {
                    checkbox.checked = this.checked;
                });
                updateBulkActionButton();
            });
        }
        
        notificationCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateBulkActionButton);
        });
    }
    
    // Auto-refresh notification count
    setInterval(updateNotificationCount, 30000); // Update every 30 seconds
});

function markAllNotificationsAsRead() {
    const btn = document.getElementById('mark-all-read-btn');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Marking as read...';
    btn.disabled = true;
    
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showAlert('Error marking notifications as read', 'danger');
        }
    })
    .catch(error => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        showAlert('Error marking notifications as read', 'danger');
        console.error('Error:', error);
    });
}

function deleteReadNotifications() {
    if (!confirm('Are you sure you want to delete all read notifications?')) {
        return;
    }
    
    const btn = document.getElementById('delete-read-btn');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Deleting...';
    btn.disabled = true;
    
    fetch('/notifications/delete-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showAlert('Error deleting notifications', 'danger');
        }
    })
    .catch(error => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        showAlert('Error deleting notifications', 'danger');
        console.error('Error:', error);
    });
}

function markNotificationAsRead(notificationId) {
    const btn = document.querySelector(`[data-notification-id="${notificationId}"]`);
    const originalClass = btn.className;
    
    btn.className = 'btn btn-sm btn-outline-secondary';
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Marking...';
    btn.disabled = true;
    
    fetch(`/notifications/${notificationId}/mark-read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notificationItem = btn.closest('.notification-item');
            notificationItem.classList.remove('unread');
            notificationItem.classList.add('read');
            
            // Update read status indicator
            const statusBadge = notificationItem.querySelector('.read-status');
            if (statusBadge) {
                statusBadge.innerHTML = '<i class="fas fa-check-circle text-success"></i> Read';
            }
            
            // Reset button
            btn.className = 'btn btn-sm btn-outline-warning mark-unread-btn';
            btn.innerHTML = '<i class="fas fa-envelope me-1"></i> Mark Unread';
            btn.disabled = false;
            
            // Update notification count
            updateNotificationCount();
        } else {
            btn.className = originalClass;
            btn.disabled = false;
            showAlert('Error marking notification as read', 'danger');
        }
    })
    .catch(error => {
        btn.className = originalClass;
        btn.disabled = false;
        showAlert('Error marking notification as read', 'danger');
        console.error('Error:', error);
    });
}

function markNotificationAsUnread(notificationId) {
    const btn = document.querySelector(`[data-notification-id="${notificationId}"]`);
    const originalClass = btn.className;
    
    btn.className = 'btn btn-sm btn-outline-secondary';
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Marking...';
    btn.disabled = true;
    
    fetch(`/notifications/${notificationId}/mark-unread/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notificationItem = btn.closest('.notification-item');
            notificationItem.classList.remove('read');
            notificationItem.classList.add('unread');
            
            // Update read status indicator
            const statusBadge = notificationItem.querySelector('.read-status');
            if (statusBadge) {
                statusBadge.innerHTML = '<i class="fas fa-envelope text-primary"></i> Unread';
            }
            
            // Reset button
            btn.className = 'btn btn-sm btn-outline-success mark-read-btn';
            btn.innerHTML = '<i class="fas fa-check me-1"></i> Mark Read';
            btn.disabled = false;
            
            // Update notification count
            updateNotificationCount();
        } else {
            btn.className = originalClass;
            btn.disabled = false;
            showAlert('Error marking notification as unread', 'danger');
        }
    })
    .catch(error => {
        btn.className = originalClass;
        btn.disabled = false;
        showAlert('Error marking notification as unread', 'danger');
        console.error('Error:', error);
    });
}

function deleteNotification(notificationId) {
    if (!confirm('Are you sure you want to delete this notification?')) {
        return;
    }
    
    const btn = document.querySelector(`[data-notification-id="${notificationId}"]`);
    const originalClass = btn.className;
    
    btn.className = 'btn btn-sm btn-outline-secondary';
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Deleting...';
    btn.disabled = true;
    
    fetch(`/notifications/${notificationId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notificationItem = btn.closest('.notification-item');
            notificationItem.style.transition = 'all 0.3s ease';
            notificationItem.style.opacity = '0';
            notificationItem.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                notificationItem.remove();
                updateNotificationCount();
            }, 300);
        } else {
            btn.className = originalClass;
            btn.disabled = false;
            showAlert('Error deleting notification', 'danger');
        }
    })
    .catch(error => {
        btn.className = originalClass;
        btn.disabled = false;
        showAlert('Error deleting notification', 'danger');
        console.error('Error:', error);
    });
}

function dismissSystemNotification(notificationId) {
    const btn = document.querySelector(`[data-notification-id="${notificationId}"]`);
    const originalClass = btn.className;
    
    btn.className = 'btn btn-sm btn-outline-secondary';
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Dismissing...';
    btn.disabled = true;
    
    fetch('/notifications/system/dismiss/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            notification_id: notificationId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notificationItem = btn.closest('.system-notification');
            notificationItem.style.transition = 'all 0.3s ease';
            notificationItem.style.opacity = '0';
            notificationItem.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                notificationItem.remove();
            }, 300);
        } else {
            btn.className = originalClass;
            btn.disabled = false;
            showAlert('Error dismissing notification', 'danger');
        }
    })
    .catch(error => {
        btn.className = originalClass;
        btn.disabled = false;
        showAlert('Error dismissing notification', 'danger');
        console.error('Error:', error);
    });
}

function updateNotificationCount() {
    fetch('/notifications/count/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // Update notification count in navigation
        const countElements = document.querySelectorAll('.notification-count');
        countElements.forEach(element => {
            if (data.count > 0) {
                element.textContent = data.count;
                element.style.display = 'inline-block';
            } else {
                element.style.display = 'none';
            }
        });
    })
    .catch(error => {
        console.error('Error updating notification count:', error);
    });
}

function updateBulkActionButton() {
    const bulkActionBtn = document.getElementById('bulk-action-btn');
    const checkedBoxes = document.querySelectorAll('.notification-checkbox:checked');
    
    if (bulkActionBtn) {
        if (checkedBoxes.length > 0) {
            bulkActionBtn.disabled = false;
        } else {
            bulkActionBtn.disabled = true;
        }
    }
}

function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to top of content
    const content = document.querySelector('.col-md-9');
    if (content) {
        content.insertBefore(alertDiv, content.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    }
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