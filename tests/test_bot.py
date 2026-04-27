import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "demo_secret_key"
DOMAIN = "http://localhost"

def test_scenario(name, signals, ref_answer="test", expected_risk="high"):
    print(f"\n=============================================")
    print(f"🕵️  Testing Scenario: {name}")
    print(f"=============================================")
    
    # Step 1: Initialize Session
    res = httpx.post(f"{BASE_URL}/sessions", json={
        "api_key": API_KEY,
        "domain": DOMAIN,
        "signals_json": json.dumps(signals)
    })
    session_data = res.json()
    session_id = session_data.get("session_id")
    
    print(f"[+] Initial Signals Sent: {json.dumps(signals)}")
    
    # Step 2: Request Challenge
    res = httpx.post(f"{BASE_URL}/challenges", json={
        "session_id": session_id
    })
    challenge_data = res.json()
    challenge_id = challenge_data.get("challenge_id")
    difficulty = challenge_data.get("difficulty")
    
    print(f"[+] Challenge Generated -> Difficulty: {difficulty.upper()}")
    
    # Step 3: Solve (simulate attempt)
    res = httpx.post(f"{BASE_URL}/challenges/{challenge_id}/solve", json={
        "ref_answer": ref_answer,
        "low_conf_answer": "test",
        "response_time_ms": signals.get("submit_time_ms", 5000),
        "signals_json": json.dumps(signals)
    })
    solve_data = res.json()
    
    # Let's see the final score assigned by the backend
    passed = solve_data.get("success")
    
    print(f"[+] Final Verdict -> Passed: {passed}")
    return session_id


if __name__ == "__main__":
    try:
        # Scenario 1: Normal Human
        human_signals = {
            "mouse_moves": 125,
            "scrolls": 5,
            "paste_used": False,
            "webdriver": False,
            "submit_time_ms": 6500, # 6.5 seconds
            "failed_attempts": 0
        }
        test_scenario("Normal Human (Slow, natural movements)", human_signals)
        
        # Scenario 2: Webdriver/Selenium Bot
        selenium_signals = {
            "mouse_moves": 0,
            "scrolls": 0,
            "paste_used": False,
            "webdriver": True, # The killer signal
            "submit_time_ms": 200, # superhuman speed
            "failed_attempts": 0
        }
        test_scenario("Selenium Bot (Automated, Webdriver=True)", selenium_signals)
        
        # Scenario 3: Human trying to cheat (Copy paste very fast)
        cheater_signals = {
            "mouse_moves": 2,
            "scrolls": 0,
            "paste_used": True, # Pasted answer
            "webdriver": False,
            "submit_time_ms": 400, # submitted in 400ms
            "failed_attempts": 0
        }
        test_scenario("Fast Cheater (Pasting text rapidly)", cheater_signals)

        print("\n✅ Simulation Complete. Run `python view_db.py` to see the final scores stored!")

    except Exception as e:
        print(f"Error connecting to server. Is it running? Details: {e}")
