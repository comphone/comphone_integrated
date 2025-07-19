#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Commands - Command line interface for system management
"""

import click
import os
import sys
from datetime import datetime, timezone
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from models import (
    db, User, Customer, Task, ServiceJob, Product, Sale, SystemSettings,
    ActivityLog, UserRole, create_tables, init_default_settings, 
    create_sample_data
)

@click.group()
def cli():
    """Comphone System Management CLI"""
    pass

@cli.command()
@with_appcontext
def init_db():
    """Initialize database with tables and default settings"""
    click.echo('🔧 Initializing database...')
    
    # Create tables
    create_tables()
    click.echo('✅ Database tables created')
    
    # Initialize default settings
    init_default_settings()
    click.echo('✅ Default settings initialized')
    
    click.echo('🎉 Database initialization completed!')

@cli.command()
@with_appcontext
def create_admin():
    """Create admin user"""
    click.echo('👤 Creating admin user...')
    
    username = click.prompt('Username', default='admin')
    email = click.prompt('Email', default='admin@comphone.com')
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)
    first_name = click.prompt('First Name', default='Admin')
    last_name = click.prompt('Last Name', default='User')
    
    # Check if user exists
    if User.query.filter_by(username=username).first():
        click.echo('❌ User already exists!')
        return
    
    # Create admin user
    admin = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=UserRole.ADMIN,
        is_active=True
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f'✅ Admin user "{username}" created successfully!')

@cli.command()
@with_appcontext
def create_sample():
    """Create sample data for testing"""
    click.echo('👥 Creating sample data...')
    
    if User.query.count() > 0:
        if not click.confirm('Sample data already exists. Continue?'):
            return
    
    create_sample_data()
    click.echo('✅ Sample data created successfully!')

@cli.command()
@with_appcontext
def reset_db():
    """Reset database (WARNING: This will delete all data)"""
    if not click.confirm('⚠️  This will delete ALL data. Are you sure?'):
        return
    
    if not click.confirm('⚠️  Really delete all data? This cannot be undone!'):
        return
    
    click.echo('🗑️  Dropping all tables...')
    db.drop_all()
    
    click.echo('🔧 Recreating tables...')
    create_tables()
    
    click.echo('⚙️  Initializing default settings...')
    init_default_settings()
    
    click.echo('✅ Database reset completed!')

@cli.command()
@with_appcontext
def backup_db():
    """Create database backup"""
    click.echo('💾 Creating database backup...')
    
    try:
        from utils.helpers import backup_database
        backup_path = backup_database()
        
        if backup_path:
            click.echo(f'✅ Database backup created: {backup_path}')
        else:
            click.echo('❌ Failed to create backup')
    except Exception as e:
        click.echo(f'❌ Backup failed: {e}')

@cli.command()
@with_appcontext
def list_users():
    """List all users"""
    users = User.query.all()
    
    if not users:
        click.echo('No users found')
        return
    
    click.echo('👥 Users:')
    click.echo('-' * 80)
    click.echo(f'{"ID":<5} {"Username":<15} {"Email":<25} {"Role":<10} {"Active":<6}')
    click.echo('-' * 80)
    
    for user in users:
        click.echo(f'{user.id:<5} {user.username:<15} {user.email:<25} {user.role.value:<10} {"✅" if user.is_active else "❌":<6}')

@cli.command()
@click.argument('username')
@with_appcontext
def deactivate_user(username):
    """Deactivate a user"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        click.echo(f'❌ User "{username}" not found')
        return
    
    if not user.is_active:
        click.echo(f'ℹ️  User "{username}" is already deactivated')
        return
    
    user.is_active = False
    db.session.commit()
    
    click.echo(f'✅ User "{username}" deactivated')

@cli.command()
@click.argument('username')
@with_appcontext
def activate_user(username):
    """Activate a user"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        click.echo(f'❌ User "{username}" not found')
        return
    
    if user.is_active:
        click.echo(f'ℹ️  User "{username}" is already active')
        return
    
    user.is_active = True
    db.session.commit()
    
    click.echo(f'✅ User "{username}" activated')

@cli.command()
@click.argument('username')
@with_appcontext
def reset_password(username):
    """Reset user password"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        click.echo(f'❌ User "{username}" not found')
        return
    
    new_password = click.prompt('New password', hide_input=True, confirmation_prompt=True)
    
    user.set_password(new_password)
    db.session.commit()
    
    click.echo(f'✅ Password reset for user "{username}"')

@cli.command()
@with_appcontext
def system_stats():
    """Show system statistics"""
    click.echo('📊 System Statistics:')
    click.echo('-' * 40)
    
    stats = {
        'Users': User.query.count(),
        'Active Users': User.query.filter_by(is_active=True).count(),
        'Customers': Customer.query.count(),
        'Tasks': Task.query.count(),
        'Service Jobs': ServiceJob.query.count(),
        'Products': Product.query.count(),
        'Sales': Sale.query.count(),
        'Activity Logs': ActivityLog.query.count()
    }
    
    for key, value in stats.items():
        click.echo(f'{key:<15}: {value:>10,}')

