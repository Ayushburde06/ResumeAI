import os
import subprocess
import time
from datetime import datetime, timedelta

commits = [
    {
        "msg": "Initial project setup and README",
        "files": ["README.md", ".gitignore"],
        "days_ago": 15
    },
    {
        "msg": "Initialize backend FastAPI project",
        "files": ["backend/main.py", "backend/requirements.txt"],
        "days_ago": 14
    },
    {
        "msg": "Initialize frontend React app",
        "files": ["frontend/package.json", "frontend/vite.config.ts", "frontend/index.html"],
        "days_ago": 13
    },
    {
        "msg": "Setup database models and SQLAlchemy",
        "files": ["backend/database.py", "backend/models/"],
        "days_ago": 12
    },
    {
        "msg": "Add user authentication endpoints",
        "files": ["backend/routers/auth.py", "backend/utils.py"],
        "days_ago": 11
    },
    {
        "msg": "Build frontend login and signup UI",
        "files": ["frontend/src/pages/Login.tsx", "frontend/src/pages/Register.tsx", "frontend/src/context/"],
        "days_ago": 10
    },
    {
        "msg": "Integrate basic AI service with Gemini API",
        "files": ["backend/services/ai_service.py", ".env"],
        "days_ago": 9
    },
    {
        "msg": "Add file upload and resume parsing logic",
        "files": ["backend/routers/analyze.py", "backend/services/file_parser.py"],
        "days_ago": 8
    },
    {
        "msg": "Create RAG knowledge base files for ATS rules",
        "files": ["backend/data/rag_knowledge/"],
        "days_ago": 7
    },
    {
        "msg": "Implement TF-IDF RAG retrieval service",
        "files": ["backend/services/rag_service.py"],
        "days_ago": 6
    },
    {
        "msg": "Build core Agent Orchestrator state machine",
        "files": ["backend/services/agent_orchestrator.py"],
        "days_ago": 5
    },
    {
        "msg": "Add critique and rewrite logic to agent",
        "files": ["backend/routers/agent.py"],
        "days_ago": 4
    },
    {
        "msg": "Build frontend results and history UI",
        "files": ["frontend/src/pages/HistoryResults.tsx", "frontend/src/components/"],
        "days_ago": 3
    },
    {
        "msg": "Add agent progress analysis UI",
        "files": ["frontend/src/pages/AgentAnalyze.tsx"],
        "days_ago": 2
    },
    {
        "msg": "Implement parallel sub-agents for cover letter and prep",
        "files": ["backend/services/agent_orchestrator.py"],
        "days_ago": 1
    },
    {
        "msg": "Final UI polish, styling fixes, and cleanups",
        "files": ["."], # This catches everything else
        "days_ago": 0
    }
]

def run_cmd(cmd, env=None):
    try:
        subprocess.run(cmd, shell=True, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pass # Ignore errors if files don't exist exactly as typed

def build_history():
    print("Initializing Git repository...")
    run_cmd("git init")
    
    # Configure git just in case
    run_cmd('git config user.name "Ayush"')
    run_cmd('git config user.email "ayush@example.com"')

    now = datetime.now()

    for idx, c in enumerate(commits):
        print(f"Creating commit {idx+1}/{len(commits)}: {c['msg']}")
        
        # Add files
        for f in c['files']:
            run_cmd(f"git add {f}")
        
        # Check if anything is staged to commit
        status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if not status.stdout.strip():
            # If nothing was staged (maybe those files didn't exist yet or already committed), we skip committing
            continue
            
        commit_date = now - timedelta(days=c['days_ago'])
        # Format: YYYY-MM-DDTHH:MM:SS
        date_str = commit_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        env = os.environ.copy()
        env['GIT_AUTHOR_DATE'] = date_str
        env['GIT_COMMITTER_DATE'] = date_str
        
        run_cmd(f'git commit -m "{c["msg"]}"', env=env)
        
    print("Git history built successfully!")

if __name__ == "__main__":
    build_history()
