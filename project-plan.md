# Personal Health Tracking System - Requirements & Implementation Plan

## Executive Summary

This document specifies a complete Ecological Momentary Assessment (EMA) system for personal health tracking. The system prompts the user throughout the day to capture behaviors and outcomes in real-time, integrates with Garmin wearables and Google Calendar, and uses LLMs to extract insights and correlations from the collected data.

**Core Architecture:** Smart server (Python on Linux) + web-based PWA client (Next.js)

**Key Technologies:**
- Backend: Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy (ORM), Alembic (migrations), Celery + Redis
- Frontend: Next.js 16, React, TypeScript, Progressive Web App
- LLM: Ollama with Gemma 3 (12B for accuracy, 1B for speed)
- Notifications: ntfy.sh push notifications
- Deployment: Docker Compose with nginx reverse proxy
- Integrations: Garmin Connect API (in progress), Google Calendar API (planned)

## Current Implementation Status (Updated 2025-11-28)

### ✅ Phase 1: Core Infrastructure (COMPLETED)
- [x] PostgreSQL database with all 11 tables
- [x] SQLAlchemy ORM models for all entities
- [x] Alembic migration system
- [x] FastAPI server with REST API
- [x] Docker Compose infrastructure (db, redis, api, celery-worker, celery-beat, pwa)
- [x] Pydantic schemas for validation
- [x] LLM integration service (Ollama with gemma3:12b/gemma3:1b)
- [x] Celery background tasks infrastructure
- [x] Test suite (49 passing tests)

### ✅ Phase 2: Client Application (COMPLETED - PWA instead of Android)
- [x] Next.js PWA with TypeScript
- [x] Quick log functionality for ad-hoc entries
- [x] Reminder response interface
- [x] History view (Recent Entries page)
- [x] Garmin data sync page
- [x] Schedule management page
- [x] Settings page
- [x] Progressive Web App capabilities
- [x] ntfy.sh push notifications (replace Android-specific notifications)
- [x] Docker-ized development and deployment

### 🔄 Phase 3: External Integrations (IN PROGRESS)
- [x] Garmin data models created
- [x] Garmin API endpoints implemented
- [x] Basic Garmin sync functionality
- [~] Garmin automated daily sync at 8:30 AM
- [ ] Google Calendar models created
- [ ] Google Calendar sync functionality
- [ ] Calendar-aware scheduling

### ⏳ Phase 4: Advanced Features (NOT STARTED)
- [ ] Iterative prompting with gap detection
- [ ] Response consolidation
- [ ] Analysis engine (correlations)
- [ ] Anomaly detection
- [ ] Insight generation
- [ ] Historical gap detection
- [ ] Promptfoo LLM evaluation setup

### 🚀 Deployment (COMPLETED)
- [x] Docker Compose for all services
- [x] Nginx reverse proxy (habitbot.lan)
- [x] Pi-hole DNS integration
- [x] LAN-accessible at https://habitbot.lan

---

## System Architecture

### High-Level Components (As Implemented)

```
┌─────────────────┐         ┌──────────────────────────┐
│  Web Browser    │◄────────┤  Docker Compose Stack    │
│  (PWA)          │  HTTPS  │  ┌────────────────────┐  │
│                 │  via    │  │  nginx (reverse    │  │
│  Mac/Mobile     │  nginx  │  │  proxy)            │  │
└─────────────────┘         │  └────────────────────┘  │
       ▲                    │           │              │
       │                    │           ▼              │
       │  ntfy.sh push      │  ┌────────────────────┐  │
       │  notifications     │  │  Next.js PWA       │  │
       └────────────────────┼──┤  (port 3000)       │  │
                            │  └────────────────────┘  │
                            │           │              │
                            │           ▼              │
                            │  ┌────────────────────┐  │
                            │  │  FastAPI Server    │  │
                            │  │  (port 8001)       │  │
                            │  └────────────────────┘  │
                            │           │              │
                            │           ▼              │
                            │  ┌────────────────────┐  │
                            │  │  PostgreSQL DB     │  │
                            │  │  (port 5434)       │  │
                            │  └────────────────────┘  │
                            │           │              │
                            │           ▼              │
                            │  ┌────────────────────┐  │
                            │  │  Redis             │  │
                            │  │  (port 6380)       │  │
                            │  └────────────────────┘  │
                            │           │              │
                            │           ▼              │
                            │  ┌────────────────────┐  │
                            │  │  Celery Workers    │  │
                            │  │  (worker + beat)   │  │
                            │  └────────────────────┘  │
                            └──────────────────────────┘
                                       │
                                       ▼
                             ┌─────────────────┐
                             │  Ollama LLM     │
                             │  (host.docker.  │
                             │   internal)     │
                             │  gemma3:12b/1b  │
                             └─────────────────┘
```

### Data Flow (As Implemented)

1. **Prompting Flow:**
   - Celery beat scheduler calculates next reminder time based on rules and configuration
   - Server sends notification via ntfy.sh to user's subscribed devices
   - User opens PWA at https://habitbot.lan
   - User responds to reminder via text input
   - Response sent to API immediately, processed in background by Celery worker

2. **Processing Flow (As Implemented):**
   - Server receives raw text response from PWA
   - Celery worker queues response for LLM processing
   - LLM service extracts structured data using Ollama + Gemma 3
   - Stores both raw text and structured JSON in responses table
   - Response marked as "completed" after successful processing
   - **Note:** Currently behaviors/outcomes tables are not being populated from responses (known issue)

3. **Analysis Flow (Planned - Not Yet Implemented):**
   - Daily job: Summarize data, flag anomalies
   - Weekly job: Run correlation analysis between behaviors and outcomes
   - Monthly job: Generate comprehensive insights report
   - Ad-hoc: Identify historical gaps and generate one-time follow-up questions

## Major Design Changes from Original Plan

### 1. PWA Instead of Native Android App
**Original Plan:** Native Android app with Kotlin + Jetpack Compose
**Implemented:** Next.js Progressive Web App

**Rationale:**
- Faster development iteration
- Works on all devices (Mac, iPhone, Android) without separate builds
- Can be accessed from any browser
- Still supports push notifications via ntfy.sh
- Eliminates Android-specific complications (Play Store, device testing, etc.)

### 2. Docker Compose Deployment
**Original Plan:** systemd services for server components
**Implemented:** Full Docker Compose stack with hot-reload

**Benefits:**
- Simplified deployment and dependency management
- Easy to tear down and rebuild
- Consistent environment across development and production
- All services orchestrated together

### 3. LLM Model Changes
**Original Plan:** Ollama with Gemma 2 32B
**Implemented:** Ollama with Gemma 3 12B (accuracy) and Gemma 3 1B (speed)

**Rationale:**
- Gemma 3 12B provides better accuracy than Gemma 2 32B with lower resource usage
- Gemma 3 1B for quick operations (category detection, simple prompts)
- More flexible model selection based on task requirements

### 4. ntfy.sh for Notifications
**Original Plan:** Direct Android push notifications
**Implemented:** ntfy.sh pub/sub notification service

**Benefits:**
- Works with any device (desktop, mobile)
- No Firebase/Google dependencies
- Simple HTTP API
- Supports multiple devices simultaneously
- User can subscribe from any ntfy client

### 5. nginx Reverse Proxy with Custom Domain
**Added:** nginx reverse proxy with SSL and custom LAN domain (habitbot.lan)

**Benefits:**
- Clean URL instead of IP:port
- SSL/TLS for secure connections (even on LAN)
- Professional user experience
- Integrates with Pi-hole for DNS

## Known Issues and Limitations

### Critical Issues
1. **Behaviors/Outcomes Not Being Created**
   - LLM extracts structured data and stores in `response_structured` JSONB field
   - Data is NOT being decomposed into separate `behaviors` and `outcomes` table rows
   - Recent Entries page only shows responses, not the extracted behaviors/outcomes
   - Impact: Cannot perform correlation analysis or insights generation until this is fixed

2. **Missing Response Submissions**
   - Some reminder responses may not be getting saved to database
   - Users report responding to reminders that don't appear in Recent Entries
   - Possible causes: Mobile app issue, API submission failure, or user confusion between "acknowledge" and "respond"

### Minor Issues
1. **Garmin Sync Not Fully Automated**
   - Scheduled sync at 8:30 AM exists but reliability not verified
   - Manual sync via UI works correctly
   - Sleep score data syncs successfully

2. **No Calendar Integration Yet**
   - Reminder scheduling doesn't check calendar availability
   - May send reminders during meetings

3. **Limited Error Handling in PWA**
   - Network errors may not be clearly communicated to user
   - Offline queue not implemented

### Technical Debt
1. **No Iterative Prompting**
   - System doesn't ask follow-up questions to fill gaps
   - Single-shot Q&A only

2. **No Analysis Engine**
   - Correlation analysis not implemented
   - Anomaly detection not implemented
   - Insight generation not implemented

