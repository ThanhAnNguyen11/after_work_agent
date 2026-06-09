from datetime import datetime, timedelta
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings
from backend.app.models import Base, User, GymClass, Activity, ActivityParticipant, Memory, RecommendationLog, UserExperience, UserBehavioralInterest, ParticipationJournal, Notification

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

        # 3. Seed Activities (Dynamic Activities)
        # Tonight's Date (we'll set it to current date at specific times)
        now = datetime.now()
        tonight_6pm = datetime(now.year, now.month, now.day, 18, 0)
        tonight_630pm = datetime(now.year, now.month, now.day, 18, 30)

        # Activity 1: Football Friendly Match (Scenario 5 & 1)
        # Needs 2 more players (limit 10, current 8)
        act1 = Activity(
            title="Football Friendly Match 7v7",
            description="Casual game. Need 2 more players to complete the teams.",
            activity_type="football",
            start_time=tonight_6pm,
            end_time=tonight_6pm + timedelta(hours=1),
            location="Z-Plex Football Field",
            participant_limit=10,
            current_participants=8,
            created_by=seeded_users["binhnd2"].id
        )
        db.add(act1)
        db.flush()

        # Add participants to Activity 1
        # binhnd2 is creator & participant, cuonglm is participant
        participants_act1 = [
            seeded_users["binhnd2"].id,
            seeded_users["cuonglm"].id,
        ]
        # Seed extra simulated users who are participants
        for u_id in participants_act1:
            p = ActivityParticipant(activity_id=act1.id, user_id=u_id)
            db.add(p)

        # Activity 2: AI Study Group / Sharing Session (Scenario 1 & 4)
        act2 = Activity(
            title="AI Sharing: Large Language Models in Production",
            description="Discussing prompt engineering, retrieval augmented generation, and deploy pipelines.",
            activity_type="ai",
            start_time=tonight_630pm,
            end_time=tonight_630pm + timedelta(hours=1),
            location="Meeting Room 3A (TEP wing)",
            participant_limit=15,
            current_participants=3,
            created_by=seeded_users["cuonglm"].id
        )
        db.add(act2)
        db.flush()

        # Add participants: cuonglm (Data Platform) and duongnt (Partnership)
        participants_act2 = [
            seeded_users["cuonglm"].id,
            seeded_users["duongnt"].id,
        ]
        for u_id in participants_act2:
            p = ActivityParticipant(activity_id=act2.id, user_id=u_id)
            db.add(p)

        # Activity 3: Board Game Night (Scenario 3)
        act3 = Activity(
            title="Catan & Avalon Board Game Night",
            description="Weekly board game gather. Everyone is welcome!",
            activity_type="board games",
            start_time=tonight_6pm + timedelta(days=1), # Tomorrow
            end_time=tonight_6pm + timedelta(days=1) + timedelta(hours=2),
            location="Pantry Area 2nd Floor",
            participant_limit=8,
            current_participants=1,
            created_by=seeded_users["lannt"].id
        )
        db.add(act3)
        db.flush()
        db.add(ActivityParticipant(activity_id=act3.id, user_id=seeded_users["lannt"].id))

        # 4. Seed Historical Participation for annt7 to create a "Routine Trap" (Gym, Gym, Gym)
        # This will trigger Scenario 3 & Discovery Agent
        for i in range(1, 6):
            past_date = now - timedelta(days=i)
            # Create a past finished activity
            past_act = Activity(
                title=f"Gym Session Day {i}",
                description="Regular workout.",
                activity_type="gym",
                start_time=past_date,
                end_time=past_date + timedelta(hours=1),
                location="Company Gym",
                participant_limit=5,
                current_participants=1,
                created_by=seeded_users["annt7"].id,
                created_at=past_date
            )
            db.add(past_act)
            db.flush()
            db.add(ActivityParticipant(activity_id=past_act.id, user_id=seeded_users["annt7"].id))

        # 5. Add initial memories for annt7
        m1 = Memory(
            user_id=seeded_users["annt7"].id,
            content="I usually go to the gym after work to keep fit.",
            created_at=now - timedelta(days=3)
        )
        db.add(m1)

        db.commit()
        print("Database seeding completed.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()
