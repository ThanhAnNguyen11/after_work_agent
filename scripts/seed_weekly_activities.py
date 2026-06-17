"""
Seed ~100 user-created activities for the current week (Mon 15/6 – Sun 21/6/2026).
Covers all activity types, on-campus and off-campus, spread across morning / lunch / after-work.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend.app.database import SessionLocal
from backend.app.models import Activity, ActivityParticipant

db = SessionLocal()

# ── Creator user IDs (from existing users) ──────────────────────────────────
CREATORS = [11, 12, 13]   # An, Phuong, Ly

# ── Base date: Monday 16/6/2026 ─────────────────────────────────────────────
BASE = datetime(2026, 6, 15)   # Monday

def day(offset: int, h: int, m: int = 0) -> datetime:
    return BASE + timedelta(days=offset, hours=h, minutes=m)

def end(start: datetime, dur_h: float = 1.0) -> datetime:
    return start + timedelta(hours=dur_h)

# ── Location pools ────────────────────────────────────────────────────────────
ON = {
    "studio_a":   "Upfit VNG Studio Room A",
    "studio_b":   "Upfit VNG Studio Room B",
    "football":   "VNG Campus Football Field",
    "running":    "VNG Campus Running Track",
    "rooftop":    "VNG Campus Rooftop",
    "conf":       "Conference Room Saigon, Lầu 6",
    "pantry":     "Pantry Area, Lầu 3",
    "pool":       "Company Swimming Pool",
    "gym":        "Gym",
}
OFF = {
    "hoan_luong": "Hoàn Lương Restaurant, Quận 7",
    "coffee_q7":  "The Coffee House Tân Thuận, Quận 7",
    "landmark":   "Sky Bar Landmark 81",
    "dam_sen":    "Công viên Đầm Sen",
    "san_bong":   "Sân bóng mini Quận 7 Sport Center",
    "lotteria":   "Lotteria Tân Thuận Đông",
    "bitexco":    "Bitexco Financial Tower Sky Deck",
    "highland":   "Highlands Coffee Nguyễn Thị Thập",
    "bowling":    "Saigon Superbowl Crescent Mall",
    "park":       "Công viên Phú Mỹ Hưng",
}

# ── Activity catalog: (title, type, location_key, is_on_campus, start_dt, dur_h, limit, difficulty, desc) ──
ACTIVITIES = [
    # ── MONDAY 15/6 ─────────────────────────────────────────────────────────
    ("Chạy bộ đầu tuần cùng nhau",      "running",      "running",    True,  day(0,17,30), 1.0, 10, None,       "Khởi động tuần mới với vòng chạy nhẹ nhàng quanh campus"),
    ("Yoga buổi tối thư giãn",          "yoga",         "studio_a",   True,  day(0,18,0),  1.0, 15, "Beginner", "45 phút yoga phục hồi sau ngày làm việc dài"),
    ("Board game tại Pantry",           "board games",  "pantry",     True,  day(0,18,30), 2.0, 8,  None,       "Chill cùng bạn bè với Catan, Ticket to Ride và nhiều game khác"),
    ("Coffee chat chiều thứ Hai",       "coffee chat",  "highland",   False, day(0,17,0),  1.5, 6,  None,       "Ngồi tán gẫu nhẹ nhàng, xả stress sau tuần làm việc"),
    ("Đá banh mini 5vs5",               "football",     "san_bong",   False, day(0,18,0),  1.5, 10, "Medium",   "Trận đấu thân thiện sau giờ làm, tất cả trình độ đều chào đón"),
    ("AI Study Group – Prompt Engineering", "ai",       "conf",       True,  day(0,19,0),  1.5, 12, None,       "Chia sẻ kỹ thuật prompt nâng cao và thảo luận use case thực tế"),

    # ── TUESDAY 16/6 ────────────────────────────────────────────────────────
    ("Badminton buổi sáng sớm",         "badminton",    "studio_b",   True,  day(1,6,30),  1.0, 8,  None,       "Đánh cầu lông nhẹ nhàng trước giờ làm, tinh thần phấn chấn cả ngày"),
    ("Book Club – Atomic Habits",       "book club",    "conf",       True,  day(1,12,0),  1.0, 10, None,       "Cùng đọc và thảo luận chương 3-5 của Atomic Habits"),
    ("Ăn trưa cùng nhau tại Hoàn Lương","dining",       "hoan_luong", False, day(1,12,0),  1.0, 8,  None,       "Bữa trưa thân thiện để gặp gỡ đồng nghiệp ngoài giờ họp"),
    ("Pickleball cho người mới",        "pickleball",   "studio_b",   True,  day(1,17,30), 1.5, 8,  "Beginner", "Học pickleball từ đầu, không cần kinh nghiệm trước"),
    ("Zumba cực vui",                   "zumba",        "studio_a",   True,  day(1,18,0),  1.0, 20, None,       "Lớp nhảy zumba năng động, không cần biết nhảy trước"),
    ("Watch Party – Movie Tuesday",     "movies",       "pantry",     True,  day(1,19,0),  2.0, 12, None,       "Xem phim cùng nhau tại pantry với popcorn và snacks"),
    ("Chạy bộ hoàng hôn",              "running",      "running",    True,  day(1,17,0),  0.75,8,  None,       "Vòng chạy 5km nhẹ nhàng ngắm hoàng hôn trên campus"),
    ("English Speaking Club",           "english",      "conf",       True,  day(1,19,0),  1.5, 10, None,       "Luyện nói tiếng Anh qua thảo luận chủ đề thú vị mỗi tuần"),

    # ── WEDNESDAY 17/6 ──────────────────────────────────────────────────────
    ("Bơi lội buổi sáng",              "swimming",     "pool",       True,  day(2,6,0),   1.0, 10, None,       "Bơi tự do buổi sáng, refreshing để vào ngày mới đầy năng lượng"),
    ("Yoga giữa trưa",                  "yoga",         "studio_a",   True,  day(2,12,0),  0.75,12, "Beginner", "30 phút yoga nhẹ giữa giờ, thả lỏng vai cổ và lưng"),
    ("Football 7vs7 cuối tuần sớm",    "football",     "football",   True,  day(2,17,30), 1.5, 14, "Medium",   "Trận bóng thân thiện trên sân campus, đủ chỗ cho 2 đội"),
    ("Knowledge Sharing – Data Engineering","knowledge-sharing","conf",True,  day(2,18,0),  1.5, 20, None,      "Anh em Data team chia sẻ kiến trúc pipeline mới nhất"),
    ("Cà phê & coding – Side Project", "coffee chat",  "coffee_q7",  False, day(2,17,30), 2.0, 6,  None,       "Ngồi code side project cùng nhau, vừa uống cà phê vừa học hỏi"),
    ("Boxing cho người mới bắt đầu",   "boxing",       "studio_b",   True,  day(2,18,0),  1.0, 8,  "Beginner", "Học kỹ thuật boxing cơ bản, xả stress cực hiệu quả"),
    ("Đi ăn tối ở Hoàn Lương",        "dining",       "hoan_luong", False, day(2,19,0),  1.5, 8,  None,       "Bữa tối ấm cúng cùng đồng nghiệp sau giờ làm"),
    ("Esports – Valorant 5v5",         "esports",      "pantry",     True,  day(2,20,0),  2.0, 10, None,       "Trận Valorant 5v5 xếp hàng friendly, mọi rank đều hoan nghênh"),

    # ── THURSDAY 18/6 ───────────────────────────────────────────────────────
    ("Gym buổi sáng",                   "gym",          "gym",        True,  day(3,6,30),  1.0, 8,  None,       "Tập gym buổi sáng, bắt đầu ngày mới với đầy năng lượng"),
    ("Product Thinking Workshop",       "product",      "conf",       True,  day(3,12,0),  1.0, 15, None,       "Workshop thực hành framework product discovery cho PM và designer"),
    ("Picnic tại công viên PHM",        "picnics",      "park",       False, day(3,17,30), 2.0, 12, None,       "Trải chiếu, mang đồ ăn, chill cùng nhau tại công viên Phú Mỹ Hưng"),
    ("Badminton doubles",               "badminton",    "studio_b",   True,  day(3,17,30), 1.5, 8,  None,       "Đánh cầu đôi, vừa thi đấu vừa giao lưu"),
    ("Taekwondo – lớp cơ bản",         "taekwondo",    "studio_a",   True,  day(3,18,0),  1.0, 12, "Beginner", "Học các đòn cơ bản taekwondo, tăng sức mạnh và sự tự tin"),
    ("Networking Dinner – Cross team", "dining",       "landmark",   False, day(3,19,0),  2.0, 16, None,       "Bữa tối giao lưu kết nối các team khác nhau tại Sky Bar"),
    ("AI & LLM Workshop thực hành",    "ai",           "conf",       True,  day(3,19,0),  2.0, 20, None,       "Hands-on workshop xây dựng ứng dụng với LangChain và GPT-4o"),
    ("Karaoke sau giờ làm",            "karaoke",      "lotteria",   False, day(3,20,0),  2.0, 10, None,       "Hát karaoke xả stress cuối tuần, không cần hát hay"),

    # ── FRIDAY 19/6 ─────────────────────────────────────────────────────────
    ("Yoga Vinasa buổi sáng",          "yoga",         "studio_a",   True,  day(4,6,30),  1.0, 15, "Medium",   "Lớp yoga vinyasa năng động, phù hợp người đã có nền tảng cơ bản"),
    ("Bơi lội buổi trưa",             "swimming",     "pool",       True,  day(4,12,0),  0.75,10, None,       "Bơi tự do 30 phút giữa ngày, refreshing và tỉnh táo ngay"),
    ("Friday Football – TGIF Edition","football",     "football",   True,  day(4,17,30), 1.5, 16, None,       "Trận đặc biệt cuối tuần, mọi người đều được chơi"),
    ("Book Club – The Lean Startup",   "book club",    "highland",   False, day(4,17,30), 1.5, 8,  None,       "Thảo luận Build-Measure-Learn loop và áp dụng vào dự án thực tế"),
    ("Esports Tournament – FIFA",      "esports",      "pantry",     True,  day(4,18,0),  3.0, 8,  None,       "Giải FIFA nội bộ, vô địch được 1 bữa cafe miễn phí"),
    ("Happy Hour – Drinks & Board Games","board games","highland",   False, day(4,19,0),  2.5, 10, None,       "Cuối tuần thư giãn với board game và đồ uống tại cafe yêu thích"),
    ("Chạy bộ Friday 5K",             "running",      "running",    True,  day(4,17,0),  0.75,12, None,       "Kết thúc tuần làm việc với vòng chạy 5km đốt calo"),
    ("English Movie Night",            "movies",       "lotteria",   False, day(4,19,30), 2.0, 12, None,       "Xem phim tiếng Anh có phụ đề, vừa giải trí vừa luyện nghe"),

    # ── SATURDAY 20/6 ───────────────────────────────────────────────────────
    ("Morning Run & Coffee",           "running",      "park",       False, day(5,7,0),   1.5, 15, None,       "Chạy bộ buổi sáng tại công viên, uống cafe sau khi chạy xong"),
    ("Badminton cuối tuần",            "badminton",    "san_bong",   False, day(5,8,0),   2.0, 8,  None,       "Đánh cầu thoải mái cuối tuần, không áp lực"),
    ("Hội sách & cà phê",             "book club",    "highland",   False, day(5,9,0),   2.0, 8,  None,       "Cùng đọc sách yêu thích và chia sẻ cảm nhận trong không gian cafe"),
    ("Ăn sáng cùng nhau",             "dining",       "hoan_luong", False, day(5,8,30),  1.0, 8,  None,       "Bữa sáng thư thả cuối tuần, không cần vội vã"),
    ("Yoga buổi sáng cuối tuần",      "yoga",         "studio_a",   True,  day(5,8,0),   1.0, 15, "Beginner", "Yoga nhẹ nhàng đón buổi sáng cuối tuần, không vội vã"),
    ("Football 7vs7 Saturday Cup",    "football",     "san_bong",   False, day(5,9,0),   2.0, 14, "Medium",   "Giải bóng đá nội bộ thứ Bảy, ai thắng ai thua đều vui"),
    ("Đi bowling cùng nhau",          "board games",  "bowling",    False, day(5,15,0),  2.0, 10, None,       "Đua bowling thân thiện, không cần kinh nghiệm"),
    ("Karaoke cuối tuần",             "karaoke",      "lotteria",   False, day(5,16,0),  2.5, 12, None,       "Hát karaoke xả stress cuối tuần với cả nhóm"),
    ("Picnic Công viên Phú Mỹ Hưng",  "picnics",      "park",       False, day(5,16,0),  2.5, 15, None,       "Trải chiếu, ăn vặt và chill tại công viên buổi chiều"),
    ("AI Demo Day – Side Projects",   "ai",           "conf",       True,  day(5,14,0),  2.0, 20, None,       "Demo các side project AI/ML của anh em trong công ty"),
    ("Networking Brunch",             "dining",       "landmark",   False, day(5,10,30), 2.0, 12, None,       "Brunch giao lưu tại tầng cao, kết nối anh em ngoài giờ làm"),
    ("Boxing – Intermediate Class",   "boxing",       "studio_b",   True,  day(5,9,0),   1.0, 8,  "Medium",   "Lớp boxing nâng cao kỹ thuật, đấu găng nhẹ cuối buổi"),
    ("Swimming race & fun",           "swimming",     "pool",       True,  day(5,10,0),  1.5, 10, None,       "Thi bơi thân thiện trong nhóm, mọi tốc độ đều được chào đón"),

    # ── SUNDAY 21/6 ─────────────────────────────────────────────────────────
    ("Yoga Chủ nhật thư giãn",        "yoga",         "studio_a",   True,  day(6,8,0),   1.0, 15, "Beginner", "Yoga chậm và nhẹ nhàng đón Chủ nhật, thư giãn toàn thân"),
    ("Chạy bộ sáng Chủ nhật",        "running",      "park",       False, day(6,7,0),   1.5, 12, None,       "Chạy bộ quanh công viên Chủ nhật sáng, nhẹ nhàng và thư thái"),
    ("Brunch & Movie Review",         "movies",       "highland",   False, day(6,10,0),  2.0, 8,  None,       "Uống cafe, ăn bánh và review phim tuần qua cùng nhau"),
    ("Sunday Badminton",              "badminton",    "studio_b",   True,  day(6,9,0),   1.5, 8,  None,       "Đánh cầu lông Chủ nhật, nhẹ nhàng không thi đấu"),
    ("Picnic & Acoustic Music",       "picnics",      "park",       False, day(6,15,0),  3.0, 15, None,       "Picnic buổi chiều có nhạc acoustic live, chill hoàn toàn"),
    ("Board Game Sunday",             "board games",  "highland",   False, day(6,14,0),  3.0, 10, None,       "Board game marathon Chủ nhật: Codenames, Dixit, Pandemic"),
    ("Karaoke – End of Week Party",   "karaoke",      "lotteria",   False, day(6,18,0),  2.5, 16, None,       "Tổng kết tuần với karaoke và đồ uống, không ai phải hát hay"),
    ("Taekwondo practice",            "taekwondo",    "studio_a",   True,  day(6,10,0),  1.5, 10, "Medium",   "Luyện tập taekwondo tự do Chủ nhật, ôn đòn và sparring nhẹ"),

    # ── THÊM MID-WEEK (back-fill cho đa dạng) ───────────────────────────────
    # Monday thêm
    ("Gym – Upper Body Monday",       "gym",          "gym",        True,  day(0,6,30),  1.0, 8,  "Medium",   "Tập ngực, vai, tay buổi sáng thứ Hai với người cùng lịch"),
    ("Swimming laps – lunchtime",     "swimming",     "pool",       True,  day(0,12,0),  0.75,8,  None,       "Bơi giữa trưa, refreshing ngay và giữ dáng"),
    ("Product Case Study Lunch",      "product",      "conf",       True,  day(0,12,0),  1.0, 10, None,       "Thảo luận case study sản phẩm nổi bật trong giờ ăn trưa"),

    # Tuesday thêm
    ("Gym – Leg Day Tuesday",         "gym",          "gym",        True,  day(1,17,30), 1.0, 6,  "Medium",   "Leg day cùng nhau, hỗ trợ nhau giữ form và không bỏ cuộc"),
    ("Taekwondo – thứ Ba",            "taekwondo",    "studio_b",   True,  day(1,18,0),  1.0, 10, "Beginner", "Lớp taekwondo cơ bản dành cho người mới hoàn toàn"),
    ("Off-campus dinner TEP team",    "dining",       "hoan_luong", False, day(1,18,30), 1.5, 8,  None,       "Bữa tối ngoài công ty, chill cùng anh em TEP team"),

    # Wednesday thêm
    ("Gym – Full Body Strength",      "gym",          "gym",        True,  day(2,6,30),  1.0, 8,  "Medium",   "Full body workout buổi sáng, mồ hôi ra đầu tuần năng lượng cả ngày"),
    ("Pickleball intermediate",       "pickleball",   "studio_b",   True,  day(2,17,30), 1.5, 8,  "Medium",   "Trận pickleball cho người đã biết cơ bản, đánh doubles"),
    ("Bitexco Rooftop meetup",        "coffee chat",  "bitexco",    False, day(2,18,30), 1.5, 8,  None,       "Uống cocktail ngắm Sài Gòn từ trên cao, kết nối networking"),

    # Thursday thêm
    ("Yoga – Power Flow Thursday",    "yoga",         "studio_a",   True,  day(3,6,30),  1.0, 12, "Medium",   "Yoga power flow buổi sáng thứ Năm, tăng sức mạnh và linh hoạt"),
    ("English Writing Workshop",      "english",      "conf",       True,  day(3,12,0),  1.0, 10, None,       "Workshop viết email và báo cáo tiếng Anh chuyên nghiệp"),
    ("Bowling night – Team BIZ",      "board games",  "bowling",    False, day(3,19,0),  2.0, 10, None,       "Thi bowling thân thiện cho team BIZ, winner được chọn địa điểm ăn tiếp"),

    # Friday thêm
    ("Gym – Push Pull Friday",        "gym",          "gym",        True,  day(4,6,30),  1.0, 8,  "Medium",   "Buổi gym cuối tuần, push pull legs routine"),
    ("Zumba Friday Party",            "zumba",        "studio_a",   True,  day(4,17,30), 1.0, 20, None,       "Kết thúc tuần bằng lớp Zumba nhảy vui, mồ hôi và nụ cười"),
    ("Coffee đầu giờ tối thứ Sáu",   "coffee chat",  "highland",   False, day(4,17,0),  1.0, 6,  None,       "Gặp gỡ nhẹ nhàng trước khi ai về nhà nấy"),
    ("Knowledge Sharing – Security",  "knowledge-sharing","conf",   True,  day(4,18,0),  1.5, 15, None,       "Chia sẻ thực tế về bảo mật ứng dụng và các lỗ hổng phổ biến"),
    ("Concerts & Live Music Night",   "concerts",     "landmark",   False, day(4,20,0),  2.5, 16, None,       "Đêm nhạc live acoustic tại Landmark, uống cocktail nghe nhạc"),

    # Saturday thêm
    ("Gym – Saturday Morning",        "gym",          "gym",        True,  day(5,8,0),   1.0, 10, None,       "Tập gym thứ Bảy sáng, nhẹ nhàng hơn ngày thường"),
    ("Zumba cuối tuần",              "zumba",        "studio_a",   True,  day(5,10,0),  1.0, 20, None,       "Zumba cuối tuần không gian mở, năng động và vui"),
    ("Running + Cafe – Sáng Thứ Bảy","running",       "park",       False, day(5,6,30),  1.5, 10, None,       "Chạy bộ sáng thứ Bảy rồi ghé cafe cùng nhau"),
    ("Esports – LOL team practice",   "esports",      "pantry",     True,  day(5,14,0),  2.0, 10, None,       "Tập luyện team LOL thứ Bảy chiều, cải thiện coordination"),
    ("Slam Dunk – Basketball pickup", "football",     "san_bong",   False, day(5,14,0),  2.0, 10, None,       "Bóng rổ pickup game thứ Bảy, tất cả trình độ đều được chào đón"),

    # Sunday thêm
    ("Gym – Sunday Easy",             "gym",          "gym",        True,  day(6,8,30),  1.0, 8,  None,       "Tập nhẹ Chủ nhật, dãn cơ và cardio nhẹ chuẩn bị cho tuần mới"),
    ("Swimming – Sunday Laps",        "swimming",     "pool",       True,  day(6,10,0),  1.0, 8,  None,       "Bơi thư giãn Chủ nhật, không áp lực tốc độ hay khoảng cách"),
    ("Product Career Sharing",        "product",      "highland",   False, day(6,15,0),  2.0, 10, None,       "Chia sẻ về con đường product career và lời khuyên thực tế"),
    ("Zumba – Sunday Fiesta",         "zumba",        "studio_a",   True,  day(6,16,0),  1.0, 20, None,       "Lớp Zumba cuối tuần, kết thúc Chủ nhật với nhiều năng lượng"),
    ("Boxing – Sunday sparring",      "boxing",       "studio_b",   True,  day(6,10,0),  1.5, 8,  "Medium",   "Sparring nhẹ Chủ nhật, kỹ thuật là chính, không thi thố"),
    ("Cafe & English conversation",   "english",      "coffee_q7",  False, day(6,16,0),  2.0, 8,  None,       "Luyện tiếng Anh tự nhiên qua trò chuyện, không học thuộc lòng"),
    ("Neighborhood Walk & Coffee",    "coffee chat",  "park",       False, day(6,7,30),  1.5, 8,  None,       "Đi bộ quanh khu, ghé cafe nhỏ, nói chuyện thoải mái"),
]

def creator(i: int) -> int:
    return CREATORS[i % len(CREATORS)]

print(f"Seeding {len(ACTIVITIES)} activities...")
count = 0
for i, (title, atype, loc_key, is_on, start_dt, dur_h, limit, diff, desc) in enumerate(ACTIVITIES):
    loc = ON.get(loc_key) or OFF.get(loc_key) or loc_key
    loc_type = "on_campus" if is_on else "off_campus"
    c_id = creator(i)

    act = Activity(
        title=title,
        description=desc,
        activity_type=atype,
        source="user_created",
        location_type=loc_type,
        start_time=start_dt,
        end_time=end(start_dt, dur_h),
        location=loc,
        participant_limit=limit,
        current_participants=1,
        created_by=c_id,
        difficulty=diff,
        open_to="all",
        status="active",
    )
    db.add(act)
    db.flush()
    db.add(ActivityParticipant(activity_id=act.id, user_id=c_id))
    count += 1

db.commit()
print(f"✓ Seeded {count} activities successfully.")
db.close()
