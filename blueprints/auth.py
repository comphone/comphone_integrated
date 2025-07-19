from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, db, ActivityLog
import logging

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            remember = bool(request.form.get('remember'))
            
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('auth/login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                # Check if user is active (use different field names)
                is_active = True  # Default to active
                if hasattr(user, 'active'):
                    is_active = user.active
                elif hasattr(user, 'is_active'):
                    is_active = user.is_active
                elif hasattr(user, 'status'):
                    is_active = user.status == 'active'
                
                if not is_active:
                    flash('Your account has been deactivated', 'error')
                    return render_template('auth/login.html')
                
                login_user(user, remember=remember)
                
                # Log successful login (safe method)
                try:
                    if hasattr(ActivityLog, 'log_activity'):
                        ActivityLog.log_activity(
                            user_id=user.id,
                            action='login',
                            description=f'User {username} logged in successfully'
                        )
                    else:
                        # Create activity log manually
                        activity = ActivityLog(
                            user_id=user.id,
                            action='login',
                            description=f'User {username} logged in successfully'
                        )
                        db.session.add(activity)
                        db.session.commit()
                except Exception as log_error:
                    logging.error(f"Error logging activity: {str(log_error)}")
                
                # Update last login (safe method)
                try:
                    if hasattr(user, 'update_last_login'):
                        user.update_last_login()
                    elif hasattr(user, 'last_login'):
                        from datetime import datetime
                        user.last_login = datetime.utcnow()
                        db.session.commit()
                except Exception as update_error:
                    logging.error(f"Error updating last login: {str(update_error)}")
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))
            else:
                # Log failed login attempt (safe method)
                try:
                    if hasattr(ActivityLog, 'log_activity'):
                        ActivityLog.log_activity(
                            action='login_failed',
                            description=f'Failed login attempt for username: {username}'
                        )
                    else:
                        activity = ActivityLog(
                            action='login_failed',
                            description=f'Failed login attempt for username: {username}'
                        )
                        db.session.add(activity)
                        db.session.commit()
                except Exception as log_error:
                    logging.error(f"Error logging failed login: {str(log_error)}")
                
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    try:
        # Log logout activity (safe method)
        try:
            if hasattr(ActivityLog, 'log_activity'):
                ActivityLog.log_activity(
                    user_id=current_user.id,
                    action='logout',
                    description=f'User {current_user.username} logged out'
                )
            else:
                activity = ActivityLog(
                    user_id=current_user.id,
                    action='logout',
                    description=f'User {current_user.username} logged out'
                )
                db.session.add(activity)
                db.session.commit()
        except Exception as log_error:
            logging.error(f"Error logging logout: {str(log_error)}")
        
        logout_user()
        flash('You have been logged out successfully', 'info')
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        flash('An error occurred during logout', 'error')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        # Get recent activities for this user (safe method)
        recent_activities = []
        try:
            recent_activities = ActivityLog.query.filter_by(
                user_id=current_user.id
            ).order_by(ActivityLog.created_at.desc()).limit(10).all()
        except Exception as activity_error:
            logging.error(f"Error getting activities: {str(activity_error)}")
        
        return render_template('auth/profile.html',
                             user=current_user,
                             recent_activities=recent_activities)
    except Exception as e:
        logging.error(f"Profile error: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('main.dashboard'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validation
            if not all([current_password, new_password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('auth/change_password.html')
            
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect', 'error')
                return render_template('auth/change_password.html')
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return render_template('auth/change_password.html')
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('auth/change_password.html')
            
            # Update password
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Log password change (safe method)
            try:
                if hasattr(ActivityLog, 'log_activity'):
                    ActivityLog.log_activity(
                        user_id=current_user.id,
                        action='password_changed',
                        description='User changed their password'
                    )
                else:
                    activity = ActivityLog(
                        user_id=current_user.id,
                        action='password_changed',
                        description='User changed their password'
                    )
                    db.session.add(activity)
                    db.session.commit()
            except Exception as log_error:
                logging.error(f"Error logging password change: {str(log_error)}")
            
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logging.error(f"Change password error: {str(e)}")
            db.session.rollback()
            flash('An error occurred while changing password', 'error')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not first_name or not last_name:
            flash('First name and last name are required', 'error')
            return redirect(url_for('auth.profile'))
        
        if email and '@' not in email:
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('auth.profile'))
        
        # Check if email is already taken by another user
        if email and hasattr(current_user, 'email') and email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email address is already in use', 'error')
                return redirect(url_for('auth.profile'))
        
        # Update user information (safe field assignment)
        if hasattr(current_user, 'first_name'):
            current_user.first_name = first_name
        if hasattr(current_user, 'last_name'):
            current_user.last_name = last_name
        if hasattr(current_user, 'email'):
            current_user.email = email
        if hasattr(current_user, 'phone'):
            current_user.phone = phone
        
        db.session.commit()
        
        # Log profile update (safe method)
        try:
            if hasattr(ActivityLog, 'log_activity'):
                ActivityLog.log_activity(
                    user_id=current_user.id,
                    action='profile_updated',
                    description='User updated their profile information'
                )
            else:
                activity = ActivityLog(
                    user_id=current_user.id,
                    action='profile_updated',
                    description='User updated their profile information'
                )
                db.session.add(activity)
                db.session.commit()
        except Exception as log_error:
            logging.error(f"Error logging profile update: {str(log_error)}")
        
        flash('Profile updated successfully', 'success')
        
    except Exception as e:
        logging.error(f"Update profile error: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating profile', 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (Admin only in production)"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            role = request.form.get('role', 'employee')
            
            # Validation
            if not all([username, email, password, confirm_password, first_name, last_name]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('auth/register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('auth/register.html')
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('auth/register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return render_template('auth/register.html')
            
            # Create new user with safe field assignment
            user_data = {
                'username': username,
                'password_hash': generate_password_hash(password),
                'role': role
            }
            
            # Add optional fields if they exist in the model
            if hasattr(User, 'email'):
                user_data['email'] = email
            if hasattr(User, 'first_name'):
                user_data['first_name'] = first_name
            if hasattr(User, 'last_name'):
                user_data['last_name'] = last_name
            if hasattr(User, 'active'):
                user_data['active'] = True
            elif hasattr(User, 'is_active'):
                user_data['is_active'] = True
            elif hasattr(User, 'status'):
                user_data['status'] = 'active'
            
            user = User(**user_data)
            
            db.session.add(user)
            db.session.commit()
            
            # Log user registration (safe method)
            try:
                if hasattr(ActivityLog, 'log_activity'):
                    ActivityLog.log_activity(
                        action='user_registered',
                        description=f'New user registered: {username}'
                    )
                else:
                    activity = ActivityLog(
                        action='user_registered',
                        description=f'New user registered: {username}'
                    )
                    db.session.add(activity)
                    db.session.commit()
            except Exception as log_error:
                logging.error(f"Error logging registration: {str(log_error)}")
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during registration', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/manage_users')
@login_required
def manage_users():
    """User management page (Admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('auth/manage_users.html', users=users)
    except Exception as e:
        logging.error(f"Manage users error: {str(e)}")
        flash('Error loading users', 'error')
        return redirect(url_for('main.dashboard'))

# API Endpoints
@auth_bp.route('/api/check_session')
@login_required
def check_session():
    """Check if user session is valid"""
    return jsonify({
        'status': 'success',
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'role': current_user.role,
            'full_name': getattr(current_user, 'first_name', current_user.username)
        }
    })

@auth_bp.route('/api/user_info')
@login_required
def user_info():
    """Get current user information"""
    user_dict = {
        'id': current_user.id,
        'username': current_user.username,
        'role': current_user.role
    }
    
    # Add optional fields safely
    for field in ['first_name', 'last_name', 'email', 'phone', 'active', 'is_active', 'status']:
        if hasattr(current_user, field):
            user_dict[field] = getattr(current_user, field)
    
    return jsonify({
        'status': 'success',
        'user': user_dict
    })

# Error handlers for auth blueprint
@auth_bp.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@auth_bp.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403

@auth_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500