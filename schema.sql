-- Enforce Foreign Keys
PRAGMA foreign_keys = ON;

-- 1. Goals (Top Level)
CREATE TABLE goals (
    id TEXT PRIMARY KEY, -- UUID
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active'
);

-- 2. Projects
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Int ID (Legacy compatibility)
    goal_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active', -- Enum: active, on_hold, completed
    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE SET NULL
);

-- 3. Tasks (Actionable Items)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY, -- UUID
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT 0,
    deadline DATE,
    duration TEXT,
    notes TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 4. Tags (Many-to-Many for Tasks)
-- Commercial Grade: Don't store tags as a CSV string. Normalize them.
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE task_tags (
    task_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (task_id, tag_id),
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 5. Project Resources (Shopping/Prep)
CREATE TABLE project_resources (
    id TEXT PRIMARY KEY, -- UUID
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- Enum: to_buy, to_gather
    store TEXT DEFAULT 'General',
    is_acquired BOOLEAN DEFAULT 0,
    link TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 6. Reference Items
CREATE TABLE reference_items (
    id TEXT PRIMARY KEY, -- UUID
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 7. Inbox (No Project)
CREATE TABLE inbox_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);