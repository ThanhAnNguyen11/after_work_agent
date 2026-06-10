import sys
import os
from datetime import datetime

# Adjust Python path to resolve imports from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database import init_db, SessionLocal
from backend.app.models import User, Activity, FixedActivity, ActivityParticipant, Memory, RecommendationLog, UserExperience
from backend.app.org_utils import organization_distance, calculate_recommendation_score
from backend.app.agents.extraction import extract_activity_from_text
from backend.app.agents.graph import run_agent_flow

def test_org_distance():
    print("\n--- Testing Organization Distance Logic ---")
    db = SessionLocal()
    try:
        annt7 = db.query(User).filter(User.domain == "annt7").first()
        binhnd2 = db.query(User).filter(User.domain == "binhnd2").first()
        cuonglm = db.query(User).filter(User.domain == "cuonglm").first()
        duongnt = db.query(User).filter(User.domain == "duongnt").first()
        
        # Same Squad: annt7 (TEP/PCT/Consumer Solutions) & binhnd2 (TEP/PCT/Consumer Solutions) -> 1.0
        d_squad = organization_distance(annt7, binhnd2)
        print(f"Same Squad Closeness (annt7 <-> binhnd2): {d_squad} (Expected: 1.0)")
        assert d_squad == 1.0, f"Expected 1.0, got {d_squad}"
        
        # Same Department: annt7 (Consumer Solutions) & cuonglm (Data Platform) -> 0.8
        d_dept = organization_distance(annt7, cuonglm)
        print(f"Same Dept Closeness (annt7 <-> cuonglm): {d_dept} (Expected: 0.8)")
        assert d_dept == 0.8, f"Expected 0.8, got {d_dept}"
        
        # Cross Group: annt7 (TEP PCT) & duongnt (BIZ Partnership) -> 0.2
        d_cross = organization_distance(annt7, duongnt)
        print(f"Cross Group Closeness (annt7 <-> duongnt): {d_cross} (Expected: 0.2)")
        assert d_cross == 0.2, f"Expected 0.2, got {d_cross}"
        
        print("✅ Organization Distance checks passed.")
    finally:
        db.close()

def test_activity_extraction():
    print("\n--- Testing Activity Extraction Agent ---")
    text = "Football at 7PM. Need 3 more players."
    extracted = extract_activity_from_text(text)
    print(f"Input: '{text}'")
    print(f"Extracted: {extracted}")
    assert extracted["activity_type"] == "football", "Expected football"
    assert extracted["start_time"] == "19:00", "Expected 19:00 (7PM)"
    assert extracted["required_players"] == 3, "Expected 3 players"
    
    # Test swimming extraction
    swim_text = "Anyone down for swimming at 5PM? Need 4 more players."
    extracted_swim = extract_activity_from_text(swim_text)
    print(f"Input: '{swim_text}'")
    print(f"Extracted: {extracted_swim}")
    assert extracted_swim["activity_type"] == "swimming", "Expected swimming"
    assert extracted_swim["start_time"] == "17:00", "Expected 17:00 (5PM)"
    assert extracted_swim["required_players"] == 4, "Expected 4 players"
    
    print("✅ Extraction Agent checks passed.")

def test_recommendation_scoring():
    print("\n--- Testing Recommendation Scorer ---")
    db = SessionLocal()
    try:
        annt7 = db.query(User).filter(User.domain == "annt7").first()
        
        # Get history of annt7 (which is 5 gym sessions in seeding)
        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == annt7.id).all()
        hist_ids = [p.activity_id for p in p_records]
        history = db.query(Activity).filter(Activity.id.in_(hist_ids)).all() if hist_ids else []
        
        # Score football match
        fb_act = db.query(Activity).filter(Activity.activity_type == "football").first()
        fb_peers_records = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == fb_act.id).all()
        fb_peers = db.query(User).filter(User.id.in_([p.user_id for p in fb_peers_records])).all() if fb_peers_records else []
        fb_creator = db.query(User).filter(User.id == fb_act.created_by).first()
        
        fb_score = calculate_recommendation_score(
            user=annt7,
            activity_or_class=fb_act,
            user_history=history,
            participants=fb_peers,
            creator=fb_creator
        )
        print(f"Football Match Scores: {fb_score}")
        
        # Score Gym Class Yoga
        yoga_class = db.query(FixedActivity).filter(FixedActivity.class_name == "Yoga").first()
        yoga_score = calculate_recommendation_score(
            user=annt7,
            activity_or_class=yoga_class,
            user_history=history,
            participants=[],
            creator=None
        )
        print(f"Yoga Gym Class Scores: {yoga_score}")
        
        # Gym class relevance should be zeroed out in routine trap, and discovery score for football should be high
        assert yoga_score["activity_relevance"] == 0.0, "Gym class relevance should be zeroed out in a routine trap"
        assert fb_score["discovery_score"] > yoga_score["discovery_score"], "Football match should have higher discovery score"
        assert fb_score["final_score"] > yoga_score["final_score"], "Routine breaker should score higher than dominant category"
        
        print("✅ Recommendation Scoring checks passed.")
    finally:
        db.close()

