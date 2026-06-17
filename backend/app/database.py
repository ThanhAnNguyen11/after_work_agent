from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings
from backend.app.models import Base

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

# Authoritative fixed-activities dataset. Edit here to update the platform schedule.
FIXED_ACTIVITIES_DATA = [
    # --- Lunch classes (12:00–13:00) ---
    {
        "class_name": "Yoga",
        "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
        "weekday": "Monday, Wednesday, Friday",
        "start_time": "12:00", "end_time": "13:00",
        "location": "Upfit VNG Studio Room A",
        "capacity": 15, "instructor": "Ngọc",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút — phiếu hết hiệu lực khi lớp bắt đầu. Nên mang thảm cá nhân.",
    },
    {
        "class_name": "Yoga",
        "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
        "weekday": "Tuesday, Thursday",
        "start_time": "12:00", "end_time": "13:00",
        "location": "Upfit VNG Studio Room A",
        "capacity": 15, "instructor": "Hà",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút — phiếu hết hiệu lực khi lớp bắt đầu. Nên mang thảm cá nhân.",
    },
    {
        "class_name": "Obstacles",
        "description": "Strength & Cardio workout involving functional obstacles (Intermediate-Hard).",
        "weekday": "Monday, Wednesday",
        "start_time": "12:00", "end_time": "13:00",
        "location": "Upfit VNG Studio Room B",
        "capacity": 15, "instructor": "Huân",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút. Mang giày thể thao phù hợp.",
    },
    {
        "class_name": "Abs",
        "description": "Strength workout focused on building abdominal power (Easy-Intermediate).",
        "weekday": "Tuesday, Thursday",
        "start_time": "12:00", "end_time": "13:00",
        "location": "Upfit VNG Studio Room A",
        "capacity": 20, "instructor": "Út",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút. Mang giày thể thao phù hợp.",
    },
    {
        "class_name": "New Obstacles",
        "description": "New strength & cardio class with Huân at lunch (Intermediate-Hard).",
        "weekday": "Friday",
        "start_time": "12:00", "end_time": "13:00",
        "location": "Upfit VNG Studio Room B",
        "capacity": 15, "instructor": "Huân",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút. Mang giày thể thao phù hợp.",
    },
    # --- Evening classes (18:00–19:00) ---
    {
        "class_name": "Fitness Dance",
        "description": "Cardio workout through fitness dancing (Easy-Intermediate).",
        "weekday": "Monday, Wednesday",
        "start_time": "18:00", "end_time": "19:00",
        "location": "Upfit VNG Studio Room A",
        "capacity": 25, "instructor": "Trung",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Mỗi người 1 phiếu/lớp, số lượng có hạn. Có mặt sớm ít nhất 5 phút.",
    },
    {
        "class_name": "Yoga",
        "description": "Flexibility workout focusing on yoga postures and breathing (Easy-Intermediate).",
        "weekday": "Tuesday, Thursday, Friday",
        "start_time": "18:00", "end_time": "19:00",
        "location": "Upfit VNG Studio Room A",
        "capacity": 15, "instructor": "Ngọc",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút — phiếu hết hiệu lực khi lớp bắt đầu. Nên mang thảm cá nhân.",
    },
    {
        "class_name": "New Body Fit",
        "description": "New strength & conditioning evening class (Easy-Intermediate).",
        "weekday": "Monday",
        "start_time": "18:00", "end_time": "19:00",
        "location": "Upfit VNG Studio Room B",
        "capacity": 20, "instructor": "Shindo",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút. Mang giày thể thao phù hợp.",
    },
    {
        "class_name": "Body Fit",
        "description": "Strength & conditioning workout to shape your body (Easy-Intermediate).",
        "weekday": "Tuesday, Wednesday, Thursday",
        "start_time": "18:00", "end_time": "19:00",
        "location": "Upfit VNG Studio Room B",
        "capacity": 20, "instructor": "Shindo",
        "guidelines": "Nhận phiếu tại quầy lễ tân trước giờ học. Có mặt sớm ít nhất 5 phút. Mang giày thể thao phù hợp.",
    },
    # --- Open-access facilities (all week) ---
    {
        "class_name": "Running",
        "description": "Free outdoor running track available for all employees. Run at your own pace.",
        "weekday": "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
        "start_time": "06:00", "end_time": "20:00",
        "location": "VNG Campus Running Track",
        "capacity": 100, "instructor": "Self-regulated",
        "guidelines": "Không cần đăng ký trước. Check-in bằng thẻ nhân viên. Mang giày chạy bộ phù hợp. Đường chạy mở từ 06:00 đến 20:00 mỗi ngày.",
    },
    {
        "class_name": "Swimming",
        "description": "Free swimming session at the company pool. Open for all employees.",
        "weekday": "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
        "start_time": "06:00", "end_time": "20:00",
        "location": "Company Swimming Pool",
        "capacity": 50, "instructor": "Self-regulated",
        "guidelines": "Không cần đăng ký trước. Check-in bằng thẻ nhân viên hoặc FaceID. Mặc trang phục bơi và tắm tráng trước khi xuống hồ. Không mang đồ thủy tinh, không nhảy cắm đầu, không chạy nhảy quanh hồ.",
    },
    {
        "class_name": "Gym",
        "description": "Free workout at the gym. Use equipment at your own pace. Open for all employees.",
        "weekday": "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
        "start_time": "06:00", "end_time": "20:00",
        "location": "Upfit VNG Gym",
        "capacity": 50, "instructor": "Self-regulated",
        "guidelines": "Check-in bằng FaceID hoặc thẻ nhân viên. Mang giày thể thao — không đi dép hoặc tập chân trần. Giờ mở: Thứ 2–6 07:00–20:30, Thứ 7–CN 08:00–19:00. Sắp xếp tạ về đúng vị trí sau khi dùng.",
    },
]


def seed_fixed_activities(db) -> int:
    """Replace all fixed activities with the authoritative FIXED_ACTIVITIES_DATA list.
    Clears dependent recommendation_logs (gym_class rows) first to satisfy FK constraints.
    Returns the number of rows inserted."""
    from backend.app.models import FixedActivity, RecommendationLog
    db.query(RecommendationLog).filter(RecommendationLog.gym_class_id.isnot(None)).delete()
    db.query(FixedActivity).delete()
    for data in FIXED_ACTIVITIES_DATA:
        db.add(FixedActivity(
            class_name=data["class_name"],
            description=data.get("description"),
            weekday=data["weekday"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            location=data["location"],
            capacity=data.get("capacity", 20),
            instructor=data.get("instructor"),
            guidelines=data.get("guidelines"),
            active=True,
        ))
    db.commit()
    return len(FIXED_ACTIVITIES_DATA)
