# Version 8 System Specifications

This document outlines the specifications for Version 8 of the system, representing the next evolution of the automation platform. It incorporates the current architecture while defining new components and improvements.

## Table of Contents
- [1. Overview](#1-overview)
- [2. Architecture Changes](#2-architecture-changes)
- [3. Screen Registry Redesign](#3-screen-registry-redesign)
- [4. Multi-Phone Interface](#4-multi-phone-interface)
- [5. Action Modes](#5-action-modes)
- [6. AI Integration](#6-ai-integration)
- [7. Database Structure](#7-database-structure)
- [8. Scaling Considerations](#8-scaling-considerations)
- [9. Web Deployment Strategy](#9-web-deployment-strategy)
- [10. Error Handling and Recovery](#10-error-handling-and-recovery)
- [11. Scheduler Integration](#11-scheduler-integration)
- [12. Task Hierarchy and Recovery System](#12-task-hierarchy-and-recovery-system)
- [13. Text Input Handling](#13-text-input-handling)
- [14. Performance Optimization](#14-performance-optimization)
- [15. Variable System and Group Management](#15-variable-system-and-group-management)

## 1. Overview

Version 8 represents a significant evolution of the system, moving from the current architecture to a more integrated, scalable solution with enhanced capabilities for multi-device management, screen verification, and automation. The system will maintain backward compatibility with existing components while introducing new features and optimizations.

## 2. Architecture Changes

### 2.1 Current Architecture

The current system consists of several independent components:
- Explorer (explorer_7.py): Records interaction sequences
- Connection Monitor (connection_monitor.py): Monitors device connections
- Player (player_7.py): Plays back recorded sequences
- Screen Analyzer GUI (screen_analyzer_gui_new.py): GUI for analyzing screens
- Screen Verifier (screen_verifier.py): Verifies screen states
- Connection Manager (connection_manager.py): Manages device connections
- APK Version Manager (apk.py): Manages APK versions
- XAPK Extractor (xapk_extractor.py): Extracts APK files from XAPK packages

### 2.2 New Architecture

The new architecture will integrate these components into a cohesive system with:
- A unified interface for device management, recording, and playback
- A redesigned screen registry for improved screen identification
- Database integration for analytics and non-critical data
- AI-assisted screen analysis and element identification
- Web deployment capabilities for remote access

## 3. Screen Registry Redesign

### 3.1 Current Limitations

The current state registry (reference_system/state_registry.json) has several limitations:
- Confusing structure with states and interrupts treated differently
- Inconsistent handling of validation and invalidation regions
- No clear association between screens and actions
- Lack of app-specific organization

### 3.2 New Registry Structure

The new screen registry will use a more logical structure:

```json
{
  "apps": {
    "tiktok": {
      "states": {
        "home_screen": {
          "name": "TikTok Home Screen",
          "description": "Main feed screen of TikTok",
          "validation_regions": [
            {
              "name": "home_icon",
              "coordinates": [x1, y1, x2, y2],
              "ocr_enabled": true
            }
          ],
          "actions": [
            {
              "name": "go_to_profile",
              "coordinates": [x1, y1, x2, y2],
              "action_type": "tap",
              "linked_state": "profile_screen"
            }
          ]
        }
      },
      "interrupts": {
        "update_popup": {
          "name": "Update Popup",
          "description": "Popup asking to update the app",
          "validation_regions": [
            {
              "name": "update_text",
              "coordinates": [x1, y1, x2, y2],
              "ocr_enabled": true
            }
          ],
          "actions": [
            {
              "name": "dismiss",
              "coordinates": [x1, y1, x2, y2],
              "action_type": "tap",
              "linked_state": null
            }
          ]
        }
      }
    },
    "global": {
      "interrupts": {
        "system_update": {
          "name": "System Update",
          "description": "System-level update notification",
          "validation_regions": [],
          "actions": []
        }
      }
    }
  }
}
```

Key changes:
- Organization by app, with a global section for system-wide interrupts
- Consistent structure for both states and interrupts
- Each screen (state or interrupt) has validation regions and actions
- Actions for states include linked states, while interrupt actions typically don't
- Clear separation between screen identification and action execution

### 3.3 Screen Identification Logic

- Screen matching is binary - either an exact match or unknown
- Each app has its own states and interrupts
- Global interrupts apply across all apps
- Each screen requires a name, description, and app association
- Validation regions determine if a screen matches a known state or interrupt

## 4. Multi-Phone Interface

### 4.1 Interface Layout

- Command window on the left side showing all connected phones
- Phones displayed in rows of 5 maximum, automatically scaled
- Each phone shows:
  - Current screenshot
  - Phone number overlay (semi-transparent)
  - Glowing blue box around selected phones
  - Any associated tags

### 4.2 Selection Mechanisms

- Click on a single phone to select it
- Click and drag between phones to select multiple
- Ctrl+click to select/deselect individual phones
- Toggle between multi-phone and single-phone views

### 4.3 Device Management

- Integration with connection_monitor.py for automatic reconnection
- Single phone model across the farm for consistency
- Potential for model switching via dropdown if needed in the future
- Custom tags for organization and filtering

## 5. Action Modes

### 5.1 Action Mode

- Single clicks create a 100px box around the center point
- Staying within box before release = tap action
- Moving outside box before release = swipe action
- Duration tracking:
  - < 0.5 seconds = tap
  - ≥ 0.5 seconds = long tap
- Right-click triggers text entry dialog
- Actions execute on all selected phones
- Automatic screenshot capture after each action
- Screen updates in the interface after each action

### 5.2 Recording Mode

- Captures all actions into a JSON sequence file
- Saves unknown screens for later processing
- Background AI analysis for screen identification
- Proposes names, descriptions, and validation regions for unknown screens

### 5.3 Edit Mode

- Interface for editing defined areas on screens
- Similar to current analyzer but with multi-phone support
- Ability to define and modify validation regions
- Ability to define and modify actions

## 6. AI Integration

### 6.1 Screen Analysis Capabilities

- AI will analyze screenshots to identify and categorize screens
- For each unknown screen, the AI will generate:
  - A descriptive name for the screen
  - A detailed description of the screen's purpose and content
  - Up to 3 distinct elements that can conclusively identify the screen
- Elements must be consistent over time (e.g., not changing content like specific videos)
- The existing Finder tool will identify coordinates for these elements

### 6.2 Integration with Edit Mode

- AI suggestions will be pre-filled in edit mode for manual review
- The name and description proposed by AI will be prefilled
- Validation regions and action boxes will be predrawn on screen
- Users can move, resize, delete, or create new regions as needed

### 6.3 Review Process

- All AI suggestions require manual review and approval
- No confidence levels are used as all suggestions are manually verified
- The system will maintain a queue of new screens to be processed
- Processed screens are added to the screen registry

## 7. Database Structure

### 7.1 JSON vs. Database

- JSON for static screen identification and action data (for speed)
- SQL/SQLite for analytics and non-critical data
- Moderate concurrency needs (not dozens of simultaneous requests)

### 7.2 Hybrid Data Architecture

- **JSON Files**:
  - Screen definitions and validation regions
  - Action sequences and playback instructions
  - Recovery prompts and error handling instructions
  - Variables and text templates
  - Fast read access for real-time operations
  - Self-contained execution units that can run independently

- **Database**:
  - Complete execution history and analytics
  - User/client management and access control
  - Scheduling information and task queues
  - Group definitions and relationships
  - Historical data for reporting and optimization

### 7.3 Database Tables

- **Execution Data**:
  - `executions`: Records of sequence executions with timestamps, duration, status
  - `execution_steps`: Individual steps within executions with timing and status
  - `execution_errors`: Detailed error information including screenshots and recovery attempts

- **Management Data**:
  - `users`: User accounts and access permissions
  - `clients`: Client information and settings
  - `phones`: Phone inventory and status information
  - `accounts`: Social media account information

- **Scheduling Data**:
  - `tasks`: Scheduled tasks with timing parameters
  - `task_dependencies`: Relationships between tasks
  - `task_history`: Historical record of task executions

- **Group Data**:
  - `groups`: Group definitions and metadata
  - `group_memberships`: Entity membership in groups
  - `group_relationships`: Relationships between groups

### 7.4 Database Sharding Strategy

- Client-based sharding for isolation and performance
- Separate database instances or schemas per client
- Shared schema for system-wide data
- Consistent connection management across shards

### 7.5 Detailed Database Schema

#### 7.5.1 Core Tables

```sql
CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL, -- 'admin', 'client_manager', 'operator'
    client_id INTEGER, -- NULL for admins/super users
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE phones (
    phone_id INTEGER PRIMARY KEY,
    serial_number TEXT UNIQUE NOT NULL,
    phone_number TEXT,
    model TEXT,
    client_id INTEGER,
    agent_id INTEGER,
    status TEXT DEFAULT 'active', -- 'active', 'maintenance', 'offline'
    last_connected TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL, -- 'tiktok', 'instagram', etc.
    account_number TEXT NOT NULL,
    username TEXT,
    password TEXT,
    profile_id INTEGER,
    phone_id INTEGER,
    status TEXT DEFAULT 'warming', -- 'active', 'warming', 'suspended'
    warming_start_date TIMESTAMP,
    warming_phase INTEGER DEFAULT 1, -- 1-5 representing warming progression
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id),
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    UNIQUE(platform, account_number, phone_id)
);

CREATE TABLE profiles (
    profile_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    birth_month INTEGER,
    birth_day INTEGER,
    birth_year INTEGER,
    gender TEXT,
    profile_password TEXT,
    interests TEXT,
    client_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);
```

#### 7.5.2 Group Management Tables

```sql
CREATE TABLE groups (
    group_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    group_type TEXT, -- 'active', 'warming', 'topic', 'custom'
    client_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE group_memberships (
    membership_id INTEGER PRIMARY KEY,
    group_id INTEGER,
    entity_type TEXT, -- 'account', 'phone', 'profile'
    entity_id INTEGER, -- references the ID in the respective table
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

CREATE TABLE group_relationships (
    relationship_id INTEGER PRIMARY KEY,
    group_id1 INTEGER,
    group_id2 INTEGER,
    relationship_type TEXT, -- 'exclusive', 'prerequisite', 'related'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id1) REFERENCES groups(group_id),
    FOREIGN KEY (group_id2) REFERENCES groups(group_id)
);
```

#### 7.5.3 Execution and Task Tables

```sql
CREATE TABLE tasks (
    task_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    sequence_file TEXT, -- Path to JSON sequence file
    schedule_type TEXT, -- 'immediate', 'scheduled', 'window'
    scheduled_time TIMESTAMP,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    repetitions INTEGER DEFAULT 1,
    client_id INTEGER,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE TABLE task_dependencies (
    dependency_id INTEGER PRIMARY KEY,
    task_id INTEGER,
    depends_on_task_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(task_id)
);

CREATE TABLE task_targets (
    target_id INTEGER PRIMARY KEY,
    task_id INTEGER,
    target_type TEXT, -- 'phone', 'account', 'group'
    target_id_value INTEGER, -- ID of the phone, account, or group
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE TABLE executions (
    execution_id INTEGER PRIMARY KEY,
    task_id INTEGER,
    phone_id INTEGER,
    account_id INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'pending', 'running', 'completed', 'failed'
    error_message TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE execution_steps (
    step_id INTEGER PRIMARY KEY,
    execution_id INTEGER,
    step_number INTEGER,
    action_type TEXT,
    screen_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'success', 'failed', 'skipped'
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

#### 7.5.4 Content Performance Tracking

```sql
CREATE TABLE content_posts (
    post_id INTEGER PRIMARY KEY,
    account_id INTEGER,
    platform TEXT,
    platform_post_id TEXT, -- ID from the platform if available
    post_type TEXT, -- 'video', 'image', 'story', etc.
    caption TEXT,
    hashtags TEXT,
    link_in_bio_active BOOLEAN,
    post_url TEXT,
    media_path TEXT, -- Local path to the media file
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE post_metrics (
    metric_id INTEGER PRIMARY KEY,
    post_id INTEGER,
    metric_date DATE, -- For daily tracking
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES content_posts(post_id),
    UNIQUE(post_id, metric_date) -- One record per post per day
);

CREATE TABLE post_analytics_sources (
    source_id INTEGER PRIMARY KEY,
    post_id INTEGER,
    source_type TEXT, -- 'hashtag', 'fyp', 'following', 'search', etc.
    views INTEGER DEFAULT 0,
    metric_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES content_posts(post_id),
    UNIQUE(post_id, source_type, metric_date)
);
```

#### 7.5.5 Content Analysis

```sql
CREATE TABLE content_analysis (
    analysis_id INTEGER PRIMARY KEY,
    post_id INTEGER,
    frame_timestamp REAL, -- Timestamp within video
    frame_path TEXT, -- Path to extracted frame
    scene_type TEXT, -- 'indoor', 'outdoor', 'closeup', etc.
    objects TEXT, -- JSON array of detected objects
    text_content TEXT, -- Extracted text from frame
    sentiment REAL, -- -1.0 to 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES content_posts(post_id)
);

CREATE TABLE content_tags (
    tag_id INTEGER PRIMARY KEY,
    post_id INTEGER,
    tag_type TEXT, -- 'category', 'theme', 'topic', 'custom'
    tag_value TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES content_posts(post_id)
);
```

#### 7.5.6 Conversation Tracking

```sql
CREATE TABLE conversations (
    conversation_id INTEGER PRIMARY KEY,
    account_id INTEGER, -- Our account
    platform TEXT,
    external_user_id TEXT, -- Platform's user ID
    external_username TEXT,
    conversation_type TEXT, -- 'comment', 'direct_message'
    started_at TIMESTAMP,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    UNIQUE(account_id, platform, external_user_id, conversation_type)
);

CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY,
    conversation_id INTEGER,
    post_id INTEGER NULL, -- For comments on specific posts
    sender_type TEXT, -- 'account' (us) or 'external' (them)
    message_text TEXT,
    media_url TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
    FOREIGN KEY (post_id) REFERENCES content_posts(post_id)
);

CREATE TABLE message_responses (
    response_id INTEGER PRIMARY KEY,
    message_id INTEGER, -- The message we're responding to
    response_message_id INTEGER, -- Our response message
    response_template_id INTEGER, -- If a template was used
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(message_id),
    FOREIGN KEY (response_message_id) REFERENCES messages(message_id)
);
```

#### 7.5.7 Link in Bio Tracking

```sql
CREATE TABLE link_in_bio (
    link_id INTEGER PRIMARY KEY,
    account_id INTEGER,
    url TEXT,
    title TEXT,
    active_from TIMESTAMP,
    active_to TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE link_clicks (
    click_id INTEGER PRIMARY KEY,
    link_id INTEGER,
    click_date DATE,
    click_count INTEGER DEFAULT 0,
    source TEXT, -- From platform analytics if available
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (link_id) REFERENCES link_in_bio(link_id),
    UNIQUE(link_id, click_date, source)
);
```

#### 7.5.8 Analytics Rollup Tables

```sql
CREATE TABLE client_daily_metrics (
    metric_id INTEGER PRIMARY KEY,
    client_id INTEGER,
    metric_date DATE,
    platform TEXT,
    total_posts INTEGER,
    total_views INTEGER,
    total_likes INTEGER,
    total_comments INTEGER,
    total_link_clicks INTEGER,
    follower_growth INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    UNIQUE(client_id, metric_date, platform)
);

CREATE TABLE platform_daily_metrics (
    metric_id INTEGER PRIMARY KEY,
    metric_date DATE,
    platform TEXT,
    total_posts INTEGER,
    total_views INTEGER,
    total_likes INTEGER,
    total_comments INTEGER,
    total_link_clicks INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date, platform)
);
```

### 7.6 Data Retention Policies

#### 7.6.1 Screenshots and Media

- **Error Screenshots**: Retain for 30 days
- **Unknown Screens**: Retain for 60 days (for AI training)
- **Regular Screenshots**: Retain for 7 days, then sample 1 per hour for another 7 days
- **Compress** screenshots older than 24 hours
- **Content Frames**: Retain for 90 days

#### 7.6.2 Execution Data

- **Detailed Step Data**: Retain for 30 days
- **Summary Execution Data**: Retain for 1 year
- **Error Logs**: Retain for 90 days

#### 7.6.3 Performance Metrics

- **Daily Metrics**: Retain for 2 years
- **Hourly Metrics**: Retain for 90 days
- **Aggregated Metrics**: Retain indefinitely

#### 7.6.4 Conversation Data

- **Active Conversations**: Retain all messages
- **Inactive Conversations**: Archive after 1 year of inactivity
- **Message Content**: Retain indefinitely (text is storage-efficient)

#### 7.6.5 Storage Tiers

- **Hot Storage**: Recent data (0-30 days)
- **Warm Storage**: Medium-term data (30-180 days)
- **Cold Storage**: Historical data (180+ days)

## 8. Scaling Considerations

### 8.1 Device Scaling

- Single agent process per computer supporting up to 60 phones
- Multi-threaded architecture for efficient resource usage:
  - One main thread for server communication and coordination
  - One thread per 10-15 phones for device monitoring
  - Thread pool for executing actions on phones
  - Separate threads for resource-intensive operations

### 8.2 Natural Behavior Simulation

- Time window randomization instead of fixed execution times
- Variable delays between actions to mimic human behavior
- Staggered execution across devices to avoid synchronized patterns
- Contextual awareness to prevent unnatural action sequences

### 8.3 Performance Optimization

- Prioritize actions that lock devices but use minimal compute resources
- Implement resource monitoring to prevent system overload
- Cache frequently accessed data for improved response times
- Optimize image processing and screen matching algorithms

### 8.4 Scaling to Hundreds of Devices

- Group agents by client for logical separation
- Implement central coordination with distributed execution
- Use message queues for reliable task distribution
- Design for horizontal scaling with stateless server components

## 9. Web Deployment Strategy

### 9.1 Architecture

- Client-server architecture with local agents
- Web-based frontend for control and visualization
- Backend server for coordination and data storage
- Local device farm agents for direct device interaction

### 9.2 Local Agent Components

- Connection Monitor: Manages device connections and reconnections
- ADB Interaction: Handles direct communication with devices
- Server Communication: Sends/receives instructions to/from the server

### 9.3 Communication Flow

- Local agent reports connected phones to the server
- Server sends instructions to the local agent
- Local agent pings the server every 1-2 seconds for instructions on non-busy phones
- Local agent notifies server when it initiates an action and reports the result

### 9.4 Security Considerations

- User authentication on the login side
- Basic encryption and protection of the database
- Multi-tiered access control:
  - Client-level access with multiple users per client
  - "Agency" tier that can grant access to multiple clients
  - Various permission levels within each tier
- Ensuring users can only see and control phones they have permission to access

## 10. Error Handling and Recovery

### 10.1 Recovery Prompts

- Each playback JSON will include a recovery prompt
- When screen validator returns an unknown screen, the recovery prompt activates
- FarmCLI takes over executing via AI until the task is complete

### 10.2 Recovery Process

- Automatic recovery attempts are made when unknown screens are encountered
- Notifications are sent for failed recovery attempts
- The system tracks recovery success rates for optimization

### 10.3 Debugging Information

The following information is captured for troubleshooting:
- Screenshots of all screens encountered
- Full get event data
- AI prompts and responses
- API call formats and responses
- Session ID
- Timestamps
- Sequence ID when recording new sequences
- Client and user IDs

## 11. Scheduler Integration

### 11.1 Scheduler Components

Integration with the existing scheduler system, which includes:
- TaskRegistry: Catalog of all available tasks
- TaskDatabase: Persistent storage for tasks and execution history
- SequenceManager: Management of ordered task collections
- TaskScheduler: Coordination of when tasks are executed
- TaskExecutor: Execution of tasks through FarmCLI or special helpers

### 11.2 Scheduling Capabilities

- Tasks can be scheduled with different execution parameters:
  - IMMEDIATE: Run as soon as possible
  - SCHEDULED: Run at a specific time
  - WINDOW: Run randomly within a time window (with specified repetitions)
- Dependencies between tasks ensure proper execution order
- Status tracking for all tasks in sequences

### 11.3 Special Features

- Account Selection: Tasks can target specific accounts based on patterns
- Flexible Scheduling: Tasks can be scheduled immediately, at specific times, within windows, or periodically
- Dependencies: Tasks can depend on other tasks completing successfully
- Error Handling: The system tracks failures and can skip dependent tasks if prerequisites fail
- Special Helpers: Custom Python scripts can be easily integrated for platform-specific actions

## 12. Task Hierarchy and Recovery System

### 12.1 Task Hierarchy

#### 12.1.1 Tasks (Atomic Actions)

- Single atomic actions like "tap", "swipe", "type text", "wait for screen"
- Each task has a specific action type, parameters, and expected outcome
- Tasks are the building blocks that can be reused across different sequences
- Examples: "Tap on Like button", "Swipe up", "Type comment text"

#### 12.1.2 Sequences (Functional Units)

- Collection of related tasks that accomplish a specific function
- Stored as JSON files for portability and reuse
- Can include conditional logic and error handling at the sequence level
- Examples: "Login to TikTok", "Upload video with caption", "Follow 5 accounts"

#### 12.1.3 Workflows (Complete Processes)

- Collection of sequences executed in a specific order
- Can include scheduling parameters, dependencies, and target selection
- Workflows can be recurring or one-time executions
- Examples: "Daily content posting routine", "Account warming cycle"

### 12.2 Database Schema for Task Hierarchy

```sql
-- Task definitions (atomic actions)
CREATE TABLE task_definitions (
    task_def_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    action_type TEXT NOT NULL, -- 'tap', 'swipe', 'type', 'wait_for_screen', etc.
    default_parameters TEXT, -- JSON object with default parameters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sequence definitions (functional units)
CREATE TABLE sequence_definitions (
    sequence_def_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    json_path TEXT, -- Path to the sequence JSON file
    recovery_prompt TEXT, -- AI prompt for recovery when sequence fails
    version INTEGER DEFAULT 1,
    client_id INTEGER,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Workflow definitions (complete processes)
CREATE TABLE workflow_definitions (
    workflow_def_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    client_id INTEGER,
    created_by INTEGER,
    is_template BOOLEAN DEFAULT FALSE, -- Can be used as a template for new workflows
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Workflow-Sequence mapping
CREATE TABLE workflow_sequences (
    workflow_sequence_id INTEGER PRIMARY KEY,
    workflow_def_id INTEGER,
    sequence_def_id INTEGER,
    execution_order INTEGER, -- Order in which sequences are executed
    conditional_execution TEXT, -- JSON with conditions for executing this sequence
    retry_policy TEXT, -- JSON with retry settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_def_id) REFERENCES workflow_definitions(workflow_def_id),
    FOREIGN KEY (sequence_def_id) REFERENCES sequence_definitions(sequence_def_id)
);
```

### 12.3 Recovery System

#### 12.3.1 System Crash Recovery

- On system restart, check database for interrupted workflows/sequences
- Verify current screen state matches expected state for interrupted task
- Resume execution from the last successful task
- Log recovery attempt and notify administrators

#### 12.3.2 Task Execution Failure

- Implement tiered retry strategy:
  1. Immediate retry (1-2 attempts with 2-second delay)
  2. Short delay retry (1-2 attempts with 10-second delay for ADB reconnection)
  3. Device verification (check if phone is still connected)
- If device is connected but task still fails:
  - Mark workflow as failed
  - Move to next workflow in queue
- If device is disconnected:
  - Pause all workflows for that device
  - Alert administrators
  - Automatically resume when device reconnects

#### 12.3.3 Unknown Screen Recovery

- When unknown screen is encountered:
  1. Capture and save screenshot
  2. Log encounter with timestamp and context
  3. Flag sequence for AI-assisted recovery
  4. Hand off to FarmCLI with recovery prompt
- FarmCLI takes over using AI-driven recovery:
  1. Analyze current screen state
  2. Determine appropriate actions to return to known state
  3. Execute recovery actions
  4. Report success/failure back to main system
- If recovery succeeds:
  1. Resume sequence from appropriate point
  2. Add unknown screen to training dataset
- If recovery fails:
  1. Mark sequence as failed
  2. Notify administrators with detailed diagnostics
  3. Pause device if multiple failures occur

#### 12.3.4 Recovery Data Collection

For each recovery attempt, collect:
- Screenshots before and after failure
- Full event logs
- AI prompts and responses
- API calls and responses
- Session ID and timestamps
- Sequence ID and step information
- Client and user IDs

#### 12.3.5 Recovery Analytics

- Track success rates of different recovery strategies
- Identify common failure patterns
- Recommend improvements to sequences based on failure data
- Provide insights for training AI recovery models

### 12.4 Execution Flow

1. **Scheduling Phase**
   - User creates or selects a workflow definition
   - User schedules the workflow (one-time, recurring, or window-based)
   - User selects targets (accounts, phones, or groups)
   - System creates a scheduled_workflow entry

2. **Execution Preparation**
   - Scheduler identifies workflows due for execution
   - System creates a workflow_execution record
   - System resolves target groups to specific accounts/phones
   - System checks for dependencies and conflicts

3. **Execution Phase**
   - For each sequence in the workflow:
     - Create sequence_execution records for each target
     - Load sequence JSON file
     - Parse and execute tasks in order
     - Record task_execution results
     - Handle errors according to retry policy
     - Update sequence_execution status

4. **Completion and Reporting**
   - Update workflow_execution with final status
   - Generate summary reports
   - Trigger notifications for completion/failure
   - Schedule next execution if recurring

## 13. Text Input Handling

### 13.1 Keyboard Management

- Integration with existing keyboard_map.json and keyboard_maps
- Option to edit keyboard maps in edit mode
- Support for different keyboard layouts

### 13.2 Variable Text Input

- Support for variables in text input
- Text templating capabilities
- Right-click to trigger text entry dialog during recording

## 14. Performance Optimization

### 14.1 Current Bottlenecks

- Disconnect between recording a sequence and updating the registries
- Sub-optimal task scheduling system

### 14.2 Multi-Device Optimization

- Each agent can handle approximately 16 devices simultaneously
- System should not block on actions that lock devices but use minimal compute resources:
  - Video uploads
  - Watching videos
  - Text entry via smart text entry
- System can move on to other devices while waiting for long-running actions

### 14.3 Account Management

- Multiple accounts per phone (up to 4 per social network)
- Randomized activity across accounts to avoid detection
- Activities should not happen at the exact same time or in the exact same order
- Time windows for sequences with randomized execution
- System must prevent scheduling conflicts on the same phone

### 14.4 Performance Metrics

- System performance metrics:
  - Response time for user interactions
  - Device utilization rates
  - Task completion rates
  - Error and recovery rates
  - Database query performance
- Account health metrics:
  - Likes, views, and comments on posts
  - Followers/subscribers count
  - Forced relogins/captcha as bot detection metrics

## 15. Variable System and Group Management

### 15.1 Variable System Architecture

#### 15.1.1 Variable Categories

**Client Variables**
- `${client.name}` - Client name
- `${client.status}` - Client status
- `${client.contact.email}` - Client contact email
- `${client.contact.discord}` - Client contact discord

**Profile Variables**
- `${profile.first_name}` - First name
- `${profile.last_name}` - Last name
- `${profile.birth_month}` - Birth month
- `${profile.birth_day}` - Birth day
- `${profile.birth_year}` - Birth year
- `${profile.gender}` - Gender
- `${profile.profile_password}` - Profile password
- `${profile.interests}` - Interests

**Account Variables**
- `${account.platform.account_number.field}` - Specific account field
  - Example: `${account.tiktok.account1.username}` - Username for TikTok account1
  - Example: `${account.instagram.account2.bio}` - Bio for Instagram account2
  - Example: `${account.platform.account_number.password}` - Account-specific password (defaults to profile password if not set)

**Content Variables**
- `${content.hashtags.set_name}` - Predefined hashtag set
- `${content.caption.template_name}` - Caption template
- `${content.media.next}` - Path to next media file in sequence
- `${content.media.folder(folder_path)}` - Reference to media in a specific folder

**Dynamic Variables**
- `${dynamic.date.format(format_string)}` - Date with format
- `${dynamic.time.format(format_string)}` - Time with format
- `${dynamic.random.number(min-max)}` - Random number in range
- `${dynamic.random.choice(item1,item2,item3)}` - Random selection from list
- `${dynamic.counter(name,start,step)}` - Named counter with start value and step

**AI Variables**
- `${ai.caption(prompt)}` - Generate caption with specific prompt
- `${ai.response(context)}` - Generate response based on context
- `${ai.hashtags(topic,count)}` - Generate hashtags for topic with count

**Custom Variables**
- `${custom.name}` - User-defined custom variable

#### 15.1.2 Spintax Support

- Text with variations: `{option1|option2|option3}`
- Example: `Just {watched|viewed|finished} this {amazing|incredible|awesome} {video|clip}!`

#### 15.1.3 Variable Resolution in Different Use Cases

**Live Use**
- Text entry dialog with variable selector
- Recent variables used
- Variable browser organized by categories
- Preview of resolved variable value

**One-off Scheduled Actions**
- Select specific phone/profile
- Select specific account on that phone
- Configure caption with variables
- Set hashtags with variables
- Preview all resolved variables

**Recurring Scheduled Actions**
- Select phone/profile pattern (specific or rotation)
- Select account pattern (specific or rotation)
- Configure media source (folder, pattern, sequence)
- Set caption template with variables
- Configure hashtag strategy

### 15.2 Scope Specification System

#### 15.2.1 Phone Scope Selectors

- **Specific Phone**: `phone:phone1`
- **All Phones**: `phone:all`
- **Multiple Specific Phones**: `phone:phone1,phone5,phone8`
- **All Except**: `phone:all-phone2,phone3`
- **Client-Based**: `phone:client:FanVue` (all phones for a client)

#### 14.2.2 Account Scope Selectors

- **Specific Account**: `account:tiktok.account1@phone1`
- **All Accounts on Platform**: `account:tiktok.all@phone1`
- **All Accounts on All Platforms**: `account:all@phone1`
- **Multiple Specific Accounts**: `account:tiktok.account1,instagram.account2@phone1`
- **All Except**: `account:all-tiktok.account3@phone1`
- **All Accounts Across Phones**: `account:tiktok.account1@all`
- **Complex Combinations**: `account:tiktok.all@phone1,phone5,phone8`

#### 14.2.3 Scope-Aware Functions

- `${random.account from account:tiktok.all@phone:all}` - Pick a random account
- `${count.accounts in account:instagram.all@phone:client:FanVue}` - Count accounts
- `${filter.phones where profile.gender=male}` - Filter phones by criteria

### 15.3 Access Control Hierarchy

#### 15.3.1 User Roles

- **Super User**: Full access across all clients and phones (highly restricted)
- **Admin**: Access to assigned clients (for team members)
- **Client User**: Access only to their own client's phones
- **Viewer**: Read-only access to specific clients (for reporting/monitoring)

#### 15.3.2 Default Scoping

- All operations are automatically scoped to the current client
- Client context is required for all operations
- Cross-client operations require explicit super user privileges

### 15.4 Group Management System

#### 15.4.1 Group Types

- **System Groups**: Built-in groups like "active" and "warming"
- **Custom Groups**: User-defined groups (e.g., "crypto", "poker", "lifestyle")
- **Smart Groups**: Dynamic groups based on criteria (e.g., "all accounts with >1000 followers")

#### 15.4.2 Group Relationships

- **Exclusivity Sets**: Define sets of mutually exclusive groups
  - Example: `exclusivity_set("account_status", ["active", "warming"])` ensures an account can only be in one of these groups
- **Prerequisite Groups**: Define groups that require membership in another group
  - Example: `requires("premium_content", "active")` ensures only active accounts can be in the premium_content group
- **Exclusionary Rules**: Define groups that cannot overlap
  - Example: `excludes("family_friendly", "adult_content")` ensures no account can be in both groups

#### 15.4.3 Group Hierarchy

- Support for parent-child relationships between groups
- Inheritance of properties and rules
- Ability to operate on entire branches of the hierarchy

### 15.5 Database Implementation

#### 15.5.1 Group Definition Table
```
group_id | name | description | type | client_id | created_by | created_at
```

#### 15.5.2 Group Membership Table
```
membership_id | group_id | entity_type | entity_id | added_by | added_at
```
- `entity_type` could be "account", "phone", etc.
- `entity_id` references the specific entity

#### 15.5.3 Group Relationship Table
```
relationship_id | relationship_type | group_id_1 | group_id_2 | parameters
```
- `relationship_type` could be "exclusive", "requires", "excludes"
- `parameters` stores any additional configuration for the relationship

### 15.6 Group-Based Variable System

#### 15.6.1 Group-Scoped Variables

- `${group.groupname.count}` - Count of entities in the group
- `${group.groupname.random}` - Random entity from the group
- `${foreach.entity in group:groupname}` - Iterate over group members

#### 15.6.2 Group Filtering

- `${group.filter(groupname, criteria)}` - Filter group by criteria
- `${group.intersection(group1, group2)}` - Entities in both groups
- `${group.difference(group1, group2)}` - Entities in group1 but not group2

### 15.7 Implementation Plan

#### 15.7.1 Core Variable System

- Develop variable registry and parser
- Implement variable resolvers for each category
- Create UI components for variable selection and preview

#### 15.7.2 Group Management System

- Implement database schema for groups and relationships
- Develop group membership management
- Create relationship engine for group rules

#### 15.7.3 Integration with Existing Components

- Connect with scheduler for group-based scheduling
- Integrate with screen registry for variable text input
- Link with AI components for dynamic content generation

##Here we are post fuckup, clean later

#### 7.5.9 Scheduling and Execution Tables

```sql
-- Scheduled Workflows
CREATE TABLE scheduled_workflows (
    scheduled_workflow_id INTEGER PRIMARY KEY,
    workflow_def_id INTEGER,
    schedule_type TEXT, -- 'immediate', 'scheduled', 'window', 'recurring'
    scheduled_time TIMESTAMP,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    recurrence_pattern TEXT, -- JSON with recurrence details (daily, weekly, etc.)
    target_selector TEXT, -- Scope specification (e.g., 'account:tiktok.all@phone1')
    status TEXT, -- 'pending', 'active', 'paused', 'completed', 'cancelled'
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_def_id) REFERENCES workflow_definitions(workflow_def_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Workflow Executions
CREATE TABLE workflow_executions (
    workflow_execution_id INTEGER PRIMARY KEY,
    scheduled_workflow_id INTEGER,
    workflow_def_id INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scheduled_workflow_id) REFERENCES scheduled_workflows(scheduled_workflow_id),
    FOREIGN KEY (workflow_def_id) REFERENCES workflow_definitions(workflow_def_id)
);

-- Sequence Executions
CREATE TABLE sequence_executions (
    sequence_execution_id INTEGER PRIMARY KEY,
    workflow_execution_id INTEGER,
    sequence_def_id INTEGER,
    phone_id INTEGER,
    account_id INTEGER,
    execution_order INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'pending', 'running', 'completed', 'failed', 'skipped'
    error_message TEXT,
    recovery_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_execution_id) REFERENCES workflow_executions(workflow_execution_id),
    FOREIGN KEY (sequence_def_id) REFERENCES sequence_definitions(sequence_def_id),
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Task Executions
CREATE TABLE task_executions (
    task_execution_id INTEGER PRIMARY KEY,
    sequence_execution_id INTEGER,
    task_def_id INTEGER,
    execution_order INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'pending', 'running', 'completed', 'failed', 'skipped'
    parameters TEXT, -- JSON with actual parameters used
    result TEXT, -- JSON with execution result
    screenshot_before TEXT, -- Path to screenshot before execution
    screenshot_after TEXT, -- Path to screenshot after execution
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_execution_id) REFERENCES sequence_executions(sequence_execution_id),
    FOREIGN KEY (task_def_id) REFERENCES task_definitions(task_def_id)
);

-- Recovery Attempts
CREATE TABLE recovery_attempts (
    recovery_id INTEGER PRIMARY KEY,
    sequence_execution_id INTEGER,
    task_execution_id INTEGER,
    attempt_number INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT, -- 'success', 'failure'
    recovery_prompt TEXT,
    ai_response TEXT,
    actions_taken TEXT, -- JSON array of actions
    screenshot_before TEXT,
    screenshot_after TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_execution_id) REFERENCES sequence_executions(sequence_execution_id),
    FOREIGN KEY (task_execution_id) REFERENCES task_executions(task_execution_id)
);
```

#### 7.5.10 Organization and Multi-tenancy Tables

```sql
-- Organizations
CREATE TABLE organizations (
    organization_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active', -- 'active', 'inactive', 'deleted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update Clients Table to include organization reference
CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,
    organization_id INTEGER,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active', -- 'active', 'inactive', 'deleted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

-- Users with organization reference
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    organization_id INTEGER,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL, -- 'super_user', 'admin', 'client_user', 'viewer'
    status TEXT DEFAULT 'active', -- 'active', 'inactive', 'deleted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

-- User-Client Access Mapping
CREATE TABLE user_client_access (
    access_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    client_id INTEGER,
    access_level TEXT, -- 'full', 'limited', 'read_only'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    UNIQUE(user_id, client_id)
);
```

#### 7.5.11 App Registry and Installation Tables

```sql
-- App Registry
CREATE TABLE app_registry (
    app_id INTEGER PRIMARY KEY,
    app_name TEXT NOT NULL, -- Friendly name (e.g., 'tiktok')
    package_name TEXT NOT NULL, -- Android package name
    description TEXT,
    default_version TEXT, -- Default version to install
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(app_name),
    UNIQUE(package_name)
);

-- APK Files
CREATE TABLE apk_files (
    apk_id INTEGER PRIMARY KEY,
    app_id INTEGER,
    version TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    is_split BOOLEAN DEFAULT FALSE,
    split_info TEXT, -- JSON with split APK details if applicable
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active', -- 'active', 'deprecated', 'deleted'
    FOREIGN KEY (app_id) REFERENCES app_registry(app_id)
);

-- Phone App Installations
CREATE TABLE phone_apps (
    installation_id INTEGER PRIMARY KEY,
    phone_id INTEGER,
    app_id INTEGER,
    installed_version TEXT,
    installation_date TIMESTAMP,
    last_used_date TIMESTAMP,
    status TEXT DEFAULT 'installed', -- 'installed', 'uninstalled', 'corrupted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    FOREIGN KEY (app_id) REFERENCES app_registry(app_id),
    UNIQUE(phone_id, app_id)
);

-- Active App Tracking
CREATE TABLE active_apps (
    active_id INTEGER PRIMARY KEY,
    phone_id INTEGER,
    app_id INTEGER,
    active_since TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    FOREIGN KEY (app_id) REFERENCES app_registry(app_id),
    UNIQUE(phone_id) -- Only one active app per phone
);

-- Active Account Tracking
CREATE TABLE active_accounts (
    active_account_id INTEGER PRIMARY KEY,
    phone_id INTEGER,
    app_id INTEGER,
    account_id INTEGER,
    active_since TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (phone_id) REFERENCES phones(phone_id),
    FOREIGN KEY (app_id) REFERENCES app_registry(app_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    UNIQUE(phone_id, app_id) -- Only one active account per app per phone
);
```

{{ ... }}

## 16. System Considerations

### 16.1 Database Requirements

- **Database Selection**: The system requires a database that supports:
  - ACID transactions for workflow execution integrity
  - JSON data type support for flexible parameter storage
  - Robust indexing for performance optimization
  - Row-level security for multi-tenant isolation
  - Backup and point-in-time recovery
  - Recommended options: PostgreSQL, MySQL/MariaDB with JSON support, or SQLite for development

- **Data Isolation**: Queries must always include appropriate organization/client filters to ensure data isolation in a multi-tenant environment

- **Soft Deletes**: All important entities should use soft deletes (status flags) instead of hard deletes to maintain referential integrity and audit history

### 16.2 Resource Management

- **Phone Locking**: Phones must not allow multiple concurrent actions. The system must enforce that only one workflow can use a phone at any given time.

- **Account Switching**: The system must maintain persistent memory of which account is active for each platform on each phone. Before executing a sequence or workflow, the system must:
  1. Check if the correct account is active
  2. If not, automatically run the appropriate account switch operation for that platform
  3. Verify the switch was successful before proceeding

- **App State Awareness**: Workflows must specify which app they require, and the system must:
  1. Check if the correct app is currently open
  2. If not, automatically open the required app
  3. Update the active app tracking table
  4. Handle account context changes when switching between apps

### 16.3 Audit Trail and Version Control

#### 16.3.1 Audit Requirements

- Every change to definitions (tasks, sequences, workflows) must be tracked with:
  - User ID of who made the change
  - Timestamp of the change
  - Before and after states
  - Reason for change (if provided)

#### 16.3.2 Version Control Recommendations

- **Git-Based Version Control**:
  - Pros: Industry standard, robust branching and merging, excellent diff tools
  - Cons: Learning curve, requires integration with application logic
  - Implementation: Store JSON definitions in a Git repository with automated commits on changes

- **Database Version History**:
  - Pros: Integrated with database, simpler implementation
  - Cons: Less flexible than Git, limited diff capabilities
  - Implementation: History tables for each definition type with version numbers

- **Hybrid Approach** (Recommended):
  - Store definitions in database for runtime access
  - Periodically export to Git repository for long-term version control
  - Use database triggers to maintain version history for short-term auditing

### 16.4 API Key Management

#### 16.4.1 API Key Storage Recommendations

- **Encrypted Storage**:
  - Store API keys in encrypted format in the database
  - Use a separate encryption key for each organization
  - Rotate encryption keys periodically

- **Vault Service**:
  - Pros: Purpose-built for secret management, access control, audit logging
  - Cons: Additional infrastructure component
  - Options: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault

- **Per-Client API Keys**:
  - Each client should have their own API keys for external services
  - System should support fallback to organization-level keys if client keys not available
  - Permissions system to control which clients can use which services

#### 16.4.2 Implementation Recommendation

```sql
CREATE TABLE api_keys (
    key_id INTEGER PRIMARY KEY,
    organization_id INTEGER,
    client_id INTEGER NULL, -- NULL for organization-wide keys
    service_name TEXT NOT NULL, -- e.g., 'openai', 'google', 'azure'
    key_identifier TEXT NOT NULL, -- Partial/masked key for reference
    encrypted_key TEXT NOT NULL, -- Encrypted full key
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);
```

### 16.5 Workflow Template Sharing

- **Template Marketplace**:
  - Allow marking workflows as templates
  - Support copying templates across clients within an organization
  - Implement permission system for template access

- **Ownership and Attribution**:
  - Track original creator of templates
  - Maintain lineage when templates are copied or modified
  - Support for template versioning

### 16.6 Data Archiving and Analytics

#### 16.6.1 Data Retention Strategy

- **Tiered Storage Approach**:
  - Hot storage (0-30 days): Full execution details, all screenshots
  - Warm storage (30-180 days): Execution summaries, sample screenshots
  - Cold storage (180+ days): Aggregated metrics, critical data only

- **Partitioning Strategy**:
  - Partition execution tables by date
  - Create summary tables for historical analysis
  - Implement data purging policies with option to archive to cold storage

#### 16.6.2 Analytics Database

- **Recommendation**: Implement a separate analytics database
  - Copy relevant data from operational database
  - Optimize schema for analytical queries
  - Support for data warehousing and business intelligence tools

#### 16.6.3 Machine Learning Data Pipeline

- **Data Collection**:
  - Capture rich metadata about content and performance
  - Link video characteristics to engagement metrics
  - Store in format suitable for ML training

- **Feature Extraction**:
  - Extract features from videos and images
  - Track performance metrics over time
  - Generate training datasets for predictive models

### 16.7 Scaling and Performance

- **Horizontal Scaling**:
  - Design for stateless server components
  - Use message queues for reliable task distribution
  - Implement central coordination with distributed execution

- **Load Balancing**:
  - Distribute phone connections across multiple agents
  - Balance workflow execution across available resources
  - Implement priority queues for critical workflows

- **Performance Monitoring**:
  - Track system metrics (CPU, memory, network)
  - Monitor execution times for workflows and sequences
  - Alert on performance degradation or resource constraints

## 18. Deployment and Disaster Recovery Addendum

### 18.1 Local-First Deployment Approach

**Decision**: Implement a local-first, disaster-ready deployment strategy that prioritizes control and portability.

**Rationale**:
- Direct control over hardware and data
- No dependency on third-party cloud services
- Reduced ongoing operational costs
- Simplified compliance and data sovereignty
- Ability to quickly relocate in emergency situations

### 18.2 System Architecture

```
┌─────────────────────────────────────────┐
│ Primary Server (Windows)                │
├─────────────────┬───────────────────────┤
│ Docker          │ ┌─────────────────┐   │
│                 │ │ PostgreSQL      │   │
│ ┌─────────────┐ │ └─────────────────┘   │
│ │ Web UI      │ │ ┌─────────────────┐   │
│ └─────────────┘ │ │ Task Scheduler  │   │
│ ┌─────────────┐ │ └─────────────────┘   │
│ │ API Server  │ │ ┌─────────────────┐   │
│ └─────────────┘ │ │ Message Queue   │   │
│ ┌─────────────┐ │ └─────────────────┘   │
│ │ Phone Agent │ │                       │
│ └─────────────┘ │                       │
└─────────────────┴───────────────────────┘
          │
          ▼
┌─────────────────────┐
│ Connected Phones    │
└─────────────────────┘
```

### 18.3 Containerization Strategy

**Base Docker Compose Configuration**:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_DB: automation_db

  api:
    build: ./api
    depends_on:
      - postgres
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/automation_db

  web:
    build: ./web
    ports:
      - "80:80"
    depends_on:
      - api

  phone_agent:
    build: ./phone_agent
    volumes:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    depends_on:
      - api

volumes:
  postgres_data:
```

### 18.4 Backup and Recovery Strategy

#### 18.4.1 Backup Components

- **Database Backups**: Daily full dumps and hourly incremental backups
- **Configuration Files**: Version-controlled in Git repository
- **Application Code**: Stored in Git with tagged releases
- **User Content**: Regular backups of uploaded media and content
- **System Images**: Monthly VM snapshots of the entire system

#### 18.4.2 Backup Automation

```bash
#!/bin/bash
# Daily backup script

# Set variables
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.dump"
EXTERNAL_STORAGE="/mnt/external_drive/backups"

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Database backup
docker exec postgres pg_dump -U ${DB_USER} -F c automation_db > ${DB_BACKUP_FILE}

# Compress backup
gzip ${DB_BACKUP_FILE}

# Copy to external storage
mkdir -p ${EXTERNAL_STORAGE}
rsync -avz ${BACKUP_DIR}/ ${EXTERNAL_STORAGE}/

# Cleanup old backups (keep last 30 days)
find ${BACKUP_DIR} -name "db_*.dump.gz" -type f -mtime +30 -delete

# Log backup completion
echo "Backup completed at $(date)" >> ${BACKUP_DIR}/backup_log.txt
```