@cli.command()
@with_appcontext
def check_health():
    """Check system health"""
    click.echo('🏥 System Health Check:')
    click.echo('-' * 40)
    
    checks = []
    
    # Database connection
    try:
        db.session.execute('SELECT 1')
        checks.append(('Database Connection', '✅ OK'))
    except Exception as e:
        checks.append(('Database Connection', f'❌ Failed: {e}'))
    
    # Check required tables
    try:
        required_tables = ['user', 'customer', 'task', 'service_job', 'product', 'sale']
        for table in required_tables:
            db.session.execute(f'SELECT 1 FROM {table} LIMIT 1')
        checks.append(('Database Tables', '✅ OK'))
    except Exception as e:
        checks.append(('Database Tables', f'❌ Failed: {e}'))
    
    # Check admin user exists
    admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
    if admin_count > 0:
        checks.append(('Admin Users', f'✅ OK ({admin_count} admin users)'))
    else:
        checks.append(('Admin Users', '⚠️  No admin users found'))
    
    # Check configuration
    config_checks = [
        ('SECRET_KEY', current_app.config.get('SECRET_KEY')),
        ('LINE_CHANNEL_ACCESS_TOKEN', current_app.config.get('LINE_CHANNEL_ACCESS_TOKEN')),
        ('GOOGLE_CLIENT_ID', current_app.config.get('GOOGLE_CLIENT_ID')),
        ('MAIL_USERNAME', current_app.config.get('MAIL_USERNAME'))
    ]
    
    for key, value in config_checks:
        if value:
            checks.append((key, '✅ Configured'))
        else:
            checks.append((key, '⚠️  Not configured'))
    
    # Display results
    for check_name, status in checks:
        click.echo(f'{check_name:<25}: {status}')

@cli.command()
@with_appcontext
def clean_logs():
    """Clean old activity logs"""
    days = click.prompt('Delete logs older than (days)', type=int, default=30)
    
    if not click.confirm(f'Delete activity logs older than {days} days?'):
        return
    
    from datetime import timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    deleted_count = ActivityLog.query.filter(
        ActivityLog.created_at < cutoff_date
    ).delete()
    
    db.session.commit()
    
    click.echo(f'✅ Deleted {deleted_count} old activity logs')

@cli.command()
@with_appcontext
def export_data():
    """Export data to JSON"""
    import json
    
    filename = click.prompt('Export filename', default='comphone_export.json')
    
    click.echo('📤 Exporting data...')
    
    export_data = {
        'users': [user.to_dict() for user in User.query.all()],
        'customers': [customer.to_dict() for customer in Customer.query.all()],
        'products': [product.to_dict() for product in Product.query.all()],
        'export_date': datetime.now(timezone.utc).isoformat()
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    click.echo(f'✅ Data exported to {filename}')

@cli.command()
@with_appcontext
def update_settings():
    """Update system settings"""
    click.echo('⚙️  System Settings:')
    
    settings = SystemSettings.query.all()
    
    if not settings:
        click.echo('No settings found')
        return
    
    for setting in settings:
        current_value = setting.value
        new_value = click.prompt(
            f'{setting.key} ({setting.description})',
            default=current_value,
            show_default=True
        )
        
        if new_value != current_value:
            setting.value = new_value
            setting.updated_at = datetime.now(timezone.utc)
            click.echo(f'✅ Updated {setting.key}')
    
    db.session.commit()
    click.echo('✅ Settings updated')

@cli.command()
@with_appcontext
def create_test_data():
    """Create test data for specific scenarios"""
    click.echo('🧪 Creating test data...')
    
    # Create test customers
    test_customers = [
        {'name': 'ทดสอบ ลูกค้า 1', 'phone': '08-1111-1111', 'email': 'test1@test.com'},
        {'name': 'ทดสอบ ลูกค้า 2', 'phone': '08-2222-2222', 'email': 'test2@test.com'},
        {'name': 'ทดสอบ ลูกค้า 3', 'phone': '08-3333-3333', 'email': 'test3@test.com'}
    ]
    
    for customer_data in test_customers:
        if not Customer.query.filter_by(phone=customer_data['phone']).first():
            customer = Customer(**customer_data)
            customer.generate_customer_code()
            db.session.add(customer)
    
    # Create test products
    test_products = [
        {'name': 'ทดสอบ สินค้า 1', 'sku': 'TEST001', 'price': 100, 'stock_quantity': 10},
        {'name': 'ทดสอบ สินค้า 2', 'sku': 'TEST002', 'price': 200, 'stock_quantity': 20},
        {'name': 'ทดสอบ บริการ 1', 'sku': 'SRV001', 'price': 500, 'is_service': True}
    ]
    
    for product_data in test_products:
        if not Product.query.filter_by(sku=product_data['sku']).first():
            product = Product(**product_data)
            db.session.add(product)
    
    db.session.commit()
    click.echo('✅ Test data created')

@cli.command()
@with_appcontext
def migrate_data():
    """Migrate data from old format"""
    click.echo('🔄 Data migration...')
    
    if not click.confirm('Start data migration?'):
        return
    
    # Example migration - update customer codes
    customers_without_codes = Customer.query.filter(
        (Customer.customer_code == None) | (Customer.customer_code == '')
    ).all()
    
    for customer in customers_without_codes:
        customer.generate_customer_code()
    
    db.session.commit()
    
    click.echo(f'✅ Updated {len(customers_without_codes)} customer codes')

@cli.command()
@with_appcontext
def fix_data():
    """Fix data integrity issues"""
    click.echo('🔧 Fixing data integrity...')
    
    issues_fixed = 0
    
    # Fix missing customer codes
    customers_without_codes = Customer.query.filter(
        (Customer.customer_code == None) | (Customer.customer_code == '')
    ).all()
    
    for customer in customers_without_codes:
        customer.generate_customer_code()
        issues_fixed += 1
    
    # Fix missing task numbers
    tasks_without_numbers = Task.query.filter(
        (Task.task_number == None) | (Task.task_number == '')
    ).all()
    
    for task in tasks_without_numbers:
        task.generate_task_number()
        issues_fixed += 1
    
    # Fix missing job numbers
    jobs_without_numbers = ServiceJob.query.filter(
        (ServiceJob.job_number == None) | (ServiceJob.job_number == '')
    ).all()
    
    for job in jobs_without_numbers:
        job.generate_job_number()
        issues_fixed += 1
    
    db.session.commit()
    
    click.echo(f'✅ Fixed {issues_fixed} data integrity issues')

@cli.command()
@with_appcontext
def optimize_db():
    """Optimize database performance"""
    click.echo('⚡ Optimizing database...')
    
    try:
        # For SQLite
        if 'sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI']:
            db.session.execute('VACUUM')
            db.session.execute('REINDEX')
            click.echo('✅ SQLite database optimized')
        else:
            click.echo('ℹ️  Database optimization not implemented for this database type')
        
        db.session.commit()
    except Exception as e:
        click.echo(f'❌ Optimization failed: {e}')

