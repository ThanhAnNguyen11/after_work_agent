import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings
from backend.app.models import Base, User, GymClass, RecommendationLog, UserExperience, UserBehavioralInterest, ParticipationJournal, Notification

# For SQLite, we use connect_args={"check_same_thread": False} to allow multi-threaded access
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if users are already seeded
        if db.query(User).count() > 0:
            return

        print("Seeding database...")

        # 1. Seed Users
        users_data = [
            {
                "domain": "annt7",
                "full_name": "Nguyen Thanh An",
                "title": "Senior Software Engineer",
                "company": "PY",
                "org_group": "TEP",
                "department": "PCT",
                "squad": "Consumer Solutions",
                "interests": ["football", "gym", "ai", "swimming"]
            },
            {
                "domain": "binhnd2",
                "full_name": "Nguyen Duy Binh",
                "title": "Product Manager",
                "company": "PY",
                "org_group": "TEP",
                "department": "PCT",
                "squad": "Consumer Solutions",
                "interests": ["football", "badminton", "startup"]
            },
            {
                "domain": "cuonglm",
                "full_name": "Le Minh Cuong",
                "title": "Data Scientist",
                "company": "PY",
                "org_group": "TEP",
                "department": "PCT",
                "squad": "Data Platform",
                "interests": ["gym", "ai", "movies"]
            },
            {
                "domain": "duongnt",
                "full_name": "Ngo Thuy Duong",
                "title": "Designer",
                "company": "PY",
                "org_group": "BIZ",
                "department": "Partnership",
                "squad": None,
                "interests": ["zumba", "yoga", "coffee", "swimming"]
            },
            {
                "domain": "lannt",
                "full_name": "Nguyen Thi Lan",
                "title": "HR Executive",
                "company": "PY",
                "org_group": "HR",
                "department": "Talent Acquisition",
                "squad": None,
                "interests": ["running", "coffee", "board games"]
            },
            {
                "domain": "minhhoang",
                "full_name": "Hoang Duc Minh",
                "title": "Associate Engineer",
                "company": "PY",
                "org_group": "TEP",
                "department": "PCT",
                "squad": "Consumer Solutions",
                "interests": ["badminton", "ai", "movies"]
            }
        ]

        seeded_users = {}
        for u in users_data:
            user = User(
                domain=u["domain"],
                password="abc",
                is_onboarded=True,
                full_name=u["full_name"],
                title=u["title"],
                company=u["company"],
                org_group=u["org_group"],
                department=u["department"],
                squad=u["squad"]
            )
            user.interests = u["interests"]
            db.add(user)
            db.flush()
            seeded_users[user.domain] = user

        # 2. Seed Gym Classes (Recurring Classes)
        gym_classes_data = [
            {
                "class_name": "Yoga",
                "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
                "weekday": "Monday, Wednesday, Friday",
                "start_time": "12:00",
                "end_time": "13:00",
                "location": "Upfit VNG Studio Room A",
                "capacity": 15,
                "instructor": "Ngọc",
                "active": True
            },
            {
                "class_name": "Yoga",
                "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
                "weekday": "Tuesday, Thursday",
                "start_time": "12:00",
                "end_time": "13:00",
                "location": "Upfit VNG Studio Room A",
                "capacity": 15,
                "instructor": "Hà",
                "active": True
            },
            {
                "class_name": "Obstacles",
                "description": "Strength & Cardio workout involving functional obstacles (Intermediate-Hard).",
                "weekday": "Monday, Wednesday",
                "start_time": "12:00",
                "end_time": "13:00", 
                "location": "Upfit VNG Studio Room B",
                "capacity": 15,
                "instructor": "Huân",
                "active": True
            },
            {
                "class_name": "Abs",
                "description": "Strength workout focused on building abdominal power (Easy-Intermediate).",
                "weekday": "Tuesday, Thursday",
                "start_time": "12:00",
                "end_time": "13:00",
                "location": "Upfit VNG Studio Room A",
                "capacity": 20,
                "instructor": "Út",
                "active": True
            },
            {
                "class_name": "New Obstacles",
                "description": "New strength & cardio class with Huân at lunch (Intermediate-Hard).",
                "weekday": "Friday",
                "start_time": "12:00",
                "end_time": "13:00",
                "location": "Upfit VNG Studio Room B",
                "capacity": 15,
                "instructor": "Huân",
                "active": True
            },
            {
                "class_name": "Fitness Dance",
                "description": "Cardio workout through fitness dancing (Easy-Intermediate).",
                "weekday": "Monday, Wednesday",
                "start_time": "18:00",
                "end_time": "19:00",
                "location": "Upfit VNG Studio Room A",
                "capacity": 25,
                "instructor": "Trung",
                "active": True
            },
            {
                "class_name": "Yoga",
                "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
                "weekday": "Tuesday, Thursday, Friday",
                "start_time": "18:00",
                "end_time": "19:00",
                "location": "Upfit VNG Studio Room A",
                "capacity": 15,
                "instructor": "Ngọc",
                "active": True
            },
            {
                "class_name": "New Body Fit",
                "description": "New strength & conditioning evening class (Easy-Intermediate).",
                "weekday": "Monday",
                "start_time": "18:00",
                "end_time": "19:00",
                "location": "Upfit VNG Studio Room B",
                "capacity": 20,
                "instructor": "Shindo",
                "active": True
            },
            {
                "class_name": "Body Fit",
                "description": "Strength & conditioning workout to shape your body (Easy-Intermediate).",
                "weekday": "Tuesday, Wednesday, Thursday",
                "start_time": "18:00",
                "end_time": "19:00",
                "location": "Upfit VNG Studio Room B",
                "capacity": 20,
                "instructor": "Shindo",
                "active": True
            },
            {
                "class_name": "Swimming",
                "description": "Free swimming session at the company pool. Open for all employees.",
                "weekday": "Monday, Tuesday, Wednesday, Thursday, Friday",
                "start_time": "06:00",
                "end_time": "20:00",
                "location": "Company Swimming Pool",
                "capacity": 50,
                "instructor": "Self-regulated",
                "active": True
            }
        ]

        for g in gym_classes_data:
            gym_class = GymClass(**g)
            db.add(gym_class)

        db.commit()
        print("Database seeding completed.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()
