import random
from datetime import datetime, timedelta, date
from passlib.context import CryptContext
from models import SessionLocal, User, Category, Transaction, Base, engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_database():
    print("[INFO] Initializing FLO Database Seeding Script...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Create or retrieve Demo User
        demo_email = "demo@flo.app"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            hashed_pwd = pwd_context.hash("password123")
            user = User(email=demo_email, password_hash=hashed_pwd)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[OK] Created Demo User: {user.email} (ID: {user.id})")
        else:
            print(f"[INFO] Found existing Demo User: {user.email} (ID: {user.id})")

        # 2. Seed Standard Categories with Keywords and Monthly Limits
        categories_data = [
            {
                "name": "Food & Dining",
                "keywords": "zomato, swiggy, restaurant, cafe, mcdonalds, pizza, burger, food, dining",
                "monthly_limit": 8000.0
            },
            {
                "name": "Groceries & Supplies",
                "keywords": "blinkit, zepto, supermarket, groceries, milk, vegetables, fruits, store",
                "monthly_limit": 6000.0
            },
            {
                "name": "Utilities & Bills",
                "keywords": "electricity, wifi, internet, recharge, water bill, gas, mobile, electricity bill",
                "monthly_limit": 4000.0
            },
            {
                "name": "Transport & Travel",
                "keywords": "uber, ola, rapido, metro, petrol, fuel, cab, flight, auto",
                "monthly_limit": 5000.0
            },
            {
                "name": "Shopping & Tech",
                "keywords": "amazon, flipkart, myntra, clothes, electronics, laptop, shoes, gadgets",
                "monthly_limit": 15000.0
            }
        ]

        cat_map = {}
        for cat_info in categories_data:
            cat = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name == cat_info["name"]
            ).first()
            if not cat:
                cat = Category(
                    name=cat_info["name"],
                    keywords=cat_info["keywords"],
                    monthly_limit=cat_info["monthly_limit"],
                    user_id=user.id
                )
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_map[cat_info["name"]] = cat

        print(f"[OK] Configured {len(cat_map)} Categories for user.")

        # 3. Seed Realistic Transactions across past 180 days
        today = date.today()
        seeded_tx_count = 0

        # Descriptions template pool
        sample_expenses = [
            ("Food & Dining", ["Zomato dinner order", "Swiggy lunch bowl", "Starbucks coffee & bagel", "McDonalds burger combo", "Domino's pizza party", "Local cafe chai & snacks"]),
            ("Groceries & Supplies", ["Blinkit grocery order", "Zepto daily essentials", "Supermarket monthly ration", "Milk and bread daily", "Fresh vegetables market"]),
            ("Utilities & Bills", ["Airtel WiFi broadband bill", "Jio mobile recharge", "BESCOM electricity bill", "Piped gas bill"]),
            ("Transport & Travel", ["Uber ride to campus", "Ola cab to station", "Rapido bike taxi", "Metro card recharge", "Petrol refill at HP pump"]),
            ("Shopping & Tech", ["Amazon book purchase", "Myntra t-shirt & jeans", "Flipkart household items", "Boat earphones"])
        ]

        # Generate Monthly Income on 1st of each month for 6 months
        for m in range(6):
            # 1st of month
            inc_date = date(today.year, max(1, today.month - m), 1)
            existing_inc = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_date == inc_date,
                Transaction.type == "Income"
            ).first()
            if not existing_inc:
                inc_tx = Transaction(
                    amount=65000.0,
                    type="Income",
                    description="Monthly Salary Credit",
                    transaction_date=inc_date,
                    category_id=None,
                    user_id=user.id
                )
                db.add(inc_tx)
                seeded_tx_count += 1

        # Generate ~100 realistic expenses over 180 days
        random.seed(42) # Deterministic random generation for consistent seeding
        for day_offset in range(180):
            tx_date = today - timedelta(days=day_offset)
            
            # 60% chance of 1 or 2 expenses per day
            if random.random() < 0.6:
                num_tx = random.choice([1, 1, 2])
                for _ in range(num_tx):
                    cat_name, desc_pool = random.choice(sample_expenses)
                    desc = random.choice(desc_pool)
                    category = cat_map[cat_name]

                    # Generate realistic amount based on category
                    if cat_name == "Food & Dining":
                        amt = round(random.uniform(150, 750), 2)
                    elif cat_name == "Groceries & Supplies":
                        amt = round(random.uniform(200, 1200), 2)
                    elif cat_name == "Utilities & Bills":
                        amt = round(random.uniform(400, 2200), 2)
                    elif cat_name == "Transport & Travel":
                        amt = round(random.uniform(80, 650), 2)
                    else:
                        amt = round(random.uniform(499, 2500), 2)

                    tx = Transaction(
                        amount=amt,
                        type="Expense",
                        description=desc,
                        transaction_date=tx_date,
                        category_id=category.id,
                        user_id=user.id
                    )
                    db.add(tx)
                    seeded_tx_count += 1

        # 4. Insert Statistical Outliers (for IQR Anomaly Detection Testing)
        outliers = [
            ("Shopping & Tech", 48500.0, "Amazon Gaming Laptop Purchase", today - timedelta(days=25)),
            ("Transport & Travel", 18500.0, "Roundtrip Flight Tickets to Goa", today - timedelta(days=55)),
            ("Shopping & Tech", 24900.0, "Apple iPad Air Purchase", today - timedelta(days=110))
        ]

        for cat_name, amt, desc, out_date in outliers:
            cat = cat_map[cat_name]
            tx = Transaction(
                amount=amt,
                type="Expense",
                description=desc,
                transaction_date=out_date,
                category_id=cat.id,
                user_id=user.id
            )
            db.add(tx)
            seeded_tx_count += 1

        db.commit()

        total_txs = db.query(Transaction).filter(Transaction.user_id == user.id).count()

        print("\n[SUCCESS] Database Seeding Completed Successfully!")
        print("--------------------------------------------------")
        print(f"Demo Credentials : Email: {demo_email} | Password: password123")
        print(f"Categories Seeded : {len(cat_map)}")
        print(f"Total Transactions : {total_txs} (New: {seeded_tx_count})")
        print(f"Statistical Outliers: 3 (Laptop, Flights, iPad)")
        print("--------------------------------------------------\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
