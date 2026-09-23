CREATE TABLE IF NOT EXISTS schedule_participants (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    is_minister TINYINT NOT NULL DEFAULT 0,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_schedule_participants_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_limits (
    slot_type VARCHAR(16) NOT NULL,
    limit_value INT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (slot_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_participant_lists (
    list_key VARCHAR(64) NOT NULL,
    participant_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (list_key, participant_id),
    CONSTRAINT fk_schedule_lists_participant
        FOREIGN KEY (participant_id)
        REFERENCES schedule_participants (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_extra_dates (
    slot_type VARCHAR(16) NOT NULL,
    date_value DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (slot_type, date_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_months (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    year_value INT NOT NULL,
    month_value INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'unpublished',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_schedule_month (year_value, month_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_slots (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    schedule_id INT UNSIGNED NOT NULL,
    slot_no INT NOT NULL,
    slot_type VARCHAR(16) NOT NULL,
    date_value DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_schedule_slot (schedule_id, slot_no),
    CONSTRAINT fk_schedule_slots_month
        FOREIGN KEY (schedule_id)
        REFERENCES schedule_months (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_slot_participants (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    slot_id INT UNSIGNED NOT NULL,
    participant_id INT UNSIGNED NOT NULL,
    is_scheduled TINYINT NOT NULL DEFAULT 1,
    attendance_status VARCHAR(32) NOT NULL DEFAULT 'planned',
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_slot_participant (slot_id, participant_id),
    CONSTRAINT fk_slot_participants_slot
        FOREIGN KEY (slot_id)
        REFERENCES schedule_slots (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_slot_participants_person
        FOREIGN KEY (participant_id)
        REFERENCES schedule_participants (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_attendance_events (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    schedule_id INT UNSIGNED NOT NULL,
    slot_id INT UNSIGNED NOT NULL,
    participant_id INT UNSIGNED NOT NULL,
    is_scheduled TINYINT NOT NULL DEFAULT 1,
    attendance_status VARCHAR(32) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_attendance_events_schedule (schedule_id),
    KEY idx_attendance_events_slot (slot_id),
    KEY idx_attendance_events_participant (participant_id),
    CONSTRAINT fk_attendance_events_month
        FOREIGN KEY (schedule_id)
        REFERENCES schedule_months (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attendance_events_slot
        FOREIGN KEY (slot_id)
        REFERENCES schedule_slots (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attendance_events_person
        FOREIGN KEY (participant_id)
        REFERENCES schedule_participants (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
