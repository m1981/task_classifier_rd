-- seed_data.sql

-- 1. Goals
INSERT INTO goals (id, name, description, status) VALUES
('g-001', 'Home Improvement', 'Renovating the house to increase value and comfort.', 'active'),
('g-002', 'Professional Growth', 'Skills acquisition for Senior Engineer role.', 'active'),
('g-003', 'Health & Fitness', 'Marathon training and diet.', 'active');

-- 2. Projects
-- Note: We explicitly set IDs to link them easily below
INSERT INTO projects (id, goal_id, name, description, status) VALUES
(1, 'g-001', 'Kitchen Renovation', 'Full cabinet and counter replacement', 'active'),
(2, 'g-001', 'Guest Bedroom Paint', 'Painting the spare room blue', 'on_hold'),
(3, 'g-002', 'Master Python AsyncIO', 'Deep dive into concurrency', 'active'),
(4, 'g-003', 'Marathon Prep', 'Training schedule for November', 'active'),
(5, NULL, 'Fix Car Brakes', 'Urgent safety repair', 'active'); -- Orphaned Project

-- 3. Tags
INSERT INTO tags (name) VALUES
('physical'), ('digital'), ('errand'), ('urgent'), ('home'), ('learning');

-- 4. Tasks
INSERT INTO tasks (id, project_id, name, is_completed, duration, notes) VALUES
('t-001', 1, 'Measure cabinet dimensions', 1, '30m', 'Width is critical'),
('t-002', 1, 'Select countertop material', 0, '1h', 'Granite vs Quartz'),
('t-003', 1, 'Demolish old backsplash', 0, '4h', 'Wear goggles'),
('t-004', 3, 'Read AsyncIO documentation', 0, '2h', 'Focus on Event Loop'),
('t-005', 3, 'Build async web scraper', 0, '3h', 'Use aiohttp'),
('t-006', 5, 'Buy brake pads', 0, '30m', 'Check model number');

-- 5. Task Tags (Linking Tasks to Tags)
-- Linking 'Demolish old backsplash' (t-003) to 'physical' (1) and 'home' (5)
INSERT INTO task_tags (task_id, tag_id) VALUES
('t-003', 1), ('t-003', 5),
('t-004', 2), ('t-004', 6),
('t-006', 3), ('t-006', 4);

-- 6. Project Resources (Shopping List)
INSERT INTO project_resources (id, project_id, name, type, store, is_acquired) VALUES
('r-001', 1, 'White Semi-Gloss Paint', 'to_buy', 'Home Depot', 0),
('r-002', 1, 'Paint Rollers', 'to_buy', 'Home Depot', 1), -- Already bought
('r-003', 1, 'Sandpaper', 'to_gather', 'Garage', 0),
('r-004', 5, 'Brake Fluid', 'to_buy', 'AutoZone', 0);

-- 7. Inbox Items (Unprocessed)
INSERT INTO inbox_items (content) VALUES
('Call plumber about low pressure'),
('Research standing desks'),
('Email accountant'),
('Buy dog food');