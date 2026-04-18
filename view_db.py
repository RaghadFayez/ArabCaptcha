import sqlite3
import json

def view_database():
    conn = sqlite3.connect('arabcaptcha.db')
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("📋 LAST 5 SESSIONS (bot_score_initial vs final)")
    print("="*50)
    cursor.execute("""
        SELECT session_id, bot_score_initial, bot_score_final, risk_level, status 
        FROM site_session 
        ORDER BY session_created_at DESC 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if not rows:
         print("No sessions found yet.")
    for row in rows:
        print(f"Session: {row[0][:8]}... | Initial Score: {row[1]} | Final Score: {row[2]} | Risk: {row[3]} | Status: {row[4]}")
    
    print("\n" + "="*50)
    print("🎯 LAST 5 CHALLENGES (Difficulty Logic)")
    print("="*50)
    cursor.execute("""
        SELECT challenge_id, bot_score, difficulty, status, is_human_verified
        FROM challenge 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if not rows:
         print("No challenges found yet.")
    for row in rows:
        print(f"Challenge: {row[0][:8]}... | Score Used: {row[1]} | Difficulty Given: {row[2].upper()} | Passed: {row[4]}")
    
    print("\n" + "="*50)
    print("🕵️ LAST 3 BEHAVIOR LOGS (Passive/Active Signals)")
    print("="*50)
    cursor.execute("""
        SELECT log_id, event_type, signals_json 
        FROM behavior_log 
        ORDER BY timestamp DESC 
        LIMIT 3
    """)
    rows = cursor.fetchall()
    if not rows:
         print("No behavior logs found yet.")
    for idx, row in enumerate(rows):
        print(f"\n[{idx+1}] Event: {row[1]}")
        try:
            print(f"Signals:\n{json.dumps(json.loads(row[2]), indent=2, ensure_ascii=False)}")
        except:
             print(f"Signals: {row[2]}")
        
    conn.close()

if __name__ == "__main__":
    view_database()
