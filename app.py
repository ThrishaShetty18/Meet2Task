import streamlit as st
import sqlite3
from datetime import datetime
from groq import Groq
import json
import plotly.graph_objects as go
import plotly.express as px
import requests

# Page config
st.set_page_config(
    page_title="Meet2Task AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database initialization
def init_db():
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            assignee TEXT,
            due_date TEXT,
            priority TEXT,
            difficulty TEXT,
            context TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Database functions
def save_tasks_to_db(tasks):
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    for task in tasks:
        # Get status from task, default to 'pending' if not specified
        status = task.get('status', 'pending')
        
        c.execute('''
            INSERT INTO tasks (task, assignee, due_date, priority, difficulty, context, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            task['task'],
            task['assignee'],
            task['due_date'],
            task['priority'],
            task['difficulty'],
            task['context'],
            status  # Use the status from AI extraction
        ))
    conn.commit()
    conn.close()

def load_tasks_from_db(status='pending'):
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', (status,))
    rows = c.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            'id': row[0],
            'task': row[1],
            'assignee': row[2],
            'due_date': row[3],
            'priority': row[4],
            'difficulty': row[5],
            'context': row[6],
            'status': row[7],
            'created_at': row[8]
        })
    return tasks

def complete_task_in_db(task_id):
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
    conn.commit()
    conn.close()

def delete_task_from_db(task_id):
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def get_all_tasks_from_db():
    conn = sqlite3.connect('meet2task.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            'id': row[0],
            'task': row[1],
            'assignee': row[2],
            'due_date': row[3],
            'priority': row[4],
            'difficulty': row[5],
            'context': row[6],
            'status': row[7],
            'created_at': row[8]
        })
    return tasks

# Initialize database
init_db()

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'tasks' not in st.session_state:
    st.session_state.tasks = load_tasks_from_db()
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    groq_api_key = st.text_input("Groq API Key", type="password", help="Get your API key from console.groq.com")
    
    st.divider()
    
    st.subheader("🐙 GitHub Settings")
    github_token = st.text_input("GitHub Token", type="password")
    repo_owner = st.text_input("Repository Owner", placeholder="username")
    repo_name = st.text_input("Repository Name", placeholder="repo-name")
    
    st.divider()
    
    # Task history
    st.subheader("📊 Task Statistics")
    all_tasks = get_all_tasks_from_db()
    pending_count = len([t for t in all_tasks if t['status'] == 'pending'])
    completed_count = len([t for t in all_tasks if t['status'] == 'completed'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pending", pending_count)
    with col2:
        st.metric("Completed", completed_count)
    
    if st.button("🗑️ Clear All History", type="secondary"):
        conn = sqlite3.connect('meet2task.db')
        c = conn.cursor()
        c.execute('DELETE FROM tasks')
        conn.commit()
        conn.close()
        st.session_state.tasks = []
        st.success("History cleared!")
        st.rerun()

# Enhanced Groq API function with completion detection
def extract_tasks_with_groq(transcript, api_key):
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Analyze this meeting transcript and extract actionable tasks in JSON format.
        
        CRITICAL: Detect task completion in the conversation.
        If someone explicitly states they "completed", "finished", "done", "already did", "pushed the fix", 
        "it's live", "deployed", or similar completion phrases about a task, set status to "completed".
        Otherwise, set status to "pending".
        
        For each task mentioned (whether completed or pending), provide:
        - task: Clear, actionable task description
        - assignee: Person responsible (extract from transcript)
        - due_date: Deadline mentioned (or "TBD")
        - priority: High/Medium/Low (infer from urgency)
        - difficulty: Easy/Medium/Hard (infer from context)
        - context: Brief context from the meeting
        - status: "completed" or "pending"
        
        Completion detection examples:
        ✅ "I finished the API endpoints this morning" → status: "completed"
        ✅ "Already fixed the CSS bugs on Monday" → status: "completed"
        ✅ "That's done and deployed" → status: "completed"
        ✅ "I pushed the fix yesterday" → status: "completed"
        ⏳ "I'll work on the documentation" → status: "pending"
        ⏳ "Still working on the homepage" → status: "pending"
        
        Transcript:
        {transcript}
        
        Return ONLY a valid JSON array. No markdown, no explanations.
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up markdown formatting
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        
        tasks = json.loads(result.strip())
        return tasks if isinstance(tasks, list) else []
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

# GitHub function
def create_github_issue(task, owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    labels = []
    if task['priority'] == 'High':
        labels.append('priority: high')
    elif task['priority'] == 'Medium':
        labels.append('priority: medium')
    else:
        labels.append('priority: low')
    
    data = {
        "title": task['task'],
        "body": f"**Assignee:** {task['assignee']}\n**Due Date:** {task['due_date']}\n**Priority:** {task['priority']}\n**Difficulty:** {task['difficulty']}\n\n**Context:**\n{task['context']}",
        "labels": labels
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Chart functions
def create_priority_chart(tasks):
    if not tasks:
        return None
    priority_counts = {}
    for task in tasks:
        priority = task['priority']
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(priority_counts.keys()),
        values=list(priority_counts.values()),
        hole=0.4,
        marker=dict(colors=['#ef4444', '#f59e0b', '#10b981'])
    )])
    fig.update_layout(title="Tasks by Priority", height=300)
    return fig

def create_assignee_chart(tasks):
    if not tasks:
        return None
    assignee_counts = {}
    for task in tasks:
        assignee = task['assignee']
        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    fig = go.Figure(data=[go.Bar(
        x=list(assignee_counts.keys()),
        y=list(assignee_counts.values()),
        marker_color='#8b5cf6'
    )])
    fig.update_layout(title="Tasks by Assignee", height=300)
    return fig

def create_difficulty_chart(tasks):
    if not tasks:
        return None
    difficulty_counts = {}
    for task in tasks:
        difficulty = task['difficulty']
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
    
    fig = go.Figure(data=[go.Bar(
        x=list(difficulty_counts.keys()),
        y=list(difficulty_counts.values()),
        marker_color='#06b6d4'
    )])
    fig.update_layout(title="Tasks by Difficulty", height=300)
    return fig

def create_timeline_chart(tasks):
    if not tasks:
        return None
    due_date_counts = {}
    for task in tasks:
        due_date = task['due_date']
        due_date_counts[due_date] = due_date_counts.get(due_date, 0) + 1
    
    fig = go.Figure(data=[go.Scatter(
        x=list(due_date_counts.keys()),
        y=list(due_date_counts.values()),
        mode='lines+markers',
        marker=dict(size=10, color='#ec4899')
    )])
    fig.update_layout(title="Tasks Timeline", height=300)
    return fig

# Main content
st.markdown("""
<style>
    @keyframes fadeIn {
        0% {
            opacity: 0;
            transform: translateY(-10px);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .big-title {
        font-size: 72px !important;
        font-weight: 700 !important;
        text-align: center !important;
        margin: 30px 0 10px 0 !important;
        line-height: 1.2 !important;
        color: #ffffff !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
        letter-spacing: -1px !important;
        animation: fadeIn 0.8s ease-out !important;
    }
    
    .subtitle {
        font-size: 18px !important;
        text-align: center !important;
        color: #94a3b8 !important;
        margin-bottom: 40px !important;
        font-weight: 400 !important;
        animation: fadeIn 1s ease-out !important;
    }
    
    /* Enhanced button styles */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Better text areas */
    .stTextArea textarea {
        border-radius: 8px !important;
        border: 2px solid #374151 !important;
        font-size: 14px !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Better tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
    }
    
    /* Better metrics */
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 700 !important;
    }
    
    /* Better expanders */
    .streamlit-expanderHeader {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Better dividers */
    hr {
        margin: 2rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, #374151, transparent) !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
    }
    
    /* Better input fields */
    .stTextInput input {
        border-radius: 8px !important;
        border: 2px solid #374151 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput input:focus {
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Better multiselect */
    .stMultiSelect [data-baseweb="tag"] {
        border-radius: 6px !important;
        background-color: #8b5cf6 !important;
    }
    
    /* Smooth scrollbar */
    ::-webkit-scrollbar {
        width: 10px !important;
        height: 10px !important;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e293b !important;
        border-radius: 10px !important;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #475569 !important;
        border-radius: 10px !important;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #64748b !important;
    }
    
    /* Success/Error/Warning messages */
    .stSuccess {
        border-radius: 8px !important;
        border-left: 4px solid #10b981 !important;
    }
    
    .stError {
        border-radius: 8px !important;
        border-left: 4px solid #ef4444 !important;
    }
    
    .stWarning {
        border-radius: 8px !important;
        border-left: 4px solid #f59e0b !important;
    }
    
    .stInfo {
        border-radius: 8px !important;
        border-left: 4px solid #3b82f6 !important;
    }
</style>

<div class="big-title">Meet2Task</div>
<div class="subtitle">AI-Powered Meeting Task Extraction</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Analyze", "✅ Pending Tasks", "🎉 Completed Tasks", "📊 Analytics", "🐙 GitHub"])

# Tab 1: Analyze
with tab1:
    st.markdown("### Meeting Transcript")
    
    transcript_input = st.text_area(
        "Transcript",
        height=300,
        placeholder="Paste your meeting transcript here...",
        value=st.session_state.transcript,
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        analyze_button = st.button("🤖 Analyze with AI", use_container_width=True, type="primary")
    
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_button:
        st.session_state.transcript = ""
        st.rerun()
    
    if analyze_button:
        if not transcript_input.strip():
            st.error("Please paste a transcript first")
        elif not groq_api_key:
            st.error("Please add your Groq API key in the sidebar")
        else:
            with st.spinner("Analyzing transcript..."):
                st.session_state.transcript = transcript_input
                tasks = extract_tasks_with_groq(transcript_input, groq_api_key)
                
                if tasks:
                    # Save to database
                    save_tasks_to_db(tasks)
                    # Reload from database
                    st.session_state.tasks = load_tasks_from_db()
                    st.session_state.analysis_done = True
                    
                    # Count completed vs pending
                    completed = len([t for t in tasks if t.get('status') == 'completed'])
                    pending = len([t for t in tasks if t.get('status') == 'pending'])
                    
                    st.success(f"✅ Extracted {len(tasks)} tasks: {completed} completed, {pending} pending")
                    st.rerun()
                else:
                    st.warning("No tasks found")

# Tab 2: Pending Tasks
with tab2:
    # Reload pending tasks from database
    pending_tasks = load_tasks_from_db(status='pending')
    
    if pending_tasks:
        st.subheader(f"⏳ {len(pending_tasks)} Pending Tasks")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            priority_filter = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium", "Low"], key="pending_priority")
        with col2:
            assignees = list(set(t['assignee'] for t in pending_tasks))
            assignee_filter = st.multiselect("Assignee", assignees, default=assignees, key="pending_assignee")
        with col3:
            difficulties = list(set(t['difficulty'] for t in pending_tasks))
            difficulty_filter = st.multiselect("Difficulty", difficulties, default=difficulties, key="pending_difficulty")
        
        # Filter tasks
        filtered_tasks = [
            t for t in pending_tasks
            if t['priority'] in priority_filter
            and t['assignee'] in assignee_filter
            and t['difficulty'] in difficulty_filter
        ]
        
        st.caption(f"Showing {len(filtered_tasks)} of {len(pending_tasks)} pending tasks")
        
        # Display tasks
        for task in filtered_tasks:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### {task['task']}")
                    st.markdown(f"**👤** {task['assignee']} • **📅** {task['due_date']} • **🎯** {task['priority']} • **💪** {task['difficulty']}")
                    with st.expander("Context"):
                        st.write(task['context'])
                        st.caption(f"Created: {task['created_at']}")
                
                with col2:
                    if st.button("✅", key=f"complete_{task['id']}", help="Mark as Complete"):
                        complete_task_in_db(task['id'])
                        st.success("Task completed!")
                        st.rerun()
                    
                    if st.button("🗑️", key=f"delete_{task['id']}", help="Delete Task"):
                        delete_task_from_db(task['id'])
                        st.warning("Task deleted")
                        st.rerun()
                
                st.divider()
    else:
        st.info("🎉 No pending tasks! All caught up.")

# Tab 3: Completed Tasks
with tab3:
    # Reload completed tasks from database
    completed_tasks = load_tasks_from_db(status='completed')
    
    if completed_tasks:
        st.subheader(f"🎉 {len(completed_tasks)} Completed Tasks")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            priority_filter_completed = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium", "Low"], key="completed_priority")
        with col2:
            assignees_completed = list(set(t['assignee'] for t in completed_tasks))
            assignee_filter_completed = st.multiselect("Assignee", assignees_completed, default=assignees_completed, key="completed_assignee")
        with col3:
            difficulties_completed = list(set(t['difficulty'] for t in completed_tasks))
            difficulty_filter_completed = st.multiselect("Difficulty", difficulties_completed, default=difficulties_completed, key="completed_difficulty")
        
        # Filter tasks
        filtered_completed = [
            t for t in completed_tasks
            if t['priority'] in priority_filter_completed
            and t['assignee'] in assignee_filter_completed
            and t['difficulty'] in difficulty_filter_completed
        ]
        
        st.caption(f"Showing {len(filtered_completed)} of {len(completed_tasks)} completed tasks")
        
        # Display completed tasks
        for task in filtered_completed:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### ~~{task['task']}~~ ✅")
                    st.markdown(f"**👤** {task['assignee']} • **📅** {task['due_date']} • **🎯** {task['priority']} • **💪** {task['difficulty']}")
                    with st.expander("Context"):
                        st.write(task['context'])
                        st.caption(f"Created: {task['created_at']}")
                
                with col2:
                    if st.button("🗑️", key=f"delete_completed_{task['id']}", help="Delete Task"):
                        delete_task_from_db(task['id'])
                        st.warning("Task deleted")
                        st.rerun()
                
                st.divider()
    else:
        st.info("No completed tasks yet. Start analyzing transcripts!")

# Tab 4: Analytics
with tab4:
    all_tasks_for_analytics = get_all_tasks_from_db()
    
    if all_tasks_for_analytics:
        st.subheader("📊 Analytics Dashboard")
        
        # Row 1: Priority and Assignee charts
        col1, col2 = st.columns(2)
        with col1:
            priority_fig = create_priority_chart(all_tasks_for_analytics)
            if priority_fig:
                st.plotly_chart(priority_fig, use_container_width=True)
        
        with col2:
            assignee_fig = create_assignee_chart(all_tasks_for_analytics)
            if assignee_fig:
                st.plotly_chart(assignee_fig, use_container_width=True)
        
        # Row 2: Difficulty and Timeline charts
        col3, col4 = st.columns(2)
        with col3:
            difficulty_fig = create_difficulty_chart(all_tasks_for_analytics)
            if difficulty_fig:
                st.plotly_chart(difficulty_fig, use_container_width=True)
        
        with col4:
            timeline_fig = create_timeline_chart(all_tasks_for_analytics)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
        
        # Summary metrics
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        pending_tasks_count = len([t for t in all_tasks_for_analytics if t['status'] == 'pending'])
        completed_tasks_count = len([t for t in all_tasks_for_analytics if t['status'] == 'completed'])
        
        with col1:
            st.metric("Total Tasks", len(all_tasks_for_analytics))
        with col2:
            st.metric("Completed", completed_tasks_count)
        with col3:
            high_priority = sum(1 for t in all_tasks_for_analytics if t['priority'] == 'High' and t['status'] == 'pending')
            st.metric("High Priority Pending", high_priority)
        with col4:
            unique_assignees = len(set(t['assignee'] for t in all_tasks_for_analytics))
            st.metric("Team Members", unique_assignees)
    else:
        st.info("No analytics available. Start analyzing transcripts!")

# Tab 5: GitHub
with tab5:
    st.subheader("🐙 GitHub Export")
    
    pending_tasks_for_github = load_tasks_from_db(status='pending')
    
    if not pending_tasks_for_github:
        st.info("No pending tasks to export")
    elif not all([github_token, repo_owner, repo_name]):
        st.warning("⚠️ Configure GitHub settings in sidebar to export tasks")
    else:
        st.write(f"**Repository:** `{repo_owner}/{repo_name}`")
        st.write(f"**Pending Tasks:** {len(pending_tasks_for_github)}")
        
        if st.button("🚀 Create GitHub Issues", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            failed_tasks = []
            
            for idx, task in enumerate(pending_tasks_for_github):
                try:
                    status_text.text(f"Creating issue {idx + 1}/{len(pending_tasks_for_github)}...")
                    result = create_github_issue(task, repo_owner, repo_name, github_token)
                    success_count += 1
                    st.success(f"✅ [{task['task']}]({result['html_url']})")
                except Exception as e:
                    failed_tasks.append((task, str(e)))
                    st.error(f"❌ {task['task']}: {str(e)}")
                
                progress_bar.progress((idx + 1) / len(pending_tasks_for_github))
            
            status_text.empty()
            progress_bar.empty()
            
            st.divider()
            st.success(f"✅ Created {success_count}/{len(pending_tasks_for_github)} issues")
            
            if failed_tasks:
                st.warning(f"⚠️ {len(failed_tasks)} failed")

# Footer
st.divider()
st.caption("Powered by Groq AI & GitHub API • Tasks stored in SQLite database • Auto-detects completed tasks")

