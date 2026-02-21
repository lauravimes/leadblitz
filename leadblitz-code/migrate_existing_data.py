import os
import sys
from sqlalchemy import text
from helpers.models import SessionLocal, User
from helpers.auth import hash_password

def migrate_to_multi_user():
    print("Starting migration to multi-user system...")
    
    db = SessionLocal()
    try:
        print("Step 1: Creating tables if they don't exist...")
        from helpers.models import Base, engine
        Base.metadata.create_all(bind=engine)
        print("Tables created/verified")
        
        print("\nStep 2: Adding user_id columns to existing tables if needed...")
        
        try:
            db.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS user_id INTEGER"))
            db.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER"))
            db.commit()
            print("Added user_id columns to campaigns and leads tables")
        except Exception as e:
            print(f"Note: Columns may already exist - {e}")
            db.rollback()
        
        print("\nStep 3: Creating default admin user...")
        default_email = "admin@example.com"
        default_password = "admin123"
        
        existing_user = db.query(User).filter(User.email == default_email).first()
        if existing_user:
            print(f"Default user '{default_email}' already exists (ID: {existing_user.id})")
            default_user_id = existing_user.id
        else:
            default_user = User(
                email=default_email,
                password_hash=hash_password(default_password),
                full_name="Default Admin",
                is_active=True,
                completed_tutorial=True
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            default_user_id = default_user.id
            print(f"Created default user: {default_email} / {default_password} (ID: {default_user_id})")
        
        print("\nStep 4: Checking for existing campaigns...")
        result = db.execute(text("SELECT COUNT(*) as count FROM campaigns WHERE user_id IS NULL"))
        orphan_campaigns = result.scalar()
        
        if orphan_campaigns > 0:
            print(f"Found {orphan_campaigns} campaigns without user_id. Assigning to default user...")
            db.execute(text(f"UPDATE campaigns SET user_id = {default_user_id} WHERE user_id IS NULL"))
            db.commit()
            print(f"Updated {orphan_campaigns} campaigns")
        else:
            print("No orphan campaigns found")
        
        print("\nStep 5: Checking for existing leads...")
        result = db.execute(text("SELECT COUNT(*) as count FROM leads WHERE user_id IS NULL"))
        orphan_leads = result.scalar()
        
        if orphan_leads > 0:
            print(f"Found {orphan_leads} leads without user_id. Assigning to default user...")
            db.execute(text(f"UPDATE leads SET user_id = {default_user_id} WHERE user_id IS NULL"))
            db.commit()
            print(f"Updated {orphan_leads} leads")
        else:
            print("No orphan leads found")
        
        print("\nStep 6: Adding foreign key constraints if needed...")
        try:
            db.execute(text("ALTER TABLE campaigns ADD CONSTRAINT IF NOT EXISTS fk_campaigns_user FOREIGN KEY (user_id) REFERENCES users(id)"))
            db.execute(text("ALTER TABLE leads ADD CONSTRAINT IF NOT EXISTS fk_leads_user FOREIGN KEY (user_id) REFERENCES users(id)"))
            db.commit()
            print("Added foreign key constraints")
        except Exception as e:
            print(f"Note: Constraints may already exist - {e}")
            db.rollback()
        
        print("\nMigration complete!")
        print(f"\nDefault login credentials:")
        print(f"  Email: {default_email}")
        print(f"  Password: {default_password}")
        print("\nPlease change this password after first login!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate_to_multi_user()
