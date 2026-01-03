# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Local Setup

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Clone or navigate to project directory
```bash
cd /path/to/Popup_Service-main
```

### 3. Create virtual environment (recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate on Mac/Linux
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure environment variables
Create a `.env` file in the project root:
```bash
POTENS_API_KEY=your_actual_api_key_here
POTENS_API_URL=https://ai.potens.ai/api/chat
RESPONSE_TIMEOUT=30
```

### 6. Run the application
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### 7. Login
Use one of the default accounts:
- Admin: `admin` / `1234`
- Employee: `HS001` / `1234` (김산, 경영관리본부, 재경팀)
- Employee: `HS002` / `1234` (이하나, 연구개발본부, 연구1팀)
- Employee: `HS003` / `1234` (홍길동, 연구개발본부, 연구2팀)

### Database initialization
The database (`groupware.db`) is automatically initialized when running `app.py` for the first time. It executes `sql/schema.sql` and creates dummy data for employees and accounts.

## Architecture Overview

### Application Flow
- **Entry point**: `app.py` always redirects to `pages/0_Login.py` for authentication
- **Role-based routing**: After login, users are routed based on role:
  - `ADMIN` → `pages/admin.py`
  - `EMPLOYEE` → `pages/employee.py`

### Core Components

#### Authentication (`core/auth.py`, `service.py`)
- `login_account()`: Unified login function for both ADMIN and EMPLOYEE roles
- Password verification using hashed passwords stored in `accounts` table
- Session state tracks: `logged_in`, `role`, `employee_id`, `employee_info`

#### Database (`core/db.py`)
- SQLite database: `groupware.db`
- Connection management via `get_conn()` context manager
- `init_db()`: Creates schema from `sql/schema.sql` and seeds dummy data
- Tables: `notices`, `popups`, `employees`, `popup_logs`, `accounts`, `notice_files`

#### Summary Integration (`core/summary.py`)
- `summarize_notice()`: Calls POTENS.ai API to generate notice summaries
- Requires `POTENS_API_KEY` environment variable
- Prompt rules: 5-line max, extract actionable items, exclude contact info

#### File Attachments (`service.py`)
- `save_attachments()`: Saves uploaded files to `uploads/` directory with naming pattern: `{post_id}_{timestamp}_{filename}`
- `list_attachments()`: Retrieves file metadata from `notice_files` table
- `get_first_image_attachment()`: Returns first image for popup display

### Business Logic (`service.py`)

#### Notice Management
- `save_post()`: Creates notice with type ('중요' or '일반') and handles attachments
- `list_posts()`: Returns all notices ordered by `post_id DESC`
- `get_post_by_id()`: Retrieves notice details including attachments
- `increment_views()`: Increments view count on detail page access

#### Popup System
- `create_popup()`: Creates popup targeting specific departments/teams with CSV storage
- `get_latest_popup_for_employee()`: Polling function (5-second interval) that:
  1. Checks if employee already responded (via `popup_logs`)
  2. Matches employee department/team against popup targets
  3. Team targets take priority over department targets
  4. Returns popup with first image attachment if available

#### Employee Actions
- `confirm_popup_action()`: Logs confirmation with secondary confirmation step
- `ignore_popup_action()`: Decrements `ignore_remaining` counter and logs
- `log_chatbot_move()`: Records chatbot navigation from popup

### Key Design Patterns

#### Popup Targeting Logic
Popups use a hierarchical matching system:
1. If `target_teams` is specified → match by team only
2. If only `target_departments` is specified → match by department
3. If neither specified → no match (popup not sent)

#### Dialog Nesting Prevention
Streamlit's `st.dialog` does not support nesting. The summary dialog is triggered via session state (`st.session_state.show_summary_dialog`) and rendered separately from the main popup dialog.

#### Timestamp Format
All timestamps use epoch milliseconds (`int(time.time() * 1000)`) for consistency across the application.

#### CSV Storage for Multi-Select
Department and team targets are stored as comma-separated strings in the database, parsed with `_parse_csv()` helper function.

## Environment Variables

Required in `.env` file:
```
POTENS_API_KEY=your_api_key
POTENS_API_URL=https://ai.potens.ai/api/chat
RESPONSE_TIMEOUT=30
```

## Default Credentials

Configured in `core/db.py` seed data:
- Admin: `login_id=admin`, `password=1234`
- Employees: `login_id=HS001/HS002/HS003`, `password=1234`

## Known Limitations

- File uploads stored locally in `uploads/` directory - will be lost on Railway/cloud redeployments
- Popup polling uses 5-second interval with Streamlit autorefresh (not real-time WebSocket)
- SQLite database may have concurrency issues under heavy load
