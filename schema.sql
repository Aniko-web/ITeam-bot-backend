-- ==============================================================================
-- Mobile Legends: Bang Bang (MLBB) Esports Community Platform
-- PostgreSQL 15+ Production Optimized Schema
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- ENUM TYPES
-- ------------------------------------------------------------------------------
CREATE TYPE mlbb_rank_tier AS ENUM (
    'Warrior',
    'Elite',
    'Master',
    'Grandmaster',
    'Epic',
    'Legend',
    'Mythic',
    'Mythic Honor',
    'Mythic Glory',
    'Mythic Immortal'
);

CREATE TYPE mlbb_role AS ENUM (
    'Jungler',
    'Mid Laner',
    'Exp Laner',
    'Gold Laner',
    'Roamer'
);

CREATE TYPE team_member_status AS ENUM (
    'active',
    'pending_approval',
    'benched',
    'declined'
);

CREATE TYPE team_slot_type AS ENUM (
    'captain',
    'starter',
    'substitute'
);

CREATE TYPE voice_channel_type AS ENUM (
    'in_game_mic',
    'telegram_voice',
    'discord',
    'teamspeak',
    'other'
);

CREATE TYPE match_format AS ENUM (
    'BO1',
    'BO3',
    'BO5'
);

CREATE TYPE scrim_status AS ENUM (
    'open',
    'matched',
    'ready_check_pending',
    'ready_check_confirmed',
    'in_progress',
    'completed',
    'cancelled',
    'expired'
);

CREATE TYPE pvp_lobby_status AS ENUM (
    'open',
    'full',
    'ready_check',
    'credentials_shared',
    'in_progress',
    'completed',
    'cancelled'
);

CREATE TYPE karma_action_type AS ENUM (
    'endorsement',
    'report'
);

-- ------------------------------------------------------------------------------
-- 1. USERS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(64),
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128),
    avatar_url TEXT,
    
    -- MLBB Identity
    mlbb_id VARCHAR(32) NOT NULL,
    server_id VARCHAR(16) NOT NULL,
    in_game_nickname VARCHAR(64) NOT NULL,
    
    -- Roles and Hero Pool
    main_roles mlbb_role[] NOT NULL DEFAULT '{}',
    top_heroes VARCHAR(64)[] NOT NULL DEFAULT '{}',
    
    -- Rank Tiering
    current_rank mlbb_rank_tier NOT NULL DEFAULT 'Mythic',
    highest_rank mlbb_rank_tier NOT NULL DEFAULT 'Mythic Glory',
    current_stars INT NOT NULL DEFAULT 0,
    language VARCHAR(8) NOT NULL DEFAULT 'uz',
    
    -- Schedule & Matchmaking Availability
    playtime_schedule VARCHAR(128) DEFAULT '20:00 - 00:00 UTC+5',
    is_lfg_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_lfg_ping TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Economy & Customization (ITeam Platform)
    istars_balance INT NOT NULL DEFAULT 0,
    selected_background_id VARCHAR(64) NOT NULL DEFAULT 'deep-void',

    -- Anti-Troll & Community Trust
    karma_score INT NOT NULL DEFAULT 100,
    total_scrims_played INT NOT NULL DEFAULT 0,
    total_pvp_played INT NOT NULL DEFAULT 0,
    penalties_count INT NOT NULL DEFAULT 0,
    is_banned BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_karma_score_bounds CHECK (karma_score >= 0 AND karma_score <= 200)
);

-- Indexes for ultra-fast LFG matching
CREATE INDEX IF NOT EXISTS idx_users_lfg_active_rank ON users(is_lfg_active, current_rank) WHERE is_lfg_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_main_roles ON users USING GIN (main_roles);
CREATE INDEX IF NOT EXISTS idx_users_karma_score ON users(karma_score);
CREATE INDEX IF NOT EXISTS idx_users_mlbb_id ON users(mlbb_id, server_id);

-- ------------------------------------------------------------------------------
-- 2. TEAMS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    captain_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE RESTRICT,
    name VARCHAR(64) NOT NULL UNIQUE,
    tag VARCHAR(8) NOT NULL UNIQUE,
    logo_url TEXT,
    pro_team_logo_id VARCHAR(64),
    is_custom_logo BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    
    -- Communication Settings (Voice Channel is private until applicant accepted)
    voice_type voice_channel_type NOT NULL DEFAULT 'in_game_mic',
    voice_link_secret TEXT, -- Discord URL / Telegram chat link
    
    -- Roster Limits (5 Main + 2 Subs default = 7; premium upgradeable to 12)
    max_slots INT NOT NULL DEFAULT 7 CHECK (max_slots >= 5 AND max_slots <= 12),
    is_recruiting BOOLEAN NOT NULL DEFAULT TRUE,
    min_rank_requirement mlbb_rank_tier DEFAULT 'Mythic',
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_id);
CREATE INDEX IF NOT EXISTS idx_teams_recruiting ON teams(is_recruiting, min_rank_requirement);

