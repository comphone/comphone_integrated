// Comphone Integrated System Custom JavaScript

// Initialize tooltips and popovers
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
    
    // Auto-hide alerts
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
});

// Global utility functions
function showAlert(message, type = 'info', duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, duration);
    }
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// API helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'API call failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showAlert('Error: ' + error.message, 'danger');
        throw error;
    }
}

// Form validation helpers
function validateForm(formId, rules = {}) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const formData = new FormData(form);
    
    for (const [field, rule] of Object.entries(rules)) {
        const value = formData.get(field);
        const element = form.querySelector(`[name="${field}"]`);
        
        if (rule.required && (!value || value.trim() === '')) {
            showFieldError(element, 'This field is required');
            isValid = false;
        } else if (value && rule.pattern && !rule.pattern.test(value)) {
            showFieldError(element, rule.message || 'Invalid format');
            isValid = false;
        } else {
            clearFieldError(element);
        }
    }
    
    return isValid;
}

function showFieldError(element, message) {
    element.classList.add('is-invalid');
    
    let feedback = element.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        element.parentNode.appendChild(feedback);
    }
    feedback.textContent = message;
}

function clearFieldError(element) {
    element.classList.remove('is-invalid');
    const feedback = element.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}