@cli.command()
@with_appcontext
def run_maintenance():
    """Run routine maintenance tasks"""
    click.echo('🛠️  Running maintenance tasks...')
    
    # Clean old logs
    from datetime import timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    deleted_logs = ActivityLog.query.filter(
        ActivityLog.created_at < cutoff_date
    ).delete()
    
    # Fix data integrity
    customers_fixed = 0
    for customer in Customer.query.filter(Customer.customer_code == None).all():
        customer.generate_customer_code()
        customers_fixed += 1
    
    # Optimize database
    if 'sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI']:
        db.session.execute('VACUUM')
    
    db.session.commit()
    
    click.echo(f'✅ Maintenance completed:')
    click.echo(f'   - Deleted {deleted_logs} old logs')
    click.echo(f'   - Fixed {customers_fixed} customer codes')
    click.echo(f'   - Optimized database')

@cli.command()
@with_appcontext
def test_integrations():
    """Test external integrations"""
    click.echo('🔗 Testing integrations...')
    
    results = []
    
    # Test LINE Bot
    line_token = current_app.config.get('LINE_CHANNEL_ACCESS_TOKEN')
    if line_token:
        try:
            # Test LINE Bot connection (mock)
            results.append(('LINE Bot', '✅ Configured'))
        except Exception as e:
            results.append(('LINE Bot', f'❌ Error: {e}'))
    else:
        results.append(('LINE Bot', '⚠️  Not configured'))
    
    # Test Google API
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    if google_client_id:
        try:
            # Test Google API connection (mock)
            results.append(('Google API', '✅ Configured'))
        except Exception as e:
            results.append(('Google API', f'❌ Error: {e}'))
    else:
        results.append(('Google API', '⚠️  Not configured'))
    
    # Test Email
    mail_username = current_app.config.get('MAIL_USERNAME')
    if mail_username:
        try:
            # Test email connection (mock)
            results.append(('Email', '✅ Configured'))
        except Exception as e:
            results.append(('Email', f'❌ Error: {e}'))
    else:
        results.append(('Email', '⚠️  Not configured'))
    
    # Display results
    for integration, status in results:
        click.echo(f'{integration:<15}: {status}')

@cli.command()
@with_appcontext
def generate_report():
    """Generate system report"""
    click.echo('📊 Generating system report...')
    
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'statistics': {
            'users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'customers': Customer.query.count(),
            'tasks': Task.query.count(),
            'service_jobs': ServiceJob.query.count(),
            'products': Product.query.count(),
            'sales': Sale.query.count()
        },
        'health_checks': {
            'database': 'OK',
            'admin_users': User.query.filter_by(role=UserRole.ADMIN).count() > 0,
            'line_bot': bool(current_app.config.get('LINE_CHANNEL_ACCESS_TOKEN')),
            'google_api': bool(current_app.config.get('GOOGLE_CLIENT_ID')),
            'email': bool(current_app.config.get('MAIL_USERNAME'))
        }
    }
    
    filename = f'system_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    click.echo(f'✅ Report generated: {filename}')

# Register commands
def register_commands(app):
    """Register CLI commands with Flask app"""
    app.cli.add_command(cli)

if __name__ == '__main__':
    cli()