-- ------------------------------------------------------------------------------
-- 3. TEAM MEMBERS TABLE (Roster & Applications)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    slot_type team_slot_type NOT NULL DEFAULT 'starter',
    assigned_role mlbb_role,
    status team_member_status NOT NULL DEFAULT 'pending_approval',
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_team_user UNIQUE (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_status ON team_members(team_id, status);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

-- ------------------------------------------------------------------------------
-- 4. SCRIMS TABLE (Match Finder & Practice Lobbies)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    host_team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    challenger_team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    
    target_time TIMESTAMP WITH TIME ZONE NOT NULL,
    target_rank mlbb_rank_tier NOT NULL DEFAULT 'Mythic',
    format match_format NOT NULL DEFAULT 'BO3',
    status scrim_status NOT NULL DEFAULT 'open',
    
    -- Credentials (revealed only upon 10/10 Ready Check confirmation)
    custom_room_id VARCHAR(64),
    custom_room_password VARCHAR(64),
    
    ready_check_started_at TIMESTAMP WITH TIME ZONE,
    ready_check_deadline TIMESTAMP WITH TIME ZONE,
    
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrims_status_target_time ON scrims(status, target_time);
CREATE INDEX IF NOT EXISTS idx_scrims_host_team ON scrims(host_team_id);
CREATE INDEX IF NOT EXISTS idx_scrims_challenger_team ON scrims(challenger_team_id);

-- ------------------------------------------------------------------------------
-- 5. SCRIM READY CHECKS TABLE (Player-level Ready confirmation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrim_ready_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scrim_id UUID NOT NULL REFERENCES scrims(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    is_ready BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT uq_scrim_user_ready UNIQUE (scrim_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_scrim_ready_scrim_id ON scrim_ready_checks(scrim_id);

-- ------------------------------------------------------------------------------
-- 6. COMMUNITY PVP LOBBIES TABLE (Bot /create_pvp)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pvp_lobbies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lobby_code VARCHAR(16) NOT NULL UNIQUE,
    title VARCHAR(128) NOT NULL DEFAULT 'Community 5v5 Custom Battle',
    creator_telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    telegram_chat_id BIGINT, -- Originating Telegram Group or Channel
    
    format match_format NOT NULL DEFAULT 'BO1',
    target_rank mlbb_rank_tier NOT NULL DEFAULT 'Mythic',
    max_slots INT NOT NULL DEFAULT 10,
    status pvp_lobby_status NOT NULL DEFAULT 'open',
    
    custom_room_id VARCHAR(64),
    custom_room_password VARCHAR(64),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pvp_lobbies_code ON pvp_lobbies(lobby_code);
CREATE INDEX IF NOT EXISTS idx_pvp_lobbies_status ON pvp_lobbies(status);

-- ------------------------------------------------------------------------------
-- 7. PVP LOBBY PARTICIPANTS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pvp_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lobby_id UUID NOT NULL REFERENCES pvp_lobbies(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    slot_index INT NOT NULL CHECK (slot_index >= 0 AND slot_index < 10),
    team_side VARCHAR(4) NOT NULL CHECK (team_side IN ('BLUE', 'RED')),
    selected_role mlbb_role NOT NULL,
    is_ready BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_lobby_slot UNIQUE (lobby_id, slot_index),
    CONSTRAINT uq_lobby_user UNIQUE (lobby_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_pvp_participants_lobby ON pvp_participants(lobby_id);

-- ------------------------------------------------------------------------------
-- 8. ANTI-TROLL KARMA LOGS TABLE (With 3-Report Anti-Abuse Protection)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS karma_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    target_user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    action_type karma_action_type NOT NULL,
    
    -- Category tags
    -- Endorsements: shot_caller, patience, carry, team_player, versatile
    -- Reports: afk, toxicity, intentional_feeding, griefing, false_credentials
    tag VARCHAR(32) NOT NULL,
    comment TEXT,
    points_delta INT NOT NULL,
    
    match_ref_type VARCHAR(16) CHECK (match_ref_type IN ('scrim', 'pvp', 'lfg')),
    match_ref_id VARCHAR(64),
    
    is_deducted BOOLEAN NOT NULL DEFAULT FALSE, -- Set to TRUE once threshold rules pass
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_reporter_not_target CHECK (reporter_id <> target_user_id)
);

CREATE INDEX IF NOT EXISTS idx_karma_target_unprocessed ON karma_logs(target_user_id, is_deducted, action_type);
CREATE INDEX IF NOT EXISTS idx_karma_reporter_target ON karma_logs(reporter_id, target_user_id, match_ref_id);

-- ------------------------------------------------------------------------------
-- 9. TRANSACTIONS TABLE (ITeam IStars Economy & Playdom Partner)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    amount_istars INT NOT NULL,
    amount_uzs BIGINT NOT NULL DEFAULT 0,
    type VARCHAR(32) NOT NULL, -- 'topup', 'team_logo_pro', 'team_logo_custom', etc.
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    provider VARCHAR(32) NOT NULL DEFAULT 'playdom',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);

-- ------------------------------------------------------------------------------
-- 10. AUTOMATIC TIMESTAMP TRIGGER
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_scrims_updated_at BEFORE UPDATE ON scrims FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_pvp_lobbies_updated_at BEFORE UPDATE ON pvp_lobbies FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

