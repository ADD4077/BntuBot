from pathlib import Path

base_dir = Path(__file__).parent.parent
server_db_path = base_dir / "databases" / "server.db"
states_db_path = base_dir / "databases" / "states.db"
literature_per_faculty_json_path = base_dir / "books" / "literature_per_faculty.json"
events_path = base_dir / "student_events"