3. **Limited Test Coverage**
   - 49 tests for backend
   - No frontend tests yet
   - No end-to-end tests

---

## Detailed Requirements

### 1. User Context & Configuration

**User Profile:**
- Name: [User configurable]
- Wake time: 6:30 AM (configurable)
- Sleep time: 10:30 PM (configurable)
- Screens off time: 9:00 PM (configurable)
- Bedtime reading: 10:00 PM (configurable)
- Timezone: System timezone

**Initial Configuration (`config.yaml`):**
```yaml
user:
  name: "User"
  timezone: "America/Los_Angeles"  # Auto-detect or configure
  
schedule:
  wake_time: "06:30"
  sleep_time: "22:30"
  screens_off: "21:00"
  bed_time: "22:00"
  
prompts:
  default_frequency: 4  # per day during waking hours
  min_interval_minutes: 120  # minimum 2 hours between prompts
  max_interval_minutes: 300  # maximum 5 hours between prompts
  reminder_intervals: [5, 10, 20]  # minutes for escalating reminders
  max_reminders: 3
  
categories:
  - name: "sleep"
    frequency_per_day: 1
    preferred_times: ["07:00"]
  - name: "nutrition"
    frequency_per_day: 4
  - name: "substances"
    frequency_per_day: 3
  - name: "physical_activity"
    frequency_per_day: 2
  - name: "mental_state"
    frequency_per_day: 4
  - name: "stress_anxiety"
    frequency_per_day: 4
  - name: "social_interaction"
    frequency_per_day: 2
  - name: "work_productivity"
    frequency_per_day: 2
  - name: "environment"
    frequency_per_day: 2
  - name: "physical_symptoms"
    frequency_per_day: 2
    
calendar:
  check_interval_minutes: 15
  buffer_before_minutes: 0  # future: add buffer time
  buffer_after_minutes: 0   # future: add buffer time
  
garmin:
  sync_interval_hours: 1
  data_points:
    - sleep_score
    - sleep_stages
    - stress_levels
    - body_battery
    - hrv
    - steps
    - resting_hr
    - active_minutes
    
llm:
  model: "gemma2:32b"
  max_retries: 5
  temperature: 0.3
  
server:
  host: "0.0.0.0"
  port: 8000
  lan_only: true
```

### 2. Category Framework

**10 Core Categories:**

1. **Sleep**
   - Duration (hours)
   - Quality (1-10 scale)
   - Timing (bedtime, wake time)
   - Interruptions (count, reason)
   - Dreams (boolean, description)
   - Garmin sleep score (auto-imported)
   - Sleep stages from Garmin (deep, light, REM, awake minutes)

2. **Nutrition**
   - Meals/snacks consumed
   - Timing
   - Quantity (with flexible units: cups, grams, servings, pieces, oz, ml)
   - Hydration (water intake)
   - Food type/description

3. **Substances**
   - Supplements (name, dosage, unit, timing)
   - Medications (name, dosage, unit, timing)
   - Caffeine (source, quantity, timing)
   - Alcohol (type, quantity, timing)
   - Other substances

4. **Physical Activity**
   - Exercise type
   - Duration (minutes)
   - Intensity (low/moderate/high or 1-10)
   - Steps (from Garmin)
   - Active minutes (from Garmin)
   - Movement quality (how body feels)

5. **Mental State**
   - Mood (1-10 scale)
   - Energy (1-10 scale)
   - Focus/concentration (1-10 scale)
   - Motivation (1-10 scale)
   - Mental clarity

6. **Stress/Anxiety**
   - Stress level (1-10 scale)
   - Anxiety level (1-10 scale)
   - Triggers (description)
   - Coping mechanisms used
   - Garmin stress levels (auto-imported)

7. **Social Interaction**
   - Who (person/group type)
   - Duration
   - Quality (1-10 scale)
   - Type (in-person, call, text, etc.)
   - Isolation feelings

8. **Work/Productivity**
   - Hours worked
   - Quality of work (1-10)
   - Satisfaction (1-10)
   - Cognitive load (1-10)
   - Tasks completed
   - Distractions

9. **Environment**
   - Location (home, office, outdoors, etc.)
   - Weather conditions
   - Noise level
   - Air quality perception
   - Light exposure (natural, artificial)
   - Temperature comfort

10. **Physical Symptoms**
    - Pain (location, intensity 1-10)
    - Discomfort (type, intensity)
    - Illness symptoms
    - Digestive issues
    - Headaches
    - Other bodily sensations

### 3. Prompting System

#### 3.1 Scheduling Algorithm

**Core Logic:**
```python
def calculate_next_prompt(user_config, calendar_events, category_history, garmin_data):
    """
    Calculate when the next prompt should occur.
    
    Factors considered:
    1. Time since last prompt (min/max intervals)
    2. Category coverage (ensure each category meets its frequency)
    3. Calendar availability (no meetings)
    4. Waking hours (6:30 AM - 10:30 PM)
    5. Screens off time (avoid after 9:00 PM unless critical)
    6. Historical patterns (user's typical response times)
    7. Garmin anomalies (unusual stress, poor sleep -> prompt sooner)
    """
    pass
```

**Scheduling Rules:**
- Default: 4 prompts per day during waking hours (6:30 AM - 10:30 PM)
- Minimum 2 hours between prompts
- Maximum 5 hours between prompts
- Avoid prompts after 9:00 PM (screens off time) unless category is critically overdue
- Never prompt during calendar events marked as "Busy"
- Check calendar 15 minutes before scheduled prompt to avoid conflicts

#### 3.2 Question Templates

**Dynamic Question Generation:**

Questions should include specific timestamps to replace "since last check-in":

```python
question_templates = {
    "sleep": [
        "How did you sleep last night? What time did you go to bed and wake up?",
        "Rate your sleep quality from 1-10. Any interruptions or dreams?"
    ],
    "nutrition": [
        "What have you eaten since {last_check_time}?",
        "Have you had anything to drink since {last_check_time}? How much water?"
    ],
    "substances": [
        "Have you taken any supplements, medications, or had caffeine/alcohol since {last_check_time}?",
        "Tell me about any substances you've consumed since {last_check_time} - include timing and dosage."
    ],
    "physical_activity": [
        "Have you exercised or been physically active since {last_check_time}?",
        "How has your body felt since {last_check_time}? Any movement or activity?"
    ],
    "mental_state": [
        "How are you feeling right now? Rate your mood and energy on a scale of 1-10.",
        "How's your focus and motivation at this moment?"
    ],
    "stress_anxiety": [
        "What's your stress level right now from 1-10?",
        "Are you feeling any anxiety? If so, what's triggering it?"
    ],
    "social_interaction": [
        "Have you interacted with anyone since {last_check_time}?",
        "Tell me about any social interactions since {last_check_time}."
    ],
    "work_productivity": [
        "How's your work going since {last_check_time}? Rate your productivity.",
        "What have you accomplished since {last_check_time}? How satisfied are you?"
    ],
    "environment": [
        "Where are you right now? How's the environment?",
        "Describe your surroundings - location, noise, lighting, comfort."
    ],
    "physical_symptoms": [
        "Are you experiencing any physical discomfort, pain, or symptoms?",
        "How is your body feeling? Any pain, digestive issues, or other symptoms?"
    ]
}
```

#### 3.3 Iterative Prompting

**Flow:**
1. User receives initial prompt with 1-3 questions covering due categories
2. User responds (via voice or text)
3. Server sends response to LLM for gap analysis
4. LLM identifies which categories were not addressed
5. Server sends batch of follow-up questions (one at a time to user)
6. User responds to each follow-up
7. After all follow-ups (max 5 additional questions), server consolidates all responses
8. LLM processes all responses together to create single structured output
9. Store in database

**Gap Detection Prompt:**
```
You are analyzing a user's response to health tracking questions.

Questions asked:
{questions}

User's responses:
{responses}

Required categories to cover: {due_categories}

Identify which categories were NOT addressed in the user's responses.
Return a JSON array of missing categories that need follow-up questions.

Example:
["nutrition", "substances", "physical_activity"]
```

**Consolidation Prompt:**
```
You are consolidating multiple responses from a user into a single structured record.

Questions and responses:
Q1: {question_1}
A1: {response_1}

Q2: {question_2}
A2: {response_2}

...

Extract all relevant information and create a single structured JSON output.
If the user mentioned something in response to Q1 that also answers Q2, include it in the appropriate category.
Avoid duplication and ensure all information is captured.
```

#### 3.4 Reminder System

**Escalation Pattern:**
- User receives prompt
- If no response after 5 minutes: Send first reminder (gentle notification)
- If no response after 10 more minutes: Send second reminder (persistent notification)
- If no response after 20 more minutes: Send final reminder (alarm-style)
- If still no response: Mark prompt as "missed" and calculate next prompt

**Reminder Implementation:**
- Android app tracks whether user has opened/responded to prompt
- Server receives acknowledgment when user opens prompt
- Server schedules reminder jobs based on acknowledgment status

### 4. Calendar Integration

#### 4.1 Google Calendar API Setup

**OAuth Scopes Required:**
- `https://www.googleapis.com/auth/calendar.readonly`

**Calendars to Monitor:**
- Personal Gmail calendar
- Work Gmail calendar (if separate account)

**Initial Setup Flow:**
1. User runs server setup script
2. Script opens browser for OAuth authentication
3. User grants access to both personal and work calendars
4. Credentials stored securely in `~/.config/ema-tracker/credentials.json`

#### 4.2 Meeting Interruption Rules

**Default Behavior:**
- Never prompt during events marked as "Busy"

**Future Enhancement (Stretch Goal):**
- Markdown file: `meeting_rules.md` that LLM can reference
- Example rules:
  ```markdown
  # Meeting Interruption Rules
  
  ## Never Interrupt
  - Meetings with "1:1" in title
  - Meetings with CEO, direct reports
  - Interviews
  - Client calls
  - Meetings marked "important" or "critical"
  
  ## Can Interrupt
  - Team standups (I'm usually half-listening)
  - All-hands meetings
  - Optional meetings
  - Social events
  
  ## Context
  - Weekly planning meetings: Can interrupt if < 5 people, not if presenting
  ```

**Implementation (Phase 2):**
- LLM analyzes event title, attendees, and description
- Checks against rules in `meeting_rules.md`
- Makes decision about whether to allow prompt
- User can provide feedback ("don't interrupt these again") which updates rules file

### 5. Garmin Integration

#### 5.1 Data Points to Import

**Sleep Data (synced once per day, morning):**
- Sleep score (0-100)
- Sleep stages: deep minutes, light minutes, REM minutes, awake minutes
- Sleep start time, sleep end time
- Interruptions count

**Continuous Data (synced hourly):**
- Stress levels (per hour or continuous if available)
- Body Battery (current and throughout day)
- HRV (if available)
- Resting heart rate (daily)
- Steps (cumulative)
- Active minutes (cumulative)
- Calories burned

#### 5.2 API Integration

**Library:** `garminconnect` (Python package)

**Setup:**
```python
from garminconnect import Garmin

# Login
client = Garmin(email, password)
client.login()

# Get data
sleep_data = client.get_sleep_data(date)
stress_data = client.get_stress_data(date)
steps = client.get_steps_data(date)
# etc.
```

**Sync Schedule:**
- Sleep data: 7:00 AM daily
- Activity data: Every hour
- Stress/HRV: Every hour

**Backfill Strategy:**
- On first run, import last 30 days of Garmin data
- Store in database with timestamps
- Use for initial pattern analysis

### 6. Data Schema

#### 6.1 Database: PostgreSQL

**Tables:**

