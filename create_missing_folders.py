#!/usr/bin/env python3
"""
Script to create missing folders and files for Comphone Integrated System
"""

import os

def create_folders_and_files():
    """Create all necessary folders and basic files"""
    
    # Define folder structure
    folders = [
        'templates/auth',
        'templates/main', 
        'templates/pos',
        'templates/service_jobs',
        'templates/tasks',
        'templates/customers',
        'templates/admin',
        'templates/errors',
        'static/css',
        'static/js', 
        'static/images',
        'static/uploads',
        'uploads/attachments',
        'uploads/temp',
        'instance',
        'logs',
        'credentials',
        'backups'
    ]
    
    # Create folders
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Created folder: {folder}")
        
        # Create .gitkeep for empty folders (except sensitive ones)
        if folder not in ['credentials', 'logs', 'instance']:
            gitkeep_path = os.path.join(folder, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, 'w') as f:
                    f.write('# Keep this folder in git\n')
    
    # Create basic error templates
    error_templates = {
        'templates/errors/404.html': '''{% extends "base.html" %}
{% block title %}Page Not Found{% endblock %}
{% block content %}
<div class="container text-center">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="error-template">
                <h1>404</h1>
                <h2>Page Not Found</h2>
                <div class="error-details">
                    Sorry, the page you are looking for does not exist.
                </div>
                <div class="error-actions">
                    <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">
                        <i class="fas fa-home"></i> Go to Dashboard
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',
        
        'templates/errors/500.html': '''{% extends "base.html" %}
{% block title %}Internal Server Error{% endblock %}
{% block content %}
<div class="container text-center">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="error-template">
                <h1>500</h1>
                <h2>Internal Server Error</h2>
                <div class="error-details">
                    Something went wrong on our end.
                </div>
                <div class="error-actions">
                    <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">
                        <i class="fas fa-home"></i> Go to Dashboard
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',
        
        'templates/errors/403.html': '''{% extends "base.html" %}
{% block title %}Access Forbidden{% endblock %}
{% block content %}
<div class="container text-center">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="error-template">
                <h1>403</h1>
                <h2>Access Forbidden</h2>
                <div class="error-details">
                    You don't have permission to access this resource.
                </div>
                <div class="error-actions">
                    <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">
                        <i class="fas fa-home"></i> Go to Dashboard
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
    }
    
    # Create error template files
    for file_path, content in error_templates.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Created file: {file_path}")
    
    # Create .env.example file
    env_example = '''# Comphone Integrated System Configuration

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///comphone_dev.db

# Security
SECURITY_PASSWORD_SALT=your-password-salt-here

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Google API Configuration (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LINE Bot Configuration (Optional)
LINE_CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
LINE_CHANNEL_SECRET=your-line-channel-secret

# Redis Configuration (for production rate limiting)
REDIS_URL=redis://localhost:6379/0

# Upload Configuration
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads

# Logging
LOG_LEVEL=INFO
'''
    
    if not os.path.exists('.env.example'):
        with open('.env.example', 'w') as f:
            f.write(env_example)
        print("✅ Created .env.example file")
    
    # Create basic CSS file
    basic_css = '''/* Comphone Integrated System Custom Styles */

.dashboard-card {
    transition: transform 0.2s ease-in-out;
}

.dashboard-card:hover {
    transform: translateY(-2px);
}

.stat-icon {
    font-size: 2rem;
    opacity: 0.8;
}

.chart-container {
    position: relative;
    height: 300px;
}

.quick-action-btn {
    border-radius: 15px;
    padding: 10px 20px;
    margin: 5px;
}

.timeline-item {
    border-left: 2px solid #007bff;
    padding-left: 15px;
    margin-bottom: 15px;
}

.error-template {
    padding: 40px 15px;
}

.error-template h1 {
    font-size: 100px;
    color: #007bff;
    font-weight: bold;
    margin-bottom: 20px;
}

.error-details {
    margin: 20px 0;
    color: #666;
}

.error-actions {
    margin-top: 30px;
}

/* Custom animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .quick-action-btn {
        margin: 2px 0;
    }
    
    .stat-icon {
        font-size: 1.5rem;
    }
}
'''
    
    css_path = 'static/css/custom.css'
    if not os.path.exists(css_path):
        with open(css_path, 'w') as f:
            f.write(basic_css)
        print(f"✅ Created {css_path}")
    
    # Create basic JavaScript file
    basic_js = '''// Comphone Integrated System Custom JavaScript

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
'''
    
    js_path = 'static/js/custom.js'
    if not os.path.exists(js_path):
        with open(js_path, 'w') as f:
            f.write(basic_js)
        print(f"✅ Created {js_path}")
    
    print("\n🎉 All folders and basic files created successfully!")
    print("\n📋 Next steps:")
    print("1. Copy the .env.example to .env and configure your settings")
    print("2. Replace blueprints/auth.py with the updated version")
    print("3. Create templates/main/dashboard.html with the dashboard template")
    print("4. Create auth templates (login.html, profile.html, change_password.html)")
    print("5. Run: python app.py")

if __name__ == "__main__":
    create_folders_and_files()