def test_scenarios():
    print("\n--- Testing Core User Scenarios (Graph Flows) ---")
    
    # 1. Scenario 1: What should I do tonight?
    print("\nRunning Scenario 1: annt7 asking 'What should I do tonight?'")
    db = SessionLocal()
    annt7 = db.query(User).filter(User.domain == "annt7").first()
    db.close()
    
    response_1 = run_agent_flow(annt7.id, "What should I do tonight?")
    print(f"Response:\n{response_1}")
    assert "Football" in response_1 or "Yoga" in response_1 or "AI" in response_1, "Response should mention seeded options"
    
    # 2. Scenario 2: Football at 6PM. Need 2 more players.
    print("\nRunning Scenario 2: annt7 posting 'Badminton at 8PM. Need 2 more players.'")
    response_2 = run_agent_flow(annt7.id, "Badminton at 8PM. Need 2 more players.")
    print(f"Response:\n{response_2}")
    assert "Activity Created" in response_2, "Should confirm activity creation"
    
    # Check if DB has new badminton activity
    db = SessionLocal()
    badminton_act = db.query(Activity).filter(Activity.activity_type == "badminton").first()
    assert badminton_act is not None, "Badminton activity should be saved in SQLite"
    print(f"Saved Activity: {badminton_act.title} at {badminton_act.start_time} in {badminton_act.location}")
    
    # Check if host automatically joined
    host_joined = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == badminton_act.id,
        ActivityParticipant.user_id == annt7.id
    ).first()
    assert host_joined is not None, "Creator should be automatically registered as participant"
    db.close()

    # 3. Scenario 3: I am bored of going to the gym every day.
    print("\nRunning Scenario 3: annt7 saying 'I am bored of going to the gym every day.'")
    response_3 = run_agent_flow(annt7.id, "I am bored of going to the gym every day.")
    print(f"Response:\n{response_3}")
    assert "Football" in response_3 or "AI" in response_3, "Response should offer routine breakers"
    
    # Verify Reflection Agent saved memory
    db = SessionLocal()
    memories = db.query(Memory).filter(Memory.user_id == annt7.id).all()
    memory_contents = [m.content for m in memories]
    print(f"Saved Memories for annt7: {memory_contents}")
    assert any("bored" in m.lower() and "gym" in m.lower() for m in memory_contents), "Reflection Agent should record gym fatigue"
    db.close()

    # 4. Scenario 4: New Employee joins
    db = SessionLocal()
    minhhoang = db.query(User).filter(User.domain == "minhhoang").first()
    db.close()
    print("\nRunning Scenario 4: minhhoang (new hire) asking 'Recommend some activities'")
    response_4 = run_agent_flow(minhhoang.id, "I just joined, recommend some activities please")
    print(f"Response:\n{response_4}")
    assert len(response_4) > 10, "Response should generate recommendations for new employee"

    # 5. Scenario 5: Missing players candidate selection
    print("\nRunning Scenario 5: Finding matching candidates for missing players in football activity")
    db = SessionLocal()
    football_act = db.query(Activity).filter(Activity.activity_type == "football").first()
    assert football_act is not None
    
    from backend.app.main import get_activity_candidates
    candidates = get_activity_candidates(football_act.id, db)
    db.close()
    
    print("Candidates for Football Match:")
    for c in candidates:
        print(f"- {c['full_name']} (@{c['domain']}) | Score: {c['fit_score']} | Reasons: {c['reasons']}")
        
    candidate_domains = [c["domain"] for c in candidates]
    assert "annt7" in candidate_domains, "annt7 should be recommended as a candidate for the football match"
    print("✅ Scenario 5 verification checks passed.")

    # 6. Tomorrow Query Scenario Check
    print("\nRunning Tomorrow Query check: annt7 asking 'What should I do tomorrow?'")
    response_tomorrow = run_agent_flow(annt7.id, "What should I do tomorrow?")
    print(f"Response:\n{response_tomorrow}")
    assert "Yoga" in response_tomorrow, "Response should recommend Monday Yoga gym class"
    print("✅ Tomorrow Query verification checks passed.")

    # 7. Next Monday Query Scenario Check
    print("\nRunning Next Monday Query check: annt7 asking 'What should I do next Monday?'")
    response_monday = run_agent_flow(annt7.id, "What should I do next Monday?")
    print(f"Response:\n{response_monday}")
    assert "Yoga" in response_monday, "Response should recommend Monday Yoga gym class"
    print("✅ Next Monday Query verification checks passed.")

    print("\n✅ All 7 programmatic scenario verification runs succeeded!")