**`users`**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    timezone VARCHAR(50),
    wake_time TIME,
    sleep_time TIME,
    screens_off_time TIME,
    bed_time TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`categories`**
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    frequency_per_day INTEGER DEFAULT 4,
    preferred_times TIME[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`prompts`**
```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    scheduled_time TIMESTAMP NOT NULL,
    sent_time TIMESTAMP,
    questions JSONB NOT NULL,  -- Array of question objects
    status VARCHAR(50), -- 'scheduled', 'sent', 'acknowledged', 'completed', 'missed'
    categories VARCHAR(100)[], -- Categories covered by this prompt
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_status (status)
);
```

**`responses`**
```sql
CREATE TABLE responses (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER REFERENCES prompts(id),
    user_id INTEGER REFERENCES users(id),
    question_text TEXT NOT NULL,
    response_text TEXT NOT NULL, -- Raw text from user
    response_structured JSONB, -- Structured extraction
    category VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50), -- 'pending', 'processing', 'completed', 'failed'
    processing_attempts INTEGER DEFAULT 0,
    INDEX idx_timestamp (timestamp),
    INDEX idx_category (category),
    INDEX idx_prompt (prompt_id)
);
```

**`behaviors`**
```sql
CREATE TABLE behaviors (
    id SERIAL PRIMARY KEY,
    response_id INTEGER REFERENCES responses(id),
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP NOT NULL,
    category VARCHAR(100) NOT NULL,
    behavior_type VARCHAR(100), -- e.g., 'meal', 'supplement', 'exercise'
    details JSONB NOT NULL, -- Flexible structure for each behavior type
    source VARCHAR(50), -- 'survey', 'garmin', 'manual'
    INDEX idx_timestamp (timestamp),
    INDEX idx_category (category),
    INDEX idx_behavior_type (behavior_type)
);
```

**`outcomes`**
```sql
CREATE TABLE outcomes (
    id SERIAL PRIMARY KEY,
    response_id INTEGER REFERENCES responses(id),
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP NOT NULL,
    outcome_type VARCHAR(100), -- e.g., 'mood', 'energy', 'stress'
    value NUMERIC, -- Numeric value if applicable (e.g., 1-10 scale)
    value_text VARCHAR(255), -- Text value if applicable
    details JSONB, -- Additional context
    source VARCHAR(50),
    INDEX idx_timestamp (timestamp),
    INDEX idx_outcome_type (outcome_type)
);
```

**`garmin_data`**
```sql
CREATE TABLE garmin_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    data_type VARCHAR(100), -- 'sleep', 'stress', 'steps', 'hrv', etc.
    timestamp TIMESTAMP NOT NULL,
    value NUMERIC,
    details JSONB, -- Full data structure from Garmin
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_data_type (data_type)
);
```

**`calendar_events`**
```sql
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_id VARCHAR(255) UNIQUE, -- Google Calendar event ID
    calendar_id VARCHAR(255), -- Which calendar (personal/work)
    title VARCHAR(500),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50), -- 'busy', 'free', 'tentative'
    can_interrupt BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_start_time (start_time),
    INDEX idx_end_time (end_time)
);
```

**`correlations`**
```sql
CREATE TABLE correlations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    behavior_pattern TEXT NOT NULL,
    outcome_pattern TEXT NOT NULL,
    correlation_strength NUMERIC, -- -1 to 1
    confidence_level NUMERIC, -- 0 to 1
    time_lag_hours INTEGER, -- Hours between behavior and outcome
    sample_size INTEGER, -- Number of data points
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB, -- Full analysis results
    INDEX idx_analysis_date (analysis_date)
);
```

**`insights`**
```sql
CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    insight_type VARCHAR(100), -- 'correlation', 'anomaly', 'pattern', 'recommendation'
    title VARCHAR(500),
    description TEXT,
    confidence NUMERIC, -- 0 to 1
    actionable BOOLEAN DEFAULT TRUE,
    categories VARCHAR(100)[],
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE,
    INDEX idx_generated_at (generated_at),
    INDEX idx_insight_type (insight_type)
);
```

**`historical_gaps`**
```sql
CREATE TABLE historical_gaps (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    category VARCHAR(100),
    time_period TSRANGE, -- Time range with gap
    gap_type VARCHAR(100), -- 'missing_data', 'incomplete_data', 'anomaly'
    priority INTEGER DEFAULT 5, -- 1-10, how important to fill
    follow_up_sent BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_priority (priority)
);
```

#### 6.2 Structured Data Examples

**Nutrition Response:**
```json
{
  "category": "nutrition",
  "items": [
    {
      "item": "coffee",
      "quantity": 2,
      "unit": "cups",
      "time": "08:15",
      "notes": "black, no sugar"
    },
    {
      "item": "scrambled eggs",
      "quantity": 3,
      "unit": "eggs",
      "time": "09:30"
    },
    {
      "item": "whole wheat toast",
      "quantity": 2,
      "unit": "slices",
      "time": "09:30"
    }
  ],
  "hydration": {
    "water": {
      "quantity": 32,
      "unit": "oz",
      "time_range": "08:00-12:00"
    }
  }
}
```

**Mental State Response:**
```json
{
  "category": "mental_state",
  "timestamp": "2024-11-22T14:30:00",
  "mood": {
    "value": 7,
    "scale": "1-10",
    "description": "feeling good, productive"
  },
  "energy": {
    "value": 8,
    "scale": "1-10"
  },
  "focus": {
    "value": 9,
    "scale": "1-10",
    "description": "very focused on coding task"
  },
  "motivation": {
    "value": 8,
    "scale": "1-10"
  }
}
```

**Substances Response:**
```json
{
  "category": "substances",
  "items": [
    {
      "type": "supplement",
      "name": "Vitamin D3",
      "quantity": 5000,
      "unit": "IU",
      "time": "07:00"
    },
    {
      "type": "supplement",
      "name": "Omega-3",
      "quantity": 2,
      "unit": "capsules",
      "time": "07:00"
    },
    {
      "type": "caffeine",
      "name": "coffee",
      "quantity": 200,
      "unit": "mg",
      "time": "08:15",
      "source": "brewed coffee, 2 cups"
    }
  ]
}
```

#### 6.3 Schema Validation

**JSON Schema Template:**
```python
response_schema = {
    "type": "object",
    "required": ["category", "timestamp"],
    "properties": {
        "category": {
            "type": "string",
            "enum": [
                "sleep", "nutrition", "substances", "physical_activity",
                "mental_state", "stress_anxiety", "social_interaction",
                "work_productivity", "environment", "physical_symptoms"
            ]
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        # Category-specific schemas defined per category
    }
}
```

**Validation Process:**
```python
def validate_and_extract(raw_text: str, question: str, max_retries: int = 5):
    """
    Use LLM to extract structured data from raw text.
    Validate against schema and retry if needed.
    """
    for attempt in range(max_retries):
        structured_data = llm_extract(raw_text, question)
        
        if validate_schema(structured_data):
            return structured_data
        else:
            # Include validation errors in next prompt
            error_feedback = get_validation_errors(structured_data)
            # Retry with feedback
    
    # After max retries, flag for manual review
    return {
        "status": "needs_manual_review",
        "raw_text": raw_text,
        "attempts": max_retries
    }
```

### 7. Android App Specification

#### 7.1 Technology Stack
- Language: Kotlin
- UI: Jetpack Compose
- Architecture: MVVM (Model-View-ViewModel)
- Local DB: Room (SQLite wrapper)
- Networking: Retrofit + OkHttp
- Dependency Injection: Hilt

#### 7.2 Core Features

**1. Prompt Display**
- Receive push notifications from server via WebSocket or polling
- Display full-screen activity that prevents dismissal without response
- Show one question at a time
- Support voice input (Android SpeechRecognizer) and text input
- Auto-send response to server when user submits

**2. Offline Queue**
- Store unanswered prompts locally when server unreachable
- Queue responses locally when offline
- Auto-sync when connection restored
- Show connection status indicator

**3. Settings**
- Server IP address configuration (LAN)
- Server port configuration
- Connection test button
- Notification preferences
- Voice input language settings

**4. History View** (Optional Phase 2)
- View past prompts and responses
- Edit/correct responses if needed
- Manual entry for missed prompts

#### 7.3 Notification Strategy

**Importance Level: HIGH**
- Bypass Do Not Disturb mode
- Use notification channel with maximum priority
- Full-screen intent to force user attention

**Notification Content:**
- Title: "Time to check in"
- Body: Preview of first question
- Action: "Answer Now" (opens full-screen activity)
- No dismiss option on first notification

**Reminders:**
- Escalating importance with each reminder
- Final reminder uses alarm-style notification with sound/vibration

#### 7.4 UI Mockup

```
┌────────────────────────────────┐
│  EMA Health Tracker            │
│                                │
│  [Status: Connected]           │
│                                │
│  ┌──────────────────────────┐ │
│  │ Current Question:        │ │
│  │                          │ │
│  │ How are you feeling      │ │
│  │ right now? Rate your     │ │
│  │ mood and energy on a     │ │
│  │ scale of 1-10.           │ │
│  │                          │ │
│  └──────────────────────────┘ │
│                                │
│  ┌──────────────────────────┐ │
│  │ [Your Response Here]     │ │
│  │                          │ │
│  │ (Tap to type or speak)   │ │
│  └──────────────────────────┘ │
│                                │
│  [🎤 Voice Input]  [Submit]   │
│                                │
│  Question 1 of 1               │
│                                │
└────────────────────────────────┘
```

### 8. Server Implementation

#### 8.1 Technology Stack
- Framework: FastAPI (async Python web framework)
- Database: PostgreSQL with SQLAlchemy ORM
- Migrations: Alembic
- Task Queue: Celery with Redis (for background jobs)
- LLM: Ollama with Gemma 2 32B
- Calendar: Google Calendar API (google-api-python-client)
- Garmin: garminconnect library

**SQLAlchemy Setup Example:**

`database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`models/base.py`:
```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

`models/__init__.py`:
```python
# Import all models here for Alembic autogenerate
from models.base import Base
from models.user import User
from models.prompt import Prompt
from models.response import Response
from models.behavior import Behavior
from models.outcome import Outcome
from models.garmin import GarminData
from models.calendar import CalendarEvent
from models.correlation import Correlation
from models.insight import Insight
from models.gap import HistoricalGap

__all__ = [
    "Base",
    "User",
    "Prompt",
    "Response",
    "Behavior",
    "Outcome",
    "GarminData",
    "CalendarEvent",
    "Correlation",
    "Insight",
    "HistoricalGap",
]
```

`models/user.py` example:
```python
from sqlalchemy import Column, Integer, String, Time, TIMESTAMP
from sqlalchemy.sql import func
from models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    timezone = Column(String(50))
    wake_time = Column(Time)
    sleep_time = Column(Time)
    screens_off_time = Column(Time)
    bed_time = Column(Time)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
```

**Alembic Configuration:**

`alembic/env.py` (key sections):
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models
from models import Base
from config import get_settings

# this is the Alembic Config object
config = context.config

# Set sqlalchemy.url from settings
settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

# Set target_metadata for autogenerate
target_metadata = Base.metadata

# ... rest of env.py
```

#### 8.2 API Endpoints

**Authentication:**
- Simple API key-based auth for LAN-only deployment
- API key stored in Android app config

**Core Endpoints:**

```
POST /api/v1/register-device
- Register Android app with server
- Returns device ID and API key

GET /api/v1/prompts/next
- Get next scheduled prompt for user
- Returns question(s) and prompt ID

POST /api/v1/responses
- Submit response to prompt
- Body: { prompt_id, question_id, response_text, timestamp }
- Returns: { status, next_question_id (if follow-up) }

GET /api/v1/responses/{response_id}
- Get a specific response

POST /api/v1/responses/{response_id}/acknowledge
- Acknowledge that user opened prompt (stops reminders)

GET /api/v1/calendar/check
- Check if user is available (not in meeting)

GET /api/v1/garmin/sync
- Trigger manual Garmin data sync

GET /api/v1/insights/latest
- Get latest insights and recommendations

GET /api/v1/config
- Get user configuration (wake/sleep times, etc.)

POST /api/v1/config
- Update user configuration

WebSocket: /ws/prompts
- Real-time prompt delivery to connected devices
```

#### 8.3 Background Jobs (Celery Tasks)

**Scheduler Job (runs every 5 minutes):**
```python
@celery.task
def calculate_next_prompts():
    """
    Calculate when next prompts should be sent.
    Schedule prompt jobs accordingly.
    """
    users = get_active_users()
    for user in users:
        if should_send_prompt(user):
            schedule_prompt.delay(user.id)
```

**Send Prompt Job:**
```python
@celery.task
def send_prompt(user_id):
    """
    Send prompt to user's device.
    Schedule reminder jobs if not acknowledged.
    """
    prompt = create_prompt_for_user(user_id)
    send_to_device(user_id, prompt)
    schedule_reminders(prompt.id, [5, 10, 20])
```

**Process Response Job:**
```python
@celery.task
def process_response(response_id):
    """
    Extract structured data from raw text response.
    Validate and store in database.
    """
    response = get_response(response_id)
    structured = extract_structured_data(response.response_text)
    validate_and_save(response_id, structured)
    check_for_gaps(response)
```

**Garmin Sync Job (runs hourly):**
```python
@celery.task
def sync_garmin_data():
    """
    Sync Garmin data for all users.
    """
    users = get_users_with_garmin()
    for user in users:
        sync_user_garmin_data(user)
```

**Calendar Sync Job (runs every 15 minutes):**
```python
@celery.task
def sync_calendar_events():
    """
    Sync upcoming calendar events.
    Update availability status.
    """
    users = get_users_with_calendar()
    for user in users:
        sync_user_calendar(user)
```

**Analysis Jobs:**

Daily (runs at 1:00 AM):
```python
@celery.task
def daily_analysis():
    """
    Generate daily summary and identify anomalies.
    """
    users = get_active_users()
    for user in users:
        analyze_daily_data(user)
        detect_anomalies(user)
        identify_gaps(user)
```

Weekly (runs Sunday at 2:00 AM):
```python
@celery.task
def weekly_analysis():
    """
    Run correlation analysis.
    Generate insights.
    """
    users = get_active_users()
    for user in users:
        analyze_correlations(user)
        generate_insights(user)
```

Monthly (runs 1st of month at 3:00 AM):
```python
@celery.task
def monthly_analysis():
    """
    Generate comprehensive report.
    Suggest habit experiments.
    """
    users = get_active_users()
    for user in users:
        generate_monthly_report(user)
        suggest_experiments(user)
```

**Historical Gap Detection (runs daily):**
```python
@celery.task
def detect_historical_gaps():
    """
    Identify gaps in historical data.
    Generate one-time follow-up questions.
    """
    users = get_active_users()
    for user in users:
        gaps = identify_data_gaps(user)
        for gap in gaps:
            if gap.priority > 7:  # High priority gaps
                create_followup_prompt(user, gap)
```

### 9. LLM Integration (Ollama + Gemma 2 32B)

#### 9.1 Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Gemma 2 32B model
ollama pull gemma2:32b

# Verify
ollama run gemma2:32b "Hello, test"
```

#### 9.2 Extraction Prompts

**System Prompt:**
```
You are a health data extraction assistant. Your job is to extract structured information from conversational user responses about their health, behaviors, and experiences.

Extract data according to the schema provided. Be precise with numbers, times, and units. If information is missing or unclear, mark it as null or omit it.

Always return valid JSON that matches the schema exactly.
```

**Extraction Prompt Template:**
```
Question asked: {question}

User's response: {response_text}

Expected category: {category}

Extract structured data according to this schema:
{schema}

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown.

If the user's response also contains information about other categories beyond what was asked, include that information in additional category objects.

Example:
Question: "What have you eaten since 2:30 PM?"
Response: "I had a protein shake at 3 and went for a run at 4"

Output:
{{
  "responses": [
    {{
      "category": "nutrition",
      "timestamp": "2024-11-22T15:00:00",
      "items": [
        {{
          "item": "protein shake",
          "quantity": 1,
          "unit": "serving",
          "time": "15:00"
        }}
      ]
    }},
    {{
      "category": "physical_activity",
      "timestamp": "2024-11-22T16:00:00",
      "items": [
        {{
          "activity": "running",
          "duration": null,
          "time": "16:00"
        }}
      ]
    }}
  ]
}}
```

**Gap Detection Prompt:**
```
You are analyzing a user's responses to identify missing information.

Questions asked in this session:
{questions}

User's responses:
{responses}

Required categories to cover in this session:
{required_categories}

Analyze the responses and identify which required categories were NOT adequately addressed.

Return a JSON object:
{{
  "missing_categories": ["category1", "category2"],
  "follow_up_questions": [
    {{
      "category": "category1",
      "question": "Specific follow-up question for category1"
    }},
    {{
      "category": "category2",
      "question": "Specific follow-up question for category2"
    }}
  ]
}}
```

**Consolidation Prompt:**
```
You are consolidating multiple responses from the same user session into a single structured record.

Session context:
- Time: {session_time}
- Duration: {session_duration}

All questions and responses:
{qa_pairs}

Consolidate all information into a single structured output. If the user mentioned something in one response that also answers a later question, include it once in the appropriate category. Avoid duplication.

Return a comprehensive JSON object with all extracted information organized by category.
```

#### 9.3 Python LLM Client

```python
import requests
import json
from jsonschema import validate, ValidationError

class OllamaClient:
    def __init__(self, model="gemma2:32b", temperature=0.3):
        self.base_url = "http://localhost:11434"
        self.model = model
        self.temperature = temperature
    
    def generate(self, prompt, system_prompt=None):
        """Generate response from Ollama."""
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data
        )
        
        return response.json()["response"]
    
    def extract_structured_data(
        self, 
        response_text: str, 
        question: str, 
        category: str, 
        schema: dict,
        max_retries: int = 5
    ):
        """
        Extract structured data with schema validation and retries.
        """
        system_prompt = """You are a health data extraction assistant. 
        Extract structured information from user responses. 
        Return ONLY valid JSON matching the schema."""
        
        prompt = f"""
Question asked: {question}
User's response: {response_text}
Expected category: {category}
Schema: {json.dumps(schema, indent=2)}

Extract structured data as valid JSON matching the schema exactly.
"""
        
        for attempt in range(max_retries):
            try:
                # Generate response
                llm_output = self.generate(prompt, system_prompt)
                
                # Parse JSON
                # Remove markdown code blocks if present
                json_text = llm_output.strip()
                if json_text.startswith("```"):
                    json_text = json_text.split("```")[1]
                    if json_text.startswith("json"):
                        json_text = json_text[4:]
                json_text = json_text.strip()
                
                structured_data = json.loads(json_text)
                
                # Validate against schema
                validate(instance=structured_data, schema=schema)
                
                return {
                    "status": "success",
                    "data": structured_data,
                    "attempts": attempt + 1
                }
                
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt < max_retries - 1:
                    # Add error feedback to prompt for next attempt
                    prompt += f"\n\nPrevious attempt failed: {str(e)}\nTry again with valid JSON."
                else:
                    # Max retries reached
                    return {
                        "status": "needs_manual_review",
                        "error": str(e),
                        "raw_llm_output": llm_output,
                        "attempts": max_retries
                    }
        
        return {
            "status": "failed",
            "attempts": max_retries
        }
```

### 9.4 LLM Evaluation with Promptfoo

**Purpose:** Use promptfoo to systematically evaluate and improve LLM extraction quality.

**Setup:**
```bash
# Install promptfoo
npm install -g promptfoo

# Initialize in project
promptfoo init
```

**Evaluation Configuration (`promptfooconfig.yaml`):**
```yaml
description: "EMA Health Tracking - LLM Extraction Evaluation"

providers:
  - id: ollama:gemma3:12b
    config:
      temperature: 0.3
  - id: ollama:gemma3:1b  # Faster model for testing
    config:
      temperature: 0.3

prompts:
  - file://prompts/extraction/nutrition.txt
  - file://prompts/extraction/sleep.txt
  - file://prompts/extraction/mental_state.txt
  - file://prompts/extraction/substances.txt

tests:
  # Nutrition extraction tests
  - vars:
      response_text: "I had two eggs scrambled with cheese and toast around 8am"
      question_text: "What have you eaten today?"
      category: "nutrition"
    assert:
      - type: contains-json
      - type: javascript
        value: "output.items && output.items.length >= 2"
      - type: javascript
        value: "output.items.some(i => i.item.toLowerCase().includes('egg'))"

  # Sleep extraction tests
  - vars:
      response_text: "Slept about 7 hours, went to bed at 11pm, woke at 6am. Quality 6/10."
      question_text: "How did you sleep last night?"
      category: "sleep"
    assert:
      - type: contains-json
      - type: javascript
        value: "output.duration === 7 || output.data.duration === 7"
      - type: javascript
        value: "output.quality >= 5 && output.quality <= 7"

  # Mental state extraction tests
  - vars:
      response_text: "Feeling pretty good, maybe 7 out of 10. Tired but decent mood."
      question_text: "How are you feeling right now?"
      category: "mental_state"
    assert:
      - type: contains-json
      - type: javascript
        value: "output.mood >= 6 && output.mood <= 8"

  # Edge cases
  - vars:
      response_text: "nothing really"
      question_text: "What have you eaten?"
      category: "nutrition"
    assert:
      - type: contains-json
      - type: javascript
        value: "output.items.length === 0 || output.summary.toLowerCase().includes('nothing')"
```

**Prompt Templates (`prompts/extraction/nutrition.txt`):**
```
You are a health data extraction assistant.

Question: {{question_text}}
User Response: {{response_text}}
Category: {{category}}

Extract structured data as JSON. Include:
- items: array of food items with name, quantity, unit, time
- hydration: water intake if mentioned
- summary: brief text summary

Return ONLY valid JSON.
```

**Running Evaluations:**
```bash
# Run all tests
promptfoo eval

# Run with specific provider
promptfoo eval --providers ollama:gemma3:12b

# Generate comparison report
promptfoo eval --output results.json
promptfoo view results.json

# Compare models
promptfoo eval --providers "ollama:gemma3:12b,ollama:gemma3:1b" --compare
```

**Evaluation Metrics:**
- **Accuracy:** Does extraction capture correct data?
- **Completeness:** Are all mentioned items extracted?
- **Schema Compliance:** Does output match expected JSON schema?
- **Robustness:** Does it handle edge cases (typos, incomplete info)?
- **Latency:** How fast is extraction?

**CI Integration:**
```yaml
# .github/workflows/llm-eval.yml
name: LLM Evaluation
on:
  push:
    paths:
      - 'prompts/**'
      - 'src/services/llm.py'
jobs:
  eval:
    runs-on: self-hosted  # Needs Ollama
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g promptfoo
      - run: promptfoo eval --output results.json
      - run: promptfoo eval --output results.json --assertions-only
```

**Iteration Process:**
1. Run baseline evaluation
2. Identify failing test cases
3. Improve prompts or add examples
4. Re-run evaluation
5. Track improvements over time

### 10. Analysis Engine

#### 10.1 Correlation Analysis

**Algorithm:**
```python
def analyze_correlations(user_id, time_window_days=30):
    """
    Analyze correlations between behaviors and outcomes.
    """
    # Get all behaviors and outcomes in time window
    behaviors = get_behaviors(user_id, days=time_window_days)
    outcomes = get_outcomes(user_id, days=time_window_days)
    
    correlations = []
    
    # For each behavior type
    for behavior_type in get_behavior_types(behaviors):
        # For each outcome type
        for outcome_type in get_outcome_types(outcomes):
            # Test different time lags (0-48 hours)
            for lag_hours in [0, 2, 4, 6, 12, 24, 48]:
                corr = calculate_correlation(
                    behaviors, 
                    behavior_type, 
                    outcomes, 
                    outcome_type, 
                    lag_hours
                )
                
                if abs(corr.strength) > 0.3 and corr.p_value < 0.05:
                    correlations.append({
                        "behavior": behavior_type,
                        "outcome": outcome_type,
                        "correlation": corr.strength,
                        "p_value": corr.p_value,
                        "lag_hours": lag_hours,
                        "sample_size": corr.n
                    })
    
    return correlations

def calculate_correlation(behaviors, behavior_type, outcomes, outcome_type, lag_hours):
    """
    Calculate correlation with time lag.
    """
    # Align behavior times with outcome times (shifted by lag)
    aligned_data = align_timeseries(behaviors, outcomes, lag_hours)
    
    # Calculate Pearson correlation
    from scipy.stats import pearsonr
    corr, p_value = pearsonr(
        aligned_data.behavior_values,
        aligned_data.outcome_values
    )
    
    return CorrelationResult(
        strength=corr,
        p_value=p_value,
        n=len(aligned_data)
    )
```

#### 10.2 Insight Generation

**Use LLM to generate natural language insights:**

```python
def generate_insights(user_id, correlations, garmin_data, recent_data):
    """
    Use LLM to generate actionable insights from correlation data.
    """
    prompt = f"""
You are a health data analyst reviewing personal health tracking data.

Correlations found:
{json.dumps(correlations, indent=2)}

Recent Garmin data summary:
{json.dumps(garmin_data, indent=2)}

Recent behavior and outcome data:
{json.dumps(recent_data, indent=2)}

Generate 3-5 actionable insights for the user. For each insight:
1. Describe the pattern or correlation found
2. Explain the potential mechanism (if reasonable)
3. Suggest a specific, testable action
4. Estimate confidence level (low/medium/high)

Focus on:
- Strong correlations (>0.5)
- Patterns that appear consistently
- Actionable changes the user can make
- Avoid over-interpreting weak signals

Format as JSON:
{{
  "insights": [
    {{
      "title": "Brief title",
      "description": "Full description",
      "recommendation": "Specific action to try",
      "confidence": "medium",
      "categories": ["category1", "category2"]
    }}
  ]
}}
"""
    
    llm_response = ollama_client.generate(prompt)
    insights = json.loads(llm_response)
    
    # Store insights in database
    for insight in insights["insights"]:
        save_insight(user_id, insight)
    
    return insights
```

**Example Insights:**

```json
{
  "insights": [
    {
      "title": "Caffeine timing affects sleep quality",
      "description": "Data shows caffeine consumption after 2 PM correlates with lower sleep scores (r=-0.62, p<0.01). On days when you avoided afternoon caffeine, your average sleep score was 78 vs 65 on days with afternoon caffeine.",
      "recommendation": "Try limiting caffeine intake to before 2 PM for 2 weeks and monitor sleep quality.",
      "confidence": "high",
      "categories": ["substances", "sleep"]
    },
    {
      "title": "Morning exercise boosts same-day energy",
      "description": "Exercise completed before 10 AM correlates with higher reported energy levels throughout the day (r=0.54). Average energy rating: 7.8 on exercise days vs 6.2 on non-exercise days.",
      "recommendation": "Consider scheduling workouts in the morning when possible to maximize energy benefits.",
      "confidence": "medium",
      "categories": ["physical_activity", "mental_state"]
    },
    {
      "title": "Hydration gap in afternoons",
      "description": "Water intake tends to drop between 2-5 PM, corresponding with decreased focus scores. This pattern appears consistently across the past month.",
      "recommendation": "Set a reminder to drink water at 2 PM and 4 PM daily.",
      "confidence": "medium",
      "categories": ["nutrition", "mental_state"]
    }
  ]
}
```

#### 10.3 Anomaly Detection

```python
def detect_anomalies(user_id, days=7):
    """
    Identify unusual patterns in recent data.
    """
    # Get baseline statistics from historical data
    baseline = get_baseline_stats(user_id, days=30)
    
    # Get recent data
    recent = get_recent_data(user_id, days=days)
    
    anomalies = []
    
    # Check for statistical anomalies (>2 std dev from mean)
    for metric in ["mood", "energy", "sleep_score", "stress"]:
        recent_mean = recent[metric].mean()
        baseline_mean = baseline[metric].mean()
        baseline_std = baseline[metric].std()
        
        if abs(recent_mean - baseline_mean) > 2 * baseline_std:
            anomalies.append({
                "metric": metric,
                "recent_value": recent_mean,
                "baseline_value": baseline_mean,
                "deviation": abs(recent_mean - baseline_mean) / baseline_std,
                "severity": "high" if deviation > 3 else "medium"
            })
    
    # Check Garmin anomalies
    garmin_anomalies = detect_garmin_anomalies(user_id, days)
    anomalies.extend(garmin_anomalies)
    
    return anomalies
```

#### 10.4 Historical Gap Detection

```python
def identify_data_gaps(user_id, lookback_days=30):
    """
    Identify periods or categories with missing or incomplete data.
    """
    gaps = []
    
    # Check each category
    for category in ALL_CATEGORIES:
        expected_frequency = get_category_frequency(category)
        actual_responses = count_responses(user_id, category, lookback_days)
        expected_responses = expected_frequency * lookback_days
        
        if actual_responses < expected_responses * 0.5:  # Less than 50% coverage
            gaps.append({
                "category": category,
                "expected": expected_responses,
                "actual": actual_responses,
                "coverage": actual_responses / expected_responses,
                "priority": calculate_gap_priority(category, actual_responses),
                "time_period": f"Last {lookback_days} days"
            })
    
    # Check for time periods with no data
    date_ranges = get_date_ranges_with_no_data(user_id, lookback_days)
    for date_range in date_ranges:
        gaps.append({
            "type": "temporal_gap",
            "start": date_range.start,
            "end": date_range.end,
            "priority": 8,  # High priority for temporal gaps
            "categories": "all"
        })
    
    return sorted(gaps, key=lambda x: x["priority"], reverse=True)

def calculate_gap_priority(category, actual_responses):
    """
    Calculate priority for filling a gap (1-10 scale).
    """
    # Critical categories get higher priority
    critical_categories = ["sleep", "mental_state", "stress_anxiety"]
    
    if category in critical_categories:
        base_priority = 8
    else:
        base_priority = 5
    
    # Adjust based on how sparse the data is
    if actual_responses == 0:
        return 10  # No data at all - highest priority
    elif actual_responses < 5:
        return base_priority + 2
    else:
        return base_priority
```

### 11. Future Enhancements (Stretch Goals)

#### 11.1 Natural Language Commands

**Feature:** Allow user to speak commands to modify system behavior.

**Examples:**
- "Stop asking me about social interaction so frequently"
- "Add a new question about my back pain"
- "Don't prompt me during my morning routine before 8 AM"
- "I want to track my reading time"

**Implementation:**
```python
@app.post("/api/v1/commands")
def process_natural_language_command(command: str):
    """
    Process natural language command from user.
    Use LLM to understand intent and generate code change.
    Execute via Claude Code (local instance).
    """
    # Analyze command with LLM
    intent = analyze_command_intent(command)
    
    # Generate code change
    code_change = generate_code_change(intent)
    
    # Store in pending_changes table for review
    change_id = store_pending_change(command, intent, code_change)
    
    return {
        "change_id": change_id,
        "intent": intent,
        "description": "Code change generated and pending review",
        "preview": code_change.summary
    }
```

**Storage:**
- Store commands in `user_commands` table
- Store generated code changes in markdown file: `pending_changes.md`
- User can review and approve via web interface (future)

#### 11.2 Experiment Tracking

**Feature:** System suggests experiments to test hypotheses.

**Example:**
System notices: "Coffee after 2 PM correlates with worse sleep"
Suggestion: "Run a 2-week experiment: avoid caffeine after 2 PM and track sleep quality"

**Implementation:**
- Track experiment start/end dates
- Flag data during experiment period
- Analyze results automatically at end of experiment
- Present findings to user

#### 11.3 Meeting Interruption Learning

**Feature:** Learn over time which meetings can be interrupted.

**Implementation:**
- User provides feedback after each prompt: "This was fine" vs "Bad timing"
- Store feedback with meeting context (title, attendees, time of day)
- Update `meeting_rules.md` with learned patterns
- LLM references rules file when deciding whether to prompt

---

## Implementation Plan (Updated)

### ✅ Phase 1: Core Infrastructure (COMPLETED)

**Database & Server Setup**
- [x] Set up PostgreSQL database (via Docker Compose)
- [x] Create `database.py` with SQLAlchemy engine and session
- [x] Create all SQLAlchemy ORM models in `models/`
- [x] Initialize Alembic and configure migrations
- [x] Generate and run initial migration
- [x] Set up FastAPI server with REST API endpoints
- [x] Set up Redis and Celery for background jobs
- [x] Create configuration system with environment variables

**LLM Integration**
- [x] Install and configure Ollama with Gemma 3 models (12B and 1B)
- [x] Create LLM client wrapper class (`services/llm.py`)
- [x] Implement structured data extraction
- [x] Write extraction prompts for categories
- [x] Test extraction with sample responses

**Basic Prompting System**
- [x] Implement reminder scheduling algorithm
- [x] Create API endpoints for reminders and responses
- [x] Implement ntfy.sh notification integration
- [x] Test end-to-end: schedule → notify → respond → process

### ✅ Phase 2: Client Application (COMPLETED - PWA)

**PWA Foundation**
- [x] Create Next.js 16 project with TypeScript
- [x] Set up Docker container for PWA
- [x] Create basic UI pages (home, history, garmin, schedule, settings)
- [x] Implement API client library (`lib/api.ts`)
- [x] Integrate with FastAPI backend

**Features**
- [x] Quick log functionality for ad-hoc entries
- [x] Reminder response interface
- [x] Recent Entries history view
- [x] Garmin data sync page
- [x] Settings configuration
- [x] Responsive design for mobile and desktop

**Deployment**
- [x] Docker Compose orchestration
- [x] nginx reverse proxy setup
- [x] SSL/TLS with self-signed certificates
- [x] Custom domain (habitbot.lan) with Pi-hole DNS

### 🔄 Phase 3: External Integrations (IN PROGRESS)

**Garmin Integration**
- [x] Set up Garmin Connect library (garminconnect)
- [x] Create Garmin data models
- [x] Implement Garmin API endpoints
- [x] Create manual sync functionality
- [x] Implement automated daily sync (8:30 AM)
- [~] Backfill historical data (partially working)
- [~] Verify reliability of automated sync
- [ ] Add more Garmin metrics (HRV, body battery, stress)

**Google Calendar**
- [x] Calendar event model created
- [ ] Set up Google Calendar API credentials
- [ ] Implement OAuth flow for calendar access
- [ ] Create calendar sync background job
- [ ] Implement availability checking in scheduler
- [ ] Test: reminders avoid meetings

**Smart Scheduling**
- [x] Basic time-based scheduling algorithm
- [ ] Enhance with calendar awareness
- [ ] Add Garmin data as input (sleep quality, stress)
- [ ] Implement category-specific frequency tracking
- [ ] Test: system respects all constraints

### ⏳ Phase 4: Advanced Features (NOT STARTED)

**Fix Critical Issues First**
- [ ] Implement behaviors/outcomes table population from responses
- [ ] Investigate and fix missing response submissions
- [ ] Add proper error handling throughout PWA

**Iterative Prompting**
- [ ] Implement gap detection with LLM
- [ ] Create follow-up question generation
- [ ] Implement response consolidation
- [ ] Test: system asks follow-ups appropriately

**Analysis Engine**
- [ ] Implement daily summary job
- [ ] Implement anomaly detection
- [ ] Implement correlation analysis (time-series alignment)
- [ ] Create insight generation with LLM
- [ ] Store and display insights in UI

**Historical Gap Detection**
- [ ] Implement gap detection algorithm
- [ ] Create priority scoring system
- [ ] Generate one-time follow-up questions
- [ ] Add UI to show and respond to gap-filling prompts

### 🎯 Phase 5: Testing & Documentation (PARTIALLY COMPLETE)

**Testing**
- [x] Backend unit tests (49 tests)
- [ ] Frontend component tests
- [ ] End-to-end tests
- [ ] Integration tests for Garmin/Calendar
- [ ] Performance testing (LLM latency, database queries)

**Documentation**
- [x] README with setup instructions
- [x] Docker Compose documentation
- [ ] API endpoint documentation (OpenAPI/Swagger)
- [ ] Architecture decision records
- [ ] Troubleshooting guide
- [ ] User guide for PWA

## Next Steps (Priority Order)

### Immediate Priorities (Critical for MVP)

1. **Fix Behaviors/Outcomes Population** (CRITICAL)
   - Implement service to decompose `response_structured` JSONB into behaviors/outcomes tables
   - Add celery task to process responses after LLM extraction
   - Update Recent Entries page to show behaviors/outcomes instead of raw responses
   - **Impact:** Enables all downstream features (correlations, insights, visualization)

2. **Investigate Missing Response Submissions** (HIGH)
   - Add comprehensive logging to response submission flow
   - Check if issue is in PWA, API, or database layer
   - Verify ntfy notification → PWA interaction flow
   - Add retry mechanism for failed submissions

3. **Verify Garmin Auto-Sync Reliability** (MEDIUM)
   - Monitor 8:30 AM sync for several days
   - Add logging and error handling
   - Create alerts if sync fails
   - Backfill any missing historical data

### Short-Term Features (Weeks 1-2)

4. **Complete Google Calendar Integration**
   - Set up OAuth2 credentials
   - Implement calendar sync
   - Update scheduler to check calendar before sending reminders

5. **Improve PWA User Experience**
   - Add loading states and error messages
   - Implement offline queue for responses
   - Add success confirmations
   - Improve mobile responsiveness

6. **Enhanced Scheduling**
   - Add category-specific frequency tracking
   - Use Garmin sleep data to avoid reminders after poor sleep
   - Smart spacing of reminders throughout the day

### Medium-Term Features (Weeks 3-6)

7. **Analysis Engine v1**
   - Basic correlation analysis (caffeine → sleep, exercise → mood)
   - Simple anomaly detection (unusual sleep, stress spikes)
   - LLM-generated insights with confidence scores

8. **Historical Gap Detection**
   - Identify missing data periods
   - Generate follow-up questions
   - Prioritize critical categories (sleep, mental state)

9. **Iterative Prompting**
   - Gap detection after initial response
   - Follow-up questions for incomplete answers
   - Response consolidation

### Long-Term Enhancements (Months 2-3+)

10. **Experiment Tracking System**
    - A/B testing framework for habits
    - Automatic result analysis
    - Recommendation generation

11. **Advanced Visualization**
    - Time-series charts for all metrics
    - Correlation heatmaps
    - Trend analysis graphs
    - Export to PDF reports

12. **Natural Language Commands**
    - LLM-powered configuration changes
    - "Stop asking me about X so often"
    - Dynamic question creation

---

## Module Breakdown (As Implemented)

### Backend (Python/FastAPI)

```
habit-bot/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration management
│   ├── database.py                # SQLAlchemy engine and session setup
│   ├── celery_app.py             # Celery application configuration
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── reminder.py           # (renamed from prompt.py)
│   │   ├── response.py
│   │   ├── behavior.py
│   │   ├── outcome.py
│   │   ├── garmin_data.py
│   │   ├── calendar_event.py
│   │   ├── correlation.py
│   │   ├── insight.py
│   │   ├── historical_gap.py
│   │   ├── category.py
│   │   ├── summary.py
│   │   └── mixins.py             # Soft delete functionality
│   ├── api/                       # API endpoint routers
│   │   ├── __init__.py
│   │   ├── reminders.py
│   │   ├── responses.py
│   │   ├── quicklog.py           # Ad-hoc entry creation
│   │   ├── garmin.py
│   │   ├── categories.py
│   │   ├── users.py
│   │   ├── health.py             # Health check endpoint
│   │   ├── llm.py                # LLM test endpoints
│   │   ├── notifications.py      # ntfy integration
│   │   └── summaries.py
│   ├── services/                  # Business logic
│   │   ├── llm.py                # LLM extraction & generation
│   │   ├── garmin.py             # Garmin Connect integration
│   │   └── notifications.py      # ntfy.sh service
│   ├── tasks/                     # Celery background tasks
│   │   ├── reminder_tasks.py     # Scheduling and sending
│   │   ├── llm_tasks.py          # Response processing
│   │   └── garmin_tasks.py       # Data sync
│   └── schemas/                   # Pydantic schemas
│       ├── reminder.py
│       ├── response.py
│       ├── garmin.py
│       └── user.py
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
├── tests/                         # Pytest test suite
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # API container build
├── pyproject.toml               # uv project configuration
└── .env                         # Environment variables
```

### Frontend (Next.js PWA)

```
web/
├── src/
│   ├── app/                      # Next.js 16 app router
│   │   ├── page.tsx             # Home page (Recent Entries)
│   │   ├── layout.tsx           # Root layout
│   │   ├── globals.css
│   │   ├── reminder/            # Reminder response page
│   │   │   └── [id]/page.tsx
│   │   ├── history/             # Response history
│   │   │   └── page.tsx
│   │   ├── garmin/              # Garmin data display
│   │   │   └── page.tsx
│   │   ├── schedule/            # Reminder schedule view
│   │   │   └── page.tsx
│   │   └── settings/            # User settings
│   │       └── page.tsx
│   └── lib/
│       └── api.ts               # API client library
├── public/                       # Static assets
├── Dockerfile                   # PWA container build
├── package.json
└── next.config.ts
```

### Infrastructure

```
├── docker-compose.yml           # Orchestrates all services
├── nginx/
│   └── sites-available/
│       └── habitbot.lan         # Reverse proxy config
└── .env                         # Environment configuration
```

**Containers:**
- `db` - PostgreSQL database (port 5434)
- `redis` - Redis for Celery (port 6380)
- `api` - FastAPI backend (port 8001)
- `celery-worker` - Background task processor
- `celery-beat` - Task scheduler
- `pwa` - Next.js PWA (port 3000)
- `db-test` - Test database (port 5435)

---

## Setup Instructions

### Prerequisites

**Linux Server:**
- Ubuntu 22.04 or later
- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Ollama
- At least 16GB RAM (for Gemma 2 32B)
- 100GB disk space

**Android Development:**
- Android Studio Hedgehog or later
- Android SDK 34+
- Physical Android device (API 30+) for testing

### Server Setup

```bash
# 1. Install dependencies
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql redis-server

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma2:32b

# 3. Create project directory
mkdir -p ~/ema-tracker
cd ~/ema-tracker

# 4. Clone or create project
# (project files will be generated by implementation)

# 5. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 6. Install Python dependencies
pip install -r requirements.txt

# 7. Set up PostgreSQL
sudo -u postgres psql
CREATE DATABASE ema_tracker;
CREATE USER ema_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ema_tracker TO ema_user;
\q

# 8. Configure environment
cp .env.example .env
# Edit .env with database credentials, API keys, etc.

# 9. Initialize Alembic and run migrations
alembic init alembic
# Edit alembic.ini to set sqlalchemy.url
# Edit alembic/env.py to import your models
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# 10. Set up Google Calendar API
# Follow Google Calendar API setup guide
# Download credentials.json to ~/.config/ema-tracker/

# 11. Set up Garmin credentials
# Store Garmin email/password in config (encrypted)

# 12. Start services
# Terminal 1: FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Celery worker
celery -A tasks.celery worker --loglevel=info

# Terminal 3: Celery beat (scheduler)
celery -A tasks.celery beat --loglevel=info
```

### Android App Setup

```bash
# 1. Open Android Studio
# 2. Open ema-android project
# 3. Sync Gradle
# 4. Configure server IP in app/src/main/res/values/config.xml
# 5. Build APK: Build > Build Bundle(s) / APK(s) > Build APK(s)
# 6. Install on phone: adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## Configuration Examples

### config.yaml

```yaml
user:
  name: "User"
  timezone: "America/Los_Angeles"
  
schedule:
  wake_time: "06:30"
  sleep_time: "22:30"
  screens_off: "21:00"
  bed_time: "22:00"
  
prompts:
  default_frequency: 4
  min_interval_minutes: 120
  max_interval_minutes: 300
  reminder_intervals: [5, 10, 20]
  max_reminders: 3
  
categories:
  - name: "sleep"
    frequency_per_day: 1
    preferred_times: ["07:00"]
  - name: "nutrition"
    frequency_per_day: 4
  - name: "substances"
    frequency_per_day: 3
  - name: "physical_activity"
    frequency_per_day: 2
  - name: "mental_state"
    frequency_per_day: 4
  - name: "stress_anxiety"
    frequency_per_day: 4
  - name: "social_interaction"
    frequency_per_day: 2
  - name: "work_productivity"
    frequency_per_day: 2
  - name: "environment"
    frequency_per_day: 2
  - name: "physical_symptoms"
    frequency_per_day: 2
    
calendar:
  personal_email: "user@gmail.com"
  work_email: "user@company.com"
  check_interval_minutes: 15
  
garmin:
  email: "garmin_email@example.com"
  password: "garmin_password"
  sync_interval_hours: 1
  
llm:
  model: "gemma2:32b"
  max_retries: 5
  temperature: 0.3
  
server:
  host: "0.0.0.0"
  port: 8000
  api_key: "generate_secure_random_key"
  
database:
  host: "localhost"
  port: 5432
  name: "ema_tracker"
  user: "ema_user"
  password: "secure_password"
  
redis:
  host: "localhost"
  port: 6379
```

---

## Testing Strategy

### Unit Tests
- [ ] LLM extraction with sample responses
- [ ] Schema validation
- [ ] Scheduling algorithm
- [ ] Correlation calculations
- [ ] Gap detection logic

### Integration Tests
- [ ] API endpoints
- [ ] Database operations
- [ ] Background jobs
- [ ] Calendar sync
- [ ] Garmin sync

### End-to-End Tests
- [ ] Full prompt → response → extraction → storage flow
- [ ] Multi-day usage simulation
- [ ] Offline/online transitions
- [ ] Analysis job execution

---

## Success Criteria

**Week 1:**
- ✅ Server running with database
- ✅ Basic prompting system working
- ✅ LLM extraction functional

**Week 2:**
- ✅ Android app installable and functional
- ✅ Prompts display on phone
- ✅ Voice input works
- ✅ Responses stored in database

**Week 3:**
- ✅ Calendar integration working (no prompts during meetings)
- ✅ Garmin data syncing automatically
- ✅ Iterative prompting asks follow-up questions

**Week 4:**
- ✅ Analysis jobs running daily/weekly
- ✅ Insights generated and viewable
- ✅ System runs reliably for 7+ days

**Week 5:**
- ✅ Historical gaps detected and filled
- ✅ User can configure all settings
- ✅ Documentation complete

**Week 6:**
- ✅ System production-ready
- ✅ User actively using system daily
- ✅ First meaningful correlations discovered

---

## Maintenance & Monitoring

### Daily Checks
- [ ] Check Celery worker logs for errors
- [ ] Verify Garmin sync completed
- [ ] Verify calendar sync completed
- [ ] Check for failed LLM extractions

### Weekly Reviews
- [ ] Review generated insights
- [ ] Check data quality and completeness
- [ ] Adjust prompt frequency if needed
- [ ] Review missed prompts and understand why

### Monthly Tasks
- [ ] Database backup
- [ ] Review and optimize slow queries
- [ ] Update LLM prompts based on extraction quality
- [ ] Review and update question bank

---

## Security Considerations

### API Security
- Use API keys for authentication
- LAN-only deployment initially
- Rate limiting on endpoints
- Input validation on all user inputs

### Data Security
- Encrypt sensitive data at rest (Garmin credentials)
- Use environment variables for secrets
- Regular database backups to NAS
- No PII in logs

### Privacy
- All data stays local (no cloud services)
- User has full control over data
- Data export capability
- Data deletion capability

---

## Future Roadmap

### Phase 2 Features (Post-MVP)
1. Web dashboard for viewing insights and trends
2. Export to CSV/PDF reports
3. VPN setup for remote access (Tailscale)
4. Support for multiple users
5. Integration with Apple Health
6. Custom visualization charts

### Phase 3 Features
1. Natural language command system (with Claude Code integration)
2. Experiment tracking and A/B testing
3. Machine learning models for personalized predictions
4. Integration with other health apps
5. Configurable automation (e.g., "if stress > 7, prompt for coping strategies")

---

## Notes for Claude Code

When implementing this system:

1. **Start with database models** - These define everything else
2. **Create sample data** - Use seed scripts to test with realistic data
3. **Test LLM extraction early** - This is critical; make sure prompts work well
4. **Build iteratively** - Get basic prompting working before adding complexity
5. **Focus on reliability** - System must be robust enough for daily use
6. **Modular design** - Each service should be independent and testable
7. **Configuration over code** - Make everything configurable via config.yaml
8. **Error handling** - Expect LLM failures, network issues, etc.
9. **Logging** - Log everything for debugging
10. **Documentation** - Comment complex logic, especially scheduling algorithm

**Key Files to Create First:**
1. `database.py` - SQLAlchemy engine and session setup
2. `models/` - All SQLAlchemy ORM models
3. `alembic/` - Initialize Alembic for migrations
4. `config.py` - Configuration loader
5. `services/llm_service.py` - LLM extraction wrapper
6. `services/scheduler.py` - Prompt scheduling logic
7. `api/prompts.py` - Prompt endpoints
8. `api/responses.py` - Response endpoints

**Python Requirements (`requirements.txt`):**
```
# Web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9

# Task queue
celery==5.3.4
redis==5.0.1

# Integrations
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
garminconnect==0.2.9

# LLM
requests==2.31.0

# Data validation
pydantic==2.5.0
pydantic-settings==2.1.0
jsonschema==4.20.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3
pyyaml==6.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```

**Most Critical Components:**
- Scheduling algorithm (determines quality of experience)
- LLM extraction (determines data quality)
- Iterative prompting (determines completeness)
- Analysis engine (determines value of insights)

Good luck building this system! It's ambitious but very achievable with systematic implementation.