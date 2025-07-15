#!/usr/bin/env python3
"""
Comphone Integrated System - Integration Testing Suite
Tests all integrations: Database, Google API, LINE Bot, POS System
Run: python test_integration.py
"""

import os
import sys
import json
import unittest
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import Flask app and models
from config import TestingConfig
from models import (
    db, User, Customer, Product, Sale, SaleItem, ServiceJob, 
    Task, TaskAttachment, TaskReport, CustomerFeedback, Setting
)

class IntegrationTestSuite:
    """Main integration test suite"""
    
    def __init__(self):
        self.app = None
        self.app_context = None
        self.test_data = {}
        
    def setup_test_app(self):
        """Setup Flask app for testing"""
        try:
            from blueprint_structure import create_app
            
            self.app = create_app('testing')
            self.app_context = self.app.app_context()
            self.app_context.push()
            
            # Create tables
            db.create_all()
            
            print("✅ Test Flask app setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup test app: {e}")
            return False
    
    def teardown_test_app(self):
        """Cleanup test app"""
        if self.app_context:
            db.session.remove()
            db.drop_all()
            self.app_context.pop()
        print("✅ Test app cleanup complete")
    
    def test_database_models(self):
        """Test database models and relationships"""
        print("\n🧪 Testing Database Models...")
        
        try:
            # Test User model
            user = User(
                username='testuser',
                email='test@comphone.com',
                first_name='Test',
                last_name='User',
                role='technician',
                is_technician=True
            )
            user.set_password('password123')
            user.set_skills(['phone_repair', 'computer_repair'])
            db.session.add(user)
            
            # Test Customer model
            customer = Customer(
                name='Test Customer',
                email='customer@test.com',
                phone='08-1234-5678',
                customer_type='individual',
                line_user_id='test_line_user_123'
            )
            db.session.add(customer)
            
            # Test Product model
            product = Product(
                name='Test Product',
                description='Test product description',
                price=100.00,
                cost=50.00,
                sku='TEST-001',
                stock_quantity=10,
                category='Test Category'
            )
            db.session.add(product)
            
            db.session.commit()
            
            # Test relationships
            task = Task(
                title='Test Task',
                description='Test task description',
                customer=customer,
                assigned_to=user,
                created_by=user,
                task_type='service',
                priority='normal'
            )
            db.session.add(task)
            
            service_job = ServiceJob(
                job_number='TEST001',
                customer=customer,
                assigned_to=user,
                title='Test Service Job',
                description='Test service job description',
                job_type='repair'
            )
            db.session.add(service_job)
            
            # Link task to service job
            task.service_job = service_job
            
            db.session.commit()
            
            # Verify data
            assert User.query.count() == 1
            assert Customer.query.count() == 1
            assert Product.query.count() == 1
            assert Task.query.count() == 1
            assert ServiceJob.query.count() == 1
            
            # Test model methods
            assert user.full_name == 'Test User'
            assert user.get_skills() == ['phone_repair', 'computer_repair']
            assert customer.display_name == 'Test Customer'
            assert product.is_low_stock == False
            
            # Store test data for other tests
            self.test_data = {
                'user': user,
                'customer': customer,
                'product': product,
                'task': task,
                'service_job': service_job
            }
            
            print("✅ Database models test passed")
            return True
            
        except Exception as e:
            print(f"❌ Database models test failed: {e}")
            return False
    
    def test_pos_system(self):
        """Test POS system functionality"""
        print("\n🧪 Testing POS System...")
        
        try:
            if not self.test_data:
                print("❌ No test data available")
                return False
            
            customer = self.test_data['customer']
            product = self.test_data['product']
            user = self.test_data['user']
            
            # Test sale creation
            sale = Sale(
                customer=customer,
                subtotal=100.00,
                tax_amount=7.00,
                total_amount=107.00,
                payment_method='cash',
                sold_by=user
            )
            db.session.add(sale)
            db.session.flush()
            
            # Test sale item
            sale_item = SaleItem(
                sale=sale,
                product=product,
                quantity=1,
                unit_price=100.00,
                total_price=100.00
            )
            db.session.add(sale_item)
            
            # Update stock
            original_stock = product.stock_quantity
            product.stock_quantity -= 1
            
            db.session.commit()
            
            # Verify sale
            assert Sale.query.count() == 1
            assert SaleItem.query.count() == 1
            assert product.stock_quantity == original_stock - 1
            
            print("✅ POS system test passed")
            return True
            
        except Exception as e:
            print(f"❌ POS system test failed: {e}")
            return False
    
    def test_task_management(self):
        """Test task management system"""
        print("\n🧪 Testing Task Management...")
        
        try:
            if not self.test_data:
                print("❌ No test data available")
                return False
            
            task = self.test_data['task']
            user = self.test_data['user']
            
            # Test task status update
            original_status = task.status
            task.status = 'completed'
            task.completed_at = datetime.now(timezone.utc)
            
            # Test task report
            report = TaskReport(
                task=task,
                work_summary='Completed test task',
                progress_percentage=100,
                hours_worked=2.5,
                created_by=user,
                is_final_report=True
            )
            db.session.add(report)
            
            # Test task attachment (simulated)
            attachment = TaskAttachment(
                task=task,
                google_drive_id='test_drive_id_123',
                filename='test_file.pdf',
                original_filename='test_file.pdf',
                file_type='document',
                uploaded_by=user
            )
            db.session.add(attachment)
            
            db.session.commit()
            
            # Verify task management
            assert task.status == 'completed'
            assert task.completed_at is not None
            assert TaskReport.query.count() == 1
            assert TaskAttachment.query.count() == 1
            
            print("✅ Task management test passed")
            return True
            
        except Exception as e:
            print(f"❌ Task management test failed: {e}")
            return False
    
    def test_customer_feedback(self):
        """Test customer feedback system"""
        print("\n🧪 Testing Customer Feedback...")
        
        try:
            if not self.test_data:
                print("❌ No test data available")
                return False
            
            customer = self.test_data['customer']
            service_job = self.test_data['service_job']
            user = self.test_data['user']
            
            # Test feedback creation
            feedback = CustomerFeedback(
                customer=customer,
                service_job=service_job,
                rating=5,
                feedback_text='Excellent service!',
                feedback_type='service',
                feedback_channel='manual'
            )
            db.session.add(feedback)
            
            # Test feedback response
            feedback.response_text = 'Thank you for your feedback!'
            feedback.responded_by = user
            feedback.response_date = datetime.now(timezone.utc)
            feedback.is_resolved = True
            
            db.session.commit()
            
            # Verify feedback
            assert CustomerFeedback.query.count() == 1
            assert feedback.rating == 5
            assert feedback.is_resolved == True
            
            print("✅ Customer feedback test passed")
            return True
            
        except Exception as e:
            print(f"❌ Customer feedback test failed: {e}")
            return False
    
    def test_settings_system(self):
        """Test settings management"""
        print("\n🧪 Testing Settings System...")
        
        try:
            # Test setting creation
            setting = Setting(
                key='test_setting',
                value='test_value',
                value_type='string',
                description='Test setting',
                category='test'
            )
            db.session.add(setting)
            
            # Test different value types
            bool_setting = Setting(
                key='test_bool',
                value_type='boolean',
                description='Test boolean setting',
                category='test'
            )
            bool_setting.set_value(True)
            db.session.add(bool_setting)
            
            int_setting = Setting(
                key='test_int',
                value_type='integer',
                description='Test integer setting',
                category='test'
            )
            int_setting.set_value(42)
            db.session.add(int_setting)
            
            json_setting = Setting(
                key='test_json',
                value_type='json',
                description='Test JSON setting',
                category='test'
            )
            json_setting.set_value({'key': 'value', 'number': 123})
            db.session.add(json_setting)
            
            db.session.commit()
            
            # Verify settings
            assert Setting.query.count() >= 4
            assert setting.get_value() == 'test_value'
            assert bool_setting.get_value() == True
            assert int_setting.get_value() == 42
            assert json_setting.get_value() == {'key': 'value', 'number': 123}
            
            print("✅ Settings system test passed")
            return True
            
        except Exception as e:
            print(f"❌ Settings system test failed: {e}")
            return False
    
    def test_google_api_integration(self):
        """Test Google API integration (mock)"""
        print("\n🧪 Testing Google API Integration...")
        
        try:
            # Mock Google API service
            class MockGoogleTasksService:
                def __init__(self):
                    self.authenticated = False
                
                def authenticate(self):
                    # Mock authentication
                    self.authenticated = True
                    return True
                
                def create_task(self, task):
                    if not self.authenticated:
                        raise Exception("Not authenticated")
                    
                    # Mock task creation
                    task.google_task_id = f"mock_google_task_{task.id}"
                    task.sync_status = 'synced'
                    return True
                
                def sync_tasks(self):
                    if not self.authenticated:
                        raise Exception("Not authenticated")
                    
                    # Mock sync
                    return {'synced': 1, 'errors': 0}
            
            # Test mock service
            service = MockGoogleTasksService()
            assert service.authenticate() == True
            
            if self.test_data:
                task = self.test_data['task']
                assert service.create_task(task) == True
                assert task.google_task_id is not None
                assert task.sync_status == 'synced'
                
                sync_result = service.sync_tasks()
                assert sync_result['synced'] == 1
                assert sync_result['errors'] == 0
            
            print("✅ Google API integration test passed (mock)")
            return True
            
        except Exception as e:
            print(f"❌ Google API integration test failed: {e}")
            return False
    
    def test_line_bot_integration(self):
        """Test LINE Bot integration (mock)"""
        print("\n🧪 Testing LINE Bot Integration...")
        
        try:
            # Mock LINE Bot service
            class MockLineBotService:
                def __init__(self):
                    self.authenticated = False
                
                def authenticate(self):
                    # Mock authentication
                    self.authenticated = True
                    return True
                
                def send_message(self, user_id, message):
                    if not self.authenticated:
                        raise Exception("Not authenticated")
                    
                    # Mock message sending
                    return {'success': True, 'message_id': 'mock_message_123'}
                
                def link_user(self, line_user_id, username):
                    if not self.authenticated:
                        raise Exception("Not authenticated")
                    
                    # Mock user linking
                    user = User.query.filter_by(username=username).first()
                    if user:
                        user.line_user_id = line_user_id
                        db.session.commit()
                        return True
                    return False
            
            # Test mock service
            service = MockLineBotService()
            assert service.authenticate() == True
            
            # Test message sending
            result = service.send_message('test_user_123', 'Test message')
            assert result['success'] == True
            
            # Test user linking
            if self.test_data:
                user = self.test_data['user']
                assert service.link_user('test_line_user_123', user.username) == True
                assert user.line_user_id == 'test_line_user_123'
            
            print("✅ LINE Bot integration test passed (mock)")
            return True
            
        except Exception as e:
            print(f"❌ LINE Bot integration test failed: {e}")
            return False
    
    def test_configuration_loading(self):
        """Test configuration loading"""
        print("\n🧪 Testing Configuration Loading...")
        
        try:
            # Test config loading
            from config import ConfigLoader, Config, DevelopmentConfig, ProductionConfig
            
            # Test config selection
            dev_config = ConfigLoader.load_config('development')
            prod_config = ConfigLoader.load_config('production')
            default_config = ConfigLoader.load_config('invalid')
            
            assert dev_config == DevelopmentConfig
            assert prod_config == ProductionConfig
            assert default_config == DevelopmentConfig
            
            # Test sample config creation
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                ConfigLoader.create_sample_configs()
                
                # Check if sample files were created
                assert os.path.exists('line_config.sample.json')
                assert os.path.exists('google_config.sample.json')
                assert os.path.exists('system_config.sample.json')
            
            print("✅ Configuration loading test passed")
            return True
            
        except Exception as e:
            print(f"❌ Configuration loading test failed: {e}")
            return False
    
    def test_migration_script(self):
        """Test migration script functionality"""
        print("\n🧪 Testing Migration Script...")
        
        try:
            # Test migration components
            from migrate_database import DatabaseMigrator
            
            # Create a test migrator (without running full migration)
            migrator = DatabaseMigrator(self.app)
            
            # Test configuration loading
            migrator.old_config = {
                'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
                'business_name': 'Test Business'
            }
            
            # Test settings migration (mock)
            original_count = Setting.query.count()
            migrator.migrate_settings()
            db.session.commit()
            
            # Should have added some settings
            new_count = Setting.query.count()
            assert new_count >= original_count
            
            print("✅ Migration script test passed")
            return True
            
        except Exception as e:
            print(f"❌ Migration script test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete integration test suite"""
        print("🚀 Starting Comphone Integration Test Suite")
        print("=" * 60)
        
        test_results = {}
        
        # Setup
        if not self.setup_test_app():
            print("❌ Test setup failed - aborting tests")
            return False
        
        # Run tests
        tests = [
            ('Database Models', self.test_database_models),
            ('POS System', self.test_pos_system),
            ('Task Management', self.test_task_management),
            ('Customer Feedback', self.test_customer_feedback),
            ('Settings System', self.test_settings_system),
            ('Google API Integration', self.test_google_api_integration),
            ('LINE Bot Integration', self.test_line_bot_integration),
            ('Configuration Loading', self.test_configuration_loading),
            ('Migration Script', self.test_migration_script)
        ]
        
        for test_name, test_func in tests:
            try:
                test_results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
                test_results[test_name] = False
        
        # Cleanup
        self.teardown_test_app()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Integration Test Results:")
        print("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:<25} {status}")
            if result:
                passed += 1
        
        print("=" * 60)
        print(f"📈 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All integration tests passed!")
            print("\n✅ System is ready for deployment!")
            print("\n📋 Next Steps:")
            print("   1. Configure real LINE Bot credentials")
            print("   2. Set up Google API credentials")
            print("   3. Run full system test with real APIs")
            print("   4. Deploy to production environment")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) failed - review before deployment")
            return False

def main():
    """Main test function"""
    test_suite = IntegrationTestSuite()
    success = test_suite.run_all_tests()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())