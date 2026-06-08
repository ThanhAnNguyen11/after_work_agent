import sys
import os
from datetime import datetime

# Adjust Python path to resolve imports from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database import init_db, SessionLocal
from backend.app.models import User, Activity, GymClass, ActivityParticipant, Memory
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
        yoga_class = db.query(GymClass).filter(GymClass.class_name == "Yoga").first()
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
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
