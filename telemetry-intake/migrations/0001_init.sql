CREATE TABLE IF NOT EXISTS aggregates (
  submission_id TEXT PRIMARY KEY,
  received_day TEXT NOT NULL,
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  received_day TEXT NOT NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  category TEXT NOT NULL CHECK (category IN ('bug', 'idea', 'positive', 'other')),
  text TEXT
);

CREATE INDEX IF NOT EXISTS aggregates_received_day ON aggregates(received_day);
CREATE INDEX IF NOT EXISTS feedback_received_day ON feedback(received_day);