def test_feedback_loop():
    print("\n--- Testing Feedback Loop (Principles 10 & 12) ---")
    db = SessionLocal()
    try:
        annt7 = db.query(User).filter(User.domain == "annt7").first()
        activity = db.query(Activity).filter(Activity.activity_type == "football").first()
        
        from backend.app.main import log_recommendation, create_user_experience
        from backend.app.schemas import RecommendationLogCreate, UserExperienceCreate
        
        log_create = RecommendationLogCreate(user_id=annt7.id, activity_id=activity.id)
        log = log_recommendation(log_create, db)
        print(f"Logged Recommendation: ID={log.id}, Status={log.status}")
        assert log.status == "shown", "Expected status shown"
        
        exp_create = UserExperienceCreate(
            user_id=annt7.id,
            activity_id=activity.id,
            energy_rating=2,
            connections_made=3,
            notes="Extremely fun match, connected with PM Binh.",
            communities_enjoyed=["football"]
        )
        exp = create_user_experience(annt7.id, exp_create, db)
        print(f"Logged Experience: ID={exp.id}, Energy={exp.energy_rating}, Notes='{exp.notes}'")
        assert exp.energy_rating == 2, "Expected energy rating 2"
        assert exp.connections_made == 3, "Expected 3 connections"
        
        db.refresh(log)
        print(f"Recommendation Status after Experience entry: {log.status}")
        assert log.status == "joined", "Expected log status to update to joined automatically"
        
        print("✅ Feedback Loop checks passed.")
    finally:
        db.close()

def test_cold_start_and_behavioral_learning():
    print("\n--- Testing Cold Start and Behavioral Learning ---")
    db = SessionLocal()
    try:
        # Create a new user with NO history (Cold Start)
        new_user = User(
            domain="cold_start_user",
            full_name="Cold Start Test User",
            title="Junior Dev",
            company="PY",
            org_group="TEP",
            department="PCT"
        )
        new_user.interests = ["football"]
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Test Discovery note is indeed Cold Start
        from backend.app.agents.discovery import run_discovery_agent
        discovery_note = run_discovery_agent(new_user.full_name, new_user.interests, [])
        print(f"Discovery note for new user: '{discovery_note}'")
        assert "Cold Start" in discovery_note, "Expected Cold Start discovery note for new user"
        
        # Run recommendations for Cold Start user
        from backend.app.agents.graph import run_agent_flow
        response = run_agent_flow(new_user.id, "Recommend some activities")
        print(f"Cold Start recommendation response:\n{response}")
        assert "history" in response or "haven't participated" in response.lower() or "cold start" in response.lower(), "Should mention lack of history or cold start"
        
        # Check scoring weights for Cold Start: should rely purely on declared interest
        # Setup an activity matching declared interest (football)
        football_act = db.query(Activity).filter(Activity.activity_type == "football").first()
        from backend.app.org_utils import calculate_recommendation_score
        score_cold = calculate_recommendation_score(
            user=new_user,
            activity_or_class=football_act,
            user_history=[],
            db=db
        )
        print(f"Cold start interest match score: {score_cold['interest_match']}")
        assert score_cold['interest_match'] == 1.0, "Relevance should be purely declared interest match"
        
        # Now simulate 3 football participations to move out of Cold Start
        activities = db.query(Activity).all()
        for i in range(min(3, len(activities))):
            part = ActivityParticipant(activity_id=activities[i].id, user_id=new_user.id)
            db.add(part)
        db.commit()
        
        # Reload history
        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == new_user.id).all()
        hist_ids = [p.activity_id for p in p_records]
        history = db.query(Activity).filter(Activity.id.in_(hist_ids)).all()
        
        # Now run discovery note, should NOT be Cold Start since history count >= 3
        discovery_note_2 = run_discovery_agent(new_user.full_name, new_user.interests, history)
        print(f"Discovery note for user with history: '{discovery_note_2}'")
        assert "Cold Start" not in discovery_note_2, "Should not be Cold Start mode with 3+ activities"
        
        # Let's check scoring weights after 3 participations
        # Setup behavioral interest score (e.g. 0.8 for gym)
        from backend.app.models import UserBehavioralInterest
        beh_interest = UserBehavioralInterest(user_id=new_user.id, activity_type="gym", score=0.8)
        db.add(beh_interest)
        db.commit()
        
        # Calculate score for gym activity
        gym_class = db.query(FixedActivity).filter(FixedActivity.class_name == "Yoga").first() # gym class type is gym
        score_warm = calculate_recommendation_score(
            user=new_user,
            activity_or_class=gym_class,
            user_history=history,
            db=db
        )
        print(f"Warm interest match score: {score_warm['interest_match']}")
        assert score_warm['interest_match'] > 0.0, "Behavioral interest should influence the score when out of Cold Start"
        
        print("✅ Cold Start and Behavioral Learning tests passed.")
    finally:
        db.close()

def test_journal_prompting_and_feedback():
    print("\n--- Testing Journal Prompting and Feedback Loops ---")
    db = SessionLocal()
    try:
        from datetime import date
        # Create a test user
        user = User(
            domain="journal_user",
            full_name="Journal Test User",
            title="QA Engineer",
            company="PY",
            org_group="TEP",
            department="PCT"
        )
        user.interests = ["badminton"]
        db.add(user)
        db.commit()
        db.refresh(user)
        
        from backend.app.main import get_pending_journal_prompt, resolve_journal_prompt
        from backend.app.schemas import JournalResolveRequest
        
        # 1. Test target date calculation by mocking system time (via patch)
        from unittest.mock import patch
        
        # Test Case A: Time is 22:00 (Evening) -> Target Date should be today
        with patch('backend.app.main.get_current_time') as mock_get_time:
            mock_get_time.return_value = datetime(2026, 6, 8, 22, 0, 0)
            
            res = get_pending_journal_prompt(user.id, db)
            print(f"At 22:00 prompt response: prompt={res.prompt}, target_date={res.target_date}")
            assert res.prompt is True, "Prompt should be active at 22:00"
            assert res.target_date == date(2026, 6, 8), f"Expected target date 2026-06-08, got {res.target_date}"
            
        # Test Case B: Time is 09:00 (Next morning) -> Target Date should be yesterday
        with patch('backend.app.main.get_current_time') as mock_get_time:
            mock_get_time.return_value = datetime(2026, 6, 9, 9, 0, 0)
            
            res = get_pending_journal_prompt(user.id, db)
            print(f"At 09:00 prompt response: prompt={res.prompt}, target_date={res.target_date}")
            assert res.prompt is True, "Prompt should be active at 09:00"
            assert res.target_date == date(2026, 6, 8), f"Expected target date 2026-06-08, got {res.target_date}"
            
        # Test Case C: Time is 18:00 (Outside window) -> No prompt
        with patch('backend.app.main.get_current_time') as mock_get_time:
            mock_get_time.return_value = datetime(2026, 6, 8, 18, 0, 0)
            
            res = get_pending_journal_prompt(user.id, db)
            print(f"At 18:00 prompt response: prompt={res.prompt}")
            assert res.prompt is False, "Prompt should be inactive at 18:00"
            
        # 2. Test "Never Ask Twice" constraint by resolving / skipping
        target_date = date(2026, 6, 8)
        # Skip the prompt
        resolve_req = JournalResolveRequest(status="skipped")
        resolve_res = resolve_journal_prompt(user.id, resolve_req, target_date, db)
        print(f"Resolve skipped response: {resolve_res}")
        assert resolve_res["success"] is True
        
        # Now verify get_pending_journal_prompt returns prompt=False for that date
        with patch('backend.app.main.get_current_time') as mock_get_time:
            mock_get_time.return_value = datetime(2026, 6, 8, 22, 0, 0)
            
            res = get_pending_journal_prompt(user.id, db)
            print(f"After skipping, pending response: prompt={res.prompt}")
            assert res.prompt is False, "Should not prompt again after being skipped"
            
        # 3. Test dynamic score updates on activity resolution
        # Setup badminton activity
        badminton_act = db.query(Activity).filter(Activity.activity_type == "badminton").first()
        if not badminton_act:
            badminton_act = Activity(
                title="Badminton Session",
                activity_type="badminton",
                start_time=datetime(2026, 6, 9, 18, 0),
                location="Court A",
                created_by=user.id
            )
            db.add(badminton_act)
            db.commit()
            db.refresh(badminton_act)
            
        # Resolve user joining badminton
        target_date_new = date(2026, 6, 9)
        resolve_req_act = JournalResolveRequest(
            status="resolved_activity",
            activity_id=badminton_act.id
        )
        resolve_journal_prompt(user.id, resolve_req_act, target_date_new, db)
        
        # Verify user is added as participant
        p_record = db.query(ActivityParticipant).filter(
            ActivityParticipant.user_id == user.id,
            ActivityParticipant.activity_id == badminton_act.id
        ).first()
        assert p_record is not None, "User should be automatically registered as participant upon resolution"
        
        # Verify UserBehavioralInterest score is updated
        from backend.app.models import UserBehavioralInterest
        bi = db.query(UserBehavioralInterest).filter(
            UserBehavioralInterest.user_id == user.id,
            UserBehavioralInterest.activity_type == "badminton"
        ).first()
        assert bi is not None
        print(f"Updated badminton interest score: {bi.score}")
        assert bi.score == 0.3, f"Expected behavioral score 0.3, got {bi.score}"
        
        # Now resolve another activity and verify decay
        gym_class = db.query(FixedActivity).filter(FixedActivity.class_name == "Yoga").first()
        resolve_req_gym = JournalResolveRequest(
            status="resolved_activity",
            gym_class_id=gym_class.id
        )
        resolve_journal_prompt(user.id, resolve_req_gym, date(2026, 6, 10), db)
        
        # Badminton interest should be decayed: 0.3 * 0.8 = 0.24
        db.refresh(bi)
        print(f"Decayed badminton interest score: {bi.score}")
        assert abs(bi.score - 0.24) < 1e-5, f"Expected decayed score 0.24, got {bi.score}"
        
        # Gym interest score should be 0.3
        bi_gym = db.query(UserBehavioralInterest).filter(
            UserBehavioralInterest.user_id == user.id,
            UserBehavioralInterest.activity_type == "gym"
        ).first()
        assert bi_gym is not None
        print(f"Gym interest score: {bi_gym.score}")
        assert bi_gym.score == 0.3, f"Expected gym score 0.3, got {bi_gym.score}"
        
        print("✅ Journal prompting and feedback loop tests passed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def test_guidelines_notifications_and_capacity_locks():
    print("\n--- Testing Guidelines, Notifications, and Capacity Locks (Blueprint Requirements) ---")
    db = SessionLocal()
    try:
        from backend.app.main import create_activity, join_activity, list_user_notifications, mark_notification_as_read
        from backend.app.schemas import ActivityCreate, JoinActivityRequest
        
        # 1. Verify default guidelines mapping
        # Create user 1 (host)
        host = db.query(User).filter(User.domain == "binhnd2").first()
        # Create user 2 (joiner)
        joiner = db.query(User).filter(User.domain == "annt7").first()
        
        # Create a football activity without specifying guidelines
        act_in = ActivityCreate(
            title="Sunday Football Match",
            activity_type="football",
            start_time=datetime.now(),
            location="VNG Field 1",
            participant_limit=2
        )
        activity = create_activity(act_in, host.id, db)
        print(f"Created football activity with guidelines: '{activity.guidelines}'")
        assert "football shoes" in activity.guidelines.lower(), "Expected default football guidelines"
        assert activity.status == "active", "Expected activity status to be active on creation"
        
        # 2. Verify host notification creation upon user join
        # User joins the activity
        req = JoinActivityRequest(user_id=joiner.id)
        res = join_activity(activity.id, req, db)
        print(f"Join result: success={res.success}, message='{res.message}'")
        assert res.success is True, "Expected user to join successfully"
        
        # Verify host received a notification
        notifs = list_user_notifications(host.id, db)
        host_notif_msgs = [n.message for n in notifs]
        print(f"Host notifications: {host_notif_msgs}")
        assert any("joined your activity" in m for m in host_notif_msgs), "Expected host join notification"
        
        # Verify status became inactive because capacity is reached (limit = 2, host + joiner = 2)
        db.refresh(activity)
        print(f"Activity status after full capacity: {activity.status}")
        assert activity.status == "inactive", "Expected activity to become inactive when full"
        
        # Verify host received full notification
        notifs = list_user_notifications(host.id, db)
        host_notif_msgs = [n.message for n in notifs]
        print(f"Host notifications after full: {host_notif_msgs}")
        assert any("is now full" in m for m in host_notif_msgs), "Expected host 'full' notification"
        
        # Verify marking notifications as read
        unread_notifs = [n for n in notifs if not n.read]
        assert len(unread_notifs) > 0, "Expected unread notifications"
        unread_notif = unread_notifs[0]
        mark_res = mark_notification_as_read(unread_notif.id, db)
        assert mark_res["success"] is True
        
        db.refresh(unread_notif)
        assert unread_notif.read is True, "Expected notification to be marked as read"
        
        print("✅ Guidelines, notifications, and capacity locks checks passed.")
    finally:
        db.close()

def test_authentication_and_onboarding():
    print("\n--- Testing Authentication & Onboarding Flows ---")
    db = SessionLocal()
    try:
        from backend.app.main import login_user, onboard_user
        from backend.app.schemas import UserLoginRequest, UserOnboardRequest
        
        # 1. Test successful login of seeded user
        login_req = UserLoginRequest(domain="annt7", password="abc")
        login_res = login_user(login_req, db)
        print(f"Seeded login result: {login_res}")
        assert login_res.success is True
        assert login_res.is_onboarded is True
        
        # 2. Test failed login due to incorrect password
        failed_req = UserLoginRequest(domain="annt7", password="wrongpassword")
        failed_res = login_user(failed_req, db)
        print(f"Failed login result: {failed_res}")
        assert failed_res.success is False
        assert "password" in failed_res.message.lower()
        
        # 3. Test automatic creation on first login with is_onboarded=False
        new_user_req = UserLoginRequest(domain="new_hire_1", password="securepassword")
        new_user_res = login_user(new_user_req, db)
        print(f"New user first login result: {new_user_res}")
        assert new_user_res.success is True
        assert new_user_res.is_onboarded is False
        assert new_user_res.user_id is not None
        
        # Verify user exists in database but has is_onboarded=False
        db_user = db.query(User).filter(User.id == new_user_res.user_id).first()
        assert db_user is not None
        assert db_user.is_onboarded is False
        
        # 4. Test profile onboarding and update is_onboarded=True
        onboard_req = UserOnboardRequest(
            full_name="Alex Newhire",
            company="PY",
            org_group="TEP",
            department="PCT",
            squad="Consumer Solutions",
            interests=["football", "ai"]
        )
        onboard_res = onboard_user(new_user_res.user_id, onboard_req, db)
        print(f"Onboarding result full name: {onboard_res.full_name}")
        assert onboard_res.full_name == "Alex Newhire"
        
        # Check database directly
        db.refresh(db_user)
        assert db_user.is_onboarded is True
        assert db_user.company == "PY"
        assert "football" in db_user.interests
        
        print("✅ Authentication and Onboarding checks passed.")
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize DB first in a clean state
    from backend.app.database import engine
    from backend.app.models import Base
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    # Run Tests
    test_org_distance()
    test_activity_extraction()
    test_recommendation_scoring()
    test_scenarios()
    test_feedback_loop()
    test_cold_start_and_behavioral_learning()
    test_journal_prompting_and_feedback()
    test_guidelines_notifications_and_capacity_locks()
    test_authentication_and_onboarding()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

