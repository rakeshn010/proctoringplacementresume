# 🏏 Cricket Auction Platform - Complete Project Analysis
**Generated:** 2026-03-13  
**Purpose:** Comprehensive documentation of all existing modules, features, and APIs to prevent duplication

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Core Modules](#core-modules)
4. [API Endpoints](#api-endpoints)
5. [Database Schema](#database-schema)
6. [Security Features](#security-features)
7. [Real-Time Features](#real-time-features)
8. [Frontend Features](#frontend-features)

---

## 🎯 Project Overview

**Application Type:** Real-time Cricket Auction Platform  
**Architecture:** FastAPI Backend + MongoDB + WebSocket + Jinja2 Templates  
**Deployment:** Railway (Production-ready with Gunicorn + Uvicorn workers)

### Key Capabilities
- Real-time bidding with WebSocket
- Multi-role authentication (Admin, Team Member, Viewer)
- Live auction management with countdown timer
- Player registration and approval workflow
- Team management and budget tracking
- Comprehensive security with IP blocking and threat detection
- Export functionality (Excel/CSV)
- Image upload via Cloudinary
- Session management with Redis
- Rate limiting and performance optimization

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI 0.100.0+
- **Server:** Gunicorn + Uvicorn workers
- **Language:** Python 3.11+
- **Async:** asyncio, WebSockets

### Database & Storage
- **Primary DB:** MongoDB 7.0+
- **Session Store:** Redis 5.0+
- **Image Storage:** Cloudinary
- **File Upload:** python-multipart

### Security & Auth
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt
- **Rate Limiting:** Custom token bucket implementation
- **Session Management:** Custom with Redis backend

### Frontend
- **Templates:** Jinja2
- **JavaScript:** Vanilla JS with WebSocket
- **CSS:** Custom responsive design
- **Charts:** Chart.js (for analytics)
- **PWA:** Service Worker enabled

### Performance & Monitoring
- **Compression:** GZip middleware
- **Caching:** ETag-based caching
- **Monitoring:** psutil for system metrics
- **Logging:** Structured logging with PII sanitization

---

## 🧩 Core Modules

### 1. Authentication & Authorization (`core/`)

#### `core/security.py`
**Purpose:** JWT token management and password hashing
- `hash_password(password)` - Bcrypt password hashing
- `verify_password(plain, hashed)` - Password verification
- `create_access_token(subject, extra_data)` - Generate JWT access token (15 min expiry)
- `create_refresh_token(subject)` - Generate refresh token (1 day expiry)
- `decode_token(token)` - Validate and decode JWT
- `get_current_user(request, authorization)` - Dependency for authenticated routes
- `require_admin(current_user)` - Admin-only dependency
- `require_team_member(current_user)` - Team member dependency

#### `core/auth_middleware.py`
**Purpose:** Strict authentication middleware
- Validates JWT on every request
- Checks token blacklist
- Validates sessions
- Enforces route protection
- Handles both user and team tokens
- Auto-redirects to login on auth failure

#### `core/session_manager.py`
**Purpose:** Session lifecycle management
- `create_session(user_id, request)` - Create new session
- `validate_session(session_id, request)` - Validate and refresh session
- `destroy_session(session_id)` - Destroy single session
- `destroy_all_user_sessions(user_id)` - Force logout all devices
- `blacklist_token(token)` - Add token to blacklist
- `is_token_blacklisted(token)` - Check blacklist
- `cleanup_expired_sessions()` - Periodic cleanup
- **Settings:** 30-min inactivity timeout, 8-hour max duration

#### `core/password_validator.py`
**Purpose:** Password strength validation
- Minimum 8 characters (configurable)
- Requires uppercase, lowercase, digit
- Optional special characters
- Detects common patterns
- Detects repeated characters
- `validate_password(password)` - Validate with exception
- `get_strength_score(password)` - Calculate 0-100 score
- `get_strength_label(score)` - Human-readable label

### 2. Security & Protection (`core/`)

#### `core/security_middleware.py`
**Purpose:** Multi-layer security headers and validation
- **SecurityHeadersMiddleware:** Adds security headers (CSP, HSTS, X-Frame-Options, etc.)
- **RequestValidationMiddleware:** Validates requests, detects injection attempts
- **CSRFProtectionMiddleware:** CSRF token validation (optional, disabled for API)
- **AuditLogMiddleware:** Logs security-sensitive operations
- **IPWhitelistMiddleware:** Optional IP whitelist for admin endpoints

#### `core/integrated_security.py`
**Purpose:** Unified security monitoring and blocking
- **IntegratedSecurityMiddleware:** 
  - Checks blocked IPs
  - Detects path traversal
  - Detects SQL injection
  - Detects XSS attempts
  - Auto-blocks malicious IPs
- **SecurityEventLogger:** Logs security-relevant requests

#### `core/security_monitor.py`
**Purpose:** Real-time threat detection
- `log_security_event(type, severity, ip, details)` - Log security events
- `record_failed_login(ip, email)` - Track failed logins
- `detect_brute_force(ip, attempts, email)` - Brute force detection
- `detect_sql_injection(ip, data, endpoint)` - SQL injection detection
- `detect_xss_attempt(ip, data, endpoint)` - XSS detection
- `detect_path_traversal(ip, path)` - Path traversal detection
- `should_block_ip(ip)` - Check if IP should be blocked (3+ violations)
- `get_security_stats()` - Dashboard statistics
- `cleanup_old_events(days)` - Data retention cleanup

#### `core/auto_blocker.py`
**Purpose:** Automatic IP blocking system
- `block_ip(ip, reason, duration_hours, severity)` - Block an IP
- `is_blocked(ip)` - Check if IP is blocked
- `unblock_ip(ip)` - Manually unblock
- `get_block_info(ip)` - Get block details
- `get_blocked_ips()` - List all blocked IPs
- `cleanup_expired_blocks()` - Remove expired blocks
- `get_stats()` - Blocking statistics
- **Storage:** MongoDB with in-memory cache

#### `core/rate_limiter.py`
**Purpose:** Token bucket rate limiting
- `check_rate_limit(identifier, limit, window, type)` - General rate limit
- `check_bid_rate_limit(user_id)` - Bid-specific (10/min)
- `check_auth_rate_limit(ip)` - Auth-specific (10/5min)
- `check_api_rate_limit(user_id)` - API-specific (100/min)
- `cleanup_old_entries()` - Periodic cleanup
- `get_stats()` - Rate limiter statistics
- `clear_ip_limits(ip)` - Admin function
- `clear_all_limits()` - Admin function

#### `core/log_sanitizer.py`
**Purpose:** PII redaction from logs
- Automatically redacts: emails, phones, credit cards, passwords, tokens, IPs
- `sanitize(message)` - Sanitize string
- `sanitize_dict(data)` - Sanitize dictionary
- **SanitizedFormatter:** Custom logging formatter
- `setup_sanitized_logging()` - Enable PII sanitization

### 3. Performance & Optimization (`core/`)

#### `core/performance_optimizer.py`
**Purpose:** Response optimization and caching
- **PerformanceMiddleware:** 
  - Tracks response time
  - Adds performance headers
  - Logs slow requests (>1s)
- **ETaggerMiddleware:** 
  - Generates ETags for caching
  - Returns 304 Not Modified when appropriate
- **ResponseCompressionOptimizer:** 
  - Optimizes compression settings
  - Adds Vary header
- **StaticAssetOptimizer:** 
  - Long-term caching for versioned assets
  - Immutable flag for fingerprinted files
  - CORS headers for CDN compatibility
- **DatabaseQueryOptimizer:** 
  - MongoDB projection helpers
  - Compound index creation
  - Query hints

#### `core/monitoring.py`
**Purpose:** Application health and metrics
- `get_system_metrics()` - CPU, memory, disk usage
- `check_database_health()` - MongoDB connection status
- `check_redis_health()` - Redis connection status
- `get_websocket_metrics()` - Active connections, rooms
- **Endpoints:**
  - `GET /health` - Basic health check
  - `GET /health/detailed` - Comprehensive health check
  - `GET /metrics` - Prometheus-compatible metrics
  - `GET /stats` - Application statistics

### 4. Configuration (`core/`)

#### `core/config.py`
**Purpose:** Centralized settings management
- **Settings Class (Pydantic):**
  - Application settings (name, version, environment)
  - Database URLs (MongoDB, Redis)
  - JWT configuration (secret, algorithm, expiry)
  - Admin emails
  - CORS origins
  - Auction settings (bid increment, timer)
  - File upload limits
  - Cloudinary credentials
  - Security toggles (rate limiting, CSRF, IP whitelist)
  - WebSocket settings
  - Performance settings
- **Properties:**
  - `admin_email_list` - Parsed admin emails
  - `cors_origins_list` - Parsed CORS origins
  - `admin_ip_whitelist_list` - Parsed IP whitelist

#### `core/cloudinary_config.py`
**Purpose:** Image upload to Cloudinary
- `upload_image(file_content, filename, folder)` - Upload image
- `delete_image(public_id)` - Delete image
- `is_cloudinary_configured()` - Check configuration
- **Features:** Auto-resize, quality optimization, secure URLs

#### `core/route_guard.py` (Referenced but not read)
**Purpose:** Route-level access control
- Defines public/protected routes
- Role-based route access

### 5. WebSocket Management (`websocket/`)

#### `websocket/manager.py`
**Purpose:** Real-time connection management
- **ConnectionManager Class:**
  - `connect(websocket, connection_id, user_data)` - Accept connection
  - `disconnect(connection_id)` - Remove connection
  - `join_room(connection_id, room_name)` - Join room
  - `leave_room(connection_id, room_name)` - Leave room
  - `send_personal_message(message, connection_id, compress)` - Send to one
  - `broadcast(message, exclude, compress)` - Send to all
  - `broadcast_to_room(room_name, message, compress)` - Send to room
  - `broadcast_to_users(message, user_ids)` - Send to specific users
  - `broadcast_bid(bid_data)` - Broadcast new bid
  - `broadcast_player_sold(player_data)` - Broadcast sold event
  - `broadcast_player_unsold(player_data)` - Broadcast unsold event
  - `broadcast_current_player(player_data)` - Broadcast player change
  - `broadcast_auction_status(active)` - Broadcast auction status
  - `broadcast_timer(seconds)` - Broadcast timer update
  - `broadcast_team_update(team_data)` - Broadcast team update
  - `start_timer(seconds, callback)` - Start countdown timer
  - `reset_timer(seconds)` - Reset timer
  - `stop_timer()` - Stop timer
  - `get_connection_count()` - Active connections
  - `get_authenticated_count()` - Authenticated connections
  - `get_room_count(room_name)` - Room connections
  - `get_stats()` - Comprehensive statistics
- **Features:**
  - Message compression for large payloads
  - Heartbeat/ping-pong (15s interval)
  - Connection pooling
  - Room-based broadcasting
  - User-to-connection mapping
  - Automatic cleanup of dead connections

#### `core/websocket_auth.py`
**Purpose:** WebSocket authentication
- `authenticate_websocket(websocket)` - Authenticate via token
- `require_websocket_auth(websocket)` - Require auth or close
- `check_websocket_permission(user, action)` - Check permissions
- **Token Sources:** Query parameter or first message
- **Actions:** admin_control, bid, view

### 6. Business Logic Services (`services/`)

#### `services/auction_service.py`
**Purpose:** Auction state management
- `get_auction_config()` - Get current config
- `start_auction()` - Start auction
- `stop_auction()` - Stop auction
- `get_current_player()` - Get current player
- `set_current_player(player_id)` - Set current player
- `next_player()` - Move to next available
- `mark_player_sold(player_id)` - Mark as sold
- `mark_player_unsold(player_id)` - Mark as unsold

#### `services/bid_service.py`
**Purpose:** Bid processing and validation
- `place_bid(player_id, team_id, bid_amount, bidder_id)` - Place bid
  - Validates auction status
  - Checks timer
  - Validates player status
  - Validates team budget
  - Checks minimum increment
  - Records bid history
  - Updates player
  - Restores previous team budget
  - Deducts from new team
  - Resets timer
  - Broadcasts updates
- `get_bid_history(player_id)` - Get player bid history
- `get_all_bid_history()` - Get complete history (admin)

### 7. Database Layer (`database/`)

#### `database/session.py`
**Purpose:** MongoDB connection management
- Connects to MongoDB using MONGODB_URL or DATABASE_URL
- Creates database client
- Tests connection on startup
- Provides global `db` instance
- Graceful fallback if connection fails

### 8. Data Models (`models/`, `schemas/`)

#### `models/models.py`
**Purpose:** Pydantic base models
- `Player` - Basic player model
- `Team` - Basic team model
- `BidRequest` - Bid request model

#### `schemas/user.py`
**Purpose:** User request/response schemas
- `UserRegister` - Registration data
- `UserLogin` - Login credentials
- `UserResponse` - User data response
- `TokenResponse` - JWT tokens
- `RefreshTokenRequest` - Refresh token

#### `schemas/player.py`
**Purpose:** Player schemas
- `PlayerBase` - Base player fields
- `PlayerCreate` - Create player (admin)
- `PlayerPublicRegister` - Public registration
- `PlayerUpdate` - Update player
- `PlayerResponse` - Player response
- `SetBasePriceRequest` - Set base price

#### `schemas/team.py`
**Purpose:** Team schemas
- `TeamBase` - Base team fields
- `TeamCreate` - Create team
- `TeamUpdate` - Update team
- `TeamResponse` - Team response
- `TeamDetailResponse` - Team with players

#### `schemas/auction.py`
**Purpose:** Auction schemas
- `AuctionStatus` - Auction status
- `SetCurrentPlayerRequest` - Set current player
- `AuctionSessionCreate` - Create session
- `AuctionSessionResponse` - Session response

#### `schemas/bid.py`
**Purpose:** Bid schemas
- `BidRequest` - Place bid
- `BidResponse` - Bid response
- `BidHistoryResponse` - Bid history

### 9. Utilities (`utils/`)

#### `utils/helpers.py`
**Purpose:** Common utility functions
- `validate_object_id(id_str, field_name)` - Validate MongoDB ObjectId
- `serialize_doc(doc)` - Convert MongoDB doc to JSON
- `calculate_percentage(part, total)` - Safe percentage calculation
- `format_currency(amount)` - Format as currency

---

## 🔌 API Endpoints

### Authentication (`routers/auth.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | Public | Register new user |
| POST | `/auth/login` | Public | Login (user or team) |
| POST | `/auth/team/login` | Public | Team-specific login |
| POST | `/auth/logout` | Required | Logout and invalidate token |
| POST | `/auth/refresh` | Public | Refresh access token |
| GET | `/auth/me` | Required | Get current user info |

**Features:**
- Accepts both Form data and JSON
- Rate limiting on login (10 attempts/5min)
- Session creation and management
- Token blacklisting on logout
- HTTP-only cookies for web
- JWT tokens for API

### Players (`routers/players.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/players/public_register` | Public | Public player registration |
| POST | `/players/upload-image/{player_id}` | Required | Upload player image |
| POST | `/players/add` | Admin | Add player (admin) |
| GET | `/players/` | Public | List players (with filters) |
| GET | `/players/{player_id}` | Public | Get player details |
| PUT | `/players/update/{player_id}` | Admin | Update player |
| DELETE | `/players/delete/{player_id}` | Admin | Delete player |

**Query Parameters for List:**
- `status` - Filter by status (available, sold, unsold, in_auction)
- `role` - Filter by role (Batsman, Bowler, All-Rounder, Wicketkeeper)
- `category` - Filter by category (Faculty, Student, Alumni)
- `search` - Search by name
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 50, max: 100)
- `auction_round` - Filter by auction round
- `include_unapproved` - Include unapproved players (default: false)

**Features:**
- Public registration with optional image
- Cloudinary image upload with fallback
- Image validation (type, size)
- Auto-resize and optimization
- Pagination support
- Advanced filtering

### Teams (`routers/teams.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/teams/` | Public | List all teams with stats |
| GET | `/teams/{team_id}` | Public | Get team details with players |
| POST | `/teams/create` | Admin | Create new team |
| PUT | `/teams/update/{team_id}` | Admin | Update team |
| DELETE | `/teams/delete/{team_id}` | Admin | Delete team |
| POST | `/teams/upload-logo/{team_id}` | Admin | Upload team logo |

**Team Statistics (Auto-calculated):**
- Total spent
- Remaining budget
- Players count
- Highest purchase

**Features:**
- Username/password authentication for teams
- Budget validation
- Logo upload to Cloudinary
- Cannot delete team with players
- Real-time budget updates via WebSocket

### Auction (`routers/auction.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auction/status` | Public | Get auction status |
| POST | `/auction/start` | Admin | Start auction |
| POST | `/auction/stop` | Admin | Stop auction |
| GET | `/auction/current_player` | Public | Get current player |
| POST | `/auction/set_current_player/{player_id}` | Admin | Set current player |
| POST | `/auction/next_player` | Admin | Next available player |
| POST | `/auction/start-reauction` | Admin | Start re-auction for unsold |
| GET | `/auction/unsold-players` | Admin | Get unsold players |
| GET | `/auction/auction-rounds` | Public | Get round statistics |
| POST | `/auction/sold/{player_id}` | Admin | Mark player sold |
| POST | `/auction/unsold/{player_id}` | Admin | Mark player unsold |
| POST | `/auction/bid` | Team/Admin | Place a bid |
| GET | `/auction/bid_history/{player_id}` | Public | Get player bid history |
| GET | `/auction/bid_history` | Admin | Get all bid history |
| WS | `/auction/ws` | Public | WebSocket connection |

**Bid Validation:**
- Auction must be active
- Timer must be running
- Player must be available/in_auction
- Bid must exceed current highest
- Minimum increment enforced
- Team budget validation
- Rate limiting (10 bids/min)

**WebSocket Events:**
- `bid_placed` - New bid
- `player_sold` - Player sold
- `player_unsold` - Player unsold
- `current_player_changed` - Player change
- `auction_status` - Status change
- `timer_update` - Timer countdown
- `team_update` - Team budget update
- `ping/pong` - Heartbeat

### Admin (`routers/admin.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/dashboard/stats` | Admin | Dashboard statistics |
| GET | `/admin/dashboard/revenue_by_category` | Admin | Revenue breakdown |
| GET | `/admin/dashboard/team_spending` | Admin | Team spending stats |
| GET | `/admin/players/pending` | Admin | Pending base price players |
| PATCH | `/admin/player/{player_id}/base-price` | Admin | Set base price |
| POST | `/admin/user/{user_id}/assign-team` | Admin | Assign user to team |
| GET | `/admin/activity-logs` | Admin | Recent activity logs |
| POST | `/admin/change-password` | Admin | Change admin password |
| GET | `/admin/players/pending-approval` | Admin | Pending approval players |
| POST | `/admin/players/{player_id}/approve` | Admin | Approve player |
| POST | `/admin/players/{player_id}/reject` | Admin | Reject player |
| GET | `/admin/auction/live-player` | Admin | Get live player |
| POST | `/admin/auction/set-live-player/{player_id}` | Admin | Set player live |
| POST | `/admin/auction/end-live-player/{player_id}` | Admin | End live auction |
| GET | `/admin/auction/eligible-players` | Admin | Get eligible players |
| POST | `/admin/auction/undo-last-sold` | Admin | Undo last sold player |
| GET | `/admin/auction/last-sold-info` | Admin | Get last sold info |
| POST | `/admin/auction/reset` | Admin | Reset entire auction |

**Dashboard Stats (Optimized with Aggregation):**
- Total/sold/unsold/available players
- Total teams, revenue, bids
- Current auction round stats
- Role distribution (Batsman, Bowler, etc.)
- Category distribution

**Live Auction Features:**
- Set player live (only one at a time)
- Auto-close on timer expiry
- Auto-mark sold/unsold
- Broadcast to all clients
- Undo last sold (refund team)

### Reports (`routers/reports.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/reports/export/sold-players` | Admin | Export sold players |
| GET | `/reports/export/team-summary` | Admin | Export team summary |
| GET | `/reports/export/auction-summary` | Admin | Export auction summary |

**Query Parameters:**
- `format` - Export format (csv or excel)

**Features:**
- Requires pandas and openpyxl
- Timestamped filenames
- Comprehensive player/team data
- Excel with formatted sheets
- CSV for simple exports

### Viewer (`routers/viewer.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/viewer/live` | Public | Live viewer dashboard (HTML) |
| GET | `/viewer/analytics` | Public | Live analytics |
| GET | `/viewer/current-player` | Public | Current auction player |
| GET | `/viewer/bid-history/{player_id}` | Public | Player bid history |
| GET | `/viewer/players` | Public | All approved players |

**Analytics Data:**
- Auction status and round
- Player statistics
- Total revenue
- Most expensive player
- Team leaderboard with spending

### Chat (`routers/chat.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/chat/send` | Required | Send message |
| GET | `/chat/messages` | Required | Get messages |
| DELETE | `/chat/message/{message_id}` | Required | Delete message |
| GET | `/chat/rooms` | Required | Get available rooms |

**Rooms:**
- `global` - All teams
- `admin` - Admin announcements
- `team_{team_id}` - Private team chat

**Features:**
- Real-time via WebSocket
- Message history (50 messages)
- Delete own messages or admin
- Sender type (admin, team, user)

### Wishlist (`routers/wishlist.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/wishlist/add/{player_id}` | Required | Add to wishlist |
| DELETE | `/wishlist/remove/{player_id}` | Required | Remove from wishlist |
| GET | `/wishlist/my-wishlist` | Required | Get my wishlist |
| PATCH | `/wishlist/update/{player_id}` | Required | Update wishlist item |
| GET | `/wishlist/check/{player_id}` | Required | Check if in wishlist |

**Wishlist Features:**
- Priority levels (1=High, 2=Medium, 3=Low)
- Max bid setting
- Player details included
- Live status tracking

### Comparison (`routers/comparison.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/comparison/teams` | Required | Compare multiple teams |
| GET | `/comparison/my-team-analysis` | Required | Analyze my team |

**Query Parameters:**
- `team_ids` - Comma-separated team IDs (2-4 teams)

**Comparison Metrics:**
- Total spent, remaining budget
- Budget used percentage
- Players count, average price
- Role distribution
- Category distribution
- Most/least expensive players
- Squad balance score (0-100)
- Value for money score (0-100)

**Team Analysis:**
- Strengths and weaknesses
- Recommendations
- Budget analysis

### Monitoring (`core/monitoring.py`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | Public | Basic health check |
| GET | `/health/detailed` | Public | Detailed health check |
| GET | `/metrics` | Public | Prometheus metrics |
| GET | `/stats` | Public | Application statistics |

**Metrics Exposed:**
- Application uptime
- Active sessions
- WebSocket connections
- Database counts (users, players, teams, bids)
- System resources (CPU, memory, disk)

---

## 🗄️ Database Schema

### Collections

#### `users`
```javascript
{
  _id: ObjectId,
  email: String (unique, indexed),
  password_hash: String,
  name: String,
  is_active: Boolean,
  is_admin: Boolean,
  role: String, // "admin", "team_member", "viewer"
  team_id: ObjectId (nullable),
  created_at: DateTime,
  updated_at: DateTime
}
```

#### `teams`
```javascript
{
  _id: ObjectId,
  name: String,
  username: String (unique),
  hashed_password: String,
  budget: Float,
  logo_path: String,
  created_at: DateTime,
  updated_at: DateTime
}
```

#### `players`
```javascript
{
  _id: ObjectId,
  name: String (indexed),
  role: String (indexed), // "Batsman", "Bowler", "All-Rounder", "Wicketkeeper"
  category: String (indexed), // "Faculty", "Student", "Alumni"
  age: Int,
  batting_style: String,
  bowling_style: String,
  bio: String,
  image_path: String,
  base_price: Float,
  base_price_status: String, // "pending", "set"
  status: String (indexed), // "available", "in_auction", "sold", "unsold"
  is_approved: Boolean,
  is_rejected: Boolean,
  is_live: Boolean,
  auction_round: Int (indexed),
  current_team: String,
  final_team: String,
  final_bid: Float,
  live_start_time: DateTime,
  live_end_time: DateTime,
  sold_at: DateTime,
  created_by: String,
  created_at: DateTime,
  updated_at: DateTime
}
```

#### `bid_history`
```javascript
{
  _id: ObjectId,
  player_id: String (indexed),
  team_id: String (indexed),
  bidder_id: String,
  bid_amount: Float,
  timestamp: DateTime (indexed),
  is_winning: Boolean
}
```
**Compound Index:** `[(player_id, timestamp)]`

#### `config`
```javascript
{
  _id: ObjectId,
  key: String, // "auction"
  active: Boolean,
  current_player_id: String,
  current_player_name: String,
  auction_round: Int,
  timer_seconds: Int,
  started_at: DateTime,
  stopped_at: DateTime,
  reauction_started_at: DateTime
}
```

#### `chat_messages`
```javascript
{
  _id: ObjectId,
  user_id: String,
  user_email: String,
  team_id: String,
  sender_name: String,
  sender_type: String, // "admin", "team", "user"
  message: String,
  room: String, // "global", "admin", "team_{id}"
  timestamp: DateTime,
  edited: Boolean,
  deleted: Boolean,
  deleted_at: DateTime
}
```

#### `wishlist`
```javascript
{
  _id: ObjectId,
  user_id: String,
  team_id: String,
  player_id: String,
  player_name: String,
  priority: Int, // 1=High, 2=Medium, 3=Low
  max_bid: Float,
  added_at: DateTime,
  notified: Boolean
}
```

#### `security_events`
```javascript
{
  _id: ObjectId,
  timestamp: DateTime,
  type: String, // "brute_force_detected", "sql_injection_attempt", etc.
  severity: String, // "low", "medium", "high", "critical"
  ip: String,
  details: Object
}
```

#### `blocked_ips`
```javascript
{
  _id: ObjectId,
  ip: String,
  reason: String,
  severity: String,
  blocked_at: DateTime,
  expires_at: DateTime,
  duration_hours: Int
}
```

#### `activity_logs`
```javascript
{
  _id: ObjectId,
  type: String, // "undo_sold", etc.
  player_id: String,
  player_name: String,
  team_id: String,
  team_name: String,
  refund_amount: Float,
  admin_id: String,
  admin_email: String,
  timestamp: DateTime
}
```

---

## 🔒 Security Features

### Multi-Layer Security Architecture

#### Layer 1: Network & Request Level
- **HTTPS Redirect:** Automatic HTTPS enforcement behind proxy
- **Security Headers:** CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Request Validation:** Size limits (10MB), suspicious pattern detection
- **IP Blocking:** Automatic blocking of malicious IPs
- **Rate Limiting:** Token bucket algorithm with configurable limits

#### Layer 2: Authentication & Authorization
- **JWT Tokens:** Short-lived access tokens (15 min), refresh tokens (1 day)
- **Session Management:** 30-min inactivity timeout, 8-hour max duration
- **Token Blacklisting:** Logout invalidates tokens
- **IP Validation:** Session tied to IP address
- **Role-Based Access:** Admin, Team Member, Viewer roles
- **Route Guards:** Middleware-based route protection

#### Layer 3: Threat Detection
- **Brute Force Detection:** 5 failed logins = auto-block (1 hour)
- **SQL Injection Detection:** Pattern matching, auto-block (72 hours)
- **XSS Detection:** Script tag detection, auto-block (24 hours)
- **Path Traversal Detection:** Directory traversal attempts, auto-block (48 hours)
- **Security Event Logging:** All threats logged to database

#### Layer 4: Data Protection
- **Password Hashing:** Bcrypt with salt
- **Password Validation:** 8+ chars, uppercase, lowercase, digit
- **PII Sanitization:** Automatic redaction in logs
- **Audit Logging:** Security-sensitive operations logged
- **Data Retention:** 90-day security event retention

#### Layer 5: Performance & Availability
- **Response Compression:** GZip for responses >1KB
- **ETag Caching:** 304 Not Modified responses
- **Static Asset Optimization:** Long-term caching for versioned assets
- **Connection Pooling:** WebSocket connection reuse
- **Heartbeat Monitoring:** 15-second ping/pong

### Security Configuration

**Environment Variables:**
```bash
# JWT
JWT_SECRET=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=1

# Security Toggles
ENABLE_RATE_LIMITING=true
ENABLE_CSRF_PROTECTION=false  # Disabled for API
ENABLE_IP_WHITELIST=false
ADMIN_IP_WHITELIST=1.2.3.4,5.6.7.8

# Redis (for sessions)
REDIS_URL=redis://localhost:6379/0
```

### Security Monitoring Dashboard

**Available Metrics:**
- Total security events (24h)
- Events by type (brute force, SQL injection, XSS, etc.)
- Events by severity (low, medium, high, critical)
- Top attacking IPs
- Blocked IPs count
- Active violations per IP

**Admin Actions:**
- View blocked IPs
- Manually unblock IP
- View security event history
- Export security logs

---

## ⚡ Real-Time Features

### WebSocket Architecture

**Connection Flow:**
1. Client connects to `/auction/ws`
2. Optional authentication via query param or first message
3. Connection registered with unique ID
4. User added to appropriate rooms (global, team-specific)
5. Heartbeat starts (15s interval)
6. Client receives real-time updates

**Message Types:**
- `connected` - Welcome message
- `ping/pong` - Heartbeat
- `bid_placed` - New bid notification
- `player_sold` - Player sold event
- `player_unsold` - Player unsold event
- `current_player_changed` - Auction player change
- `auction_status` - Auction started/stopped
- `timer_update` - Countdown timer (1s interval)
- `team_update` - Team budget update
- `chat_message` - Chat message
- `chat_message_deleted` - Message deleted
- `player_live` - Player set live
- `player_undo` - Undo sold player

**Optimization Features:**
- Message compression for payloads >1KB
- Room-based broadcasting (reduce unnecessary messages)
- Connection pooling and reuse
- Automatic dead connection cleanup
- Selective broadcasting (exclude sender)

### Timer System

**Auction Timer:**
- Default: 30 seconds
- Resets on new bid
- Auto-closes auction on expiry
- Broadcasts every second
- Callback on completion

**Auto-Close Behavior:**
- If bids exist: Mark player as SOLD
- If no bids: Mark player as UNSOLD
- Update team statistics
- Broadcast final status
- Clear current player

---

## 🎨 Frontend Features

### HTML Templates (`templates/`)

#### `index.html`
**Purpose:** Player registration page
- Public player self-registration form
- Image upload support
- Role and category selection
- Responsive design

#### `admin_fresh.html`
**Purpose:** Admin dashboard
- Dashboard statistics with charts
- Player approval workflow
- Live auction control
- Team management
- User management
- Activity logs
- Export functionality

#### `live_studio.html`
**Purpose:** Hollywood cinematic live auction studio
- Real-time bidding interface
- Countdown timer display
- Current player showcase
- Bid history
- Team leaderboard
- Chat integration
- Sound effects

#### `team_dashboard_new.html`
**Purpose:** Team dashboard
- Purchased players list
- Remaining budget display
- Bidding interface
- Wishlist management
- Team statistics

#### `user_dashboard.html`
**Purpose:** User dashboard
- Role-based action options
- Navigation to appropriate dashboards
- User profile information

### JavaScript Files (`static/`)

#### `admin.js`
**Purpose:** Admin dashboard logic
- Dashboard statistics rendering
- Player approval/rejection
- Base price setting
- User-team assignment
- Activity log display

#### `admin_teams.js`
**Purpose:** Team management UI
- Team CRUD operations
- Team list display
- Logo upload
- Budget management

#### `live_studio.js`
**Purpose:** Live auction studio logic
- WebSocket connection management
- Real-time bid updates
- Timer display
- Player showcase
- Bid placement
- Sound effects trigger

#### `team_dashboard_new.js`
**Purpose:** Team dashboard logic
- Player list rendering
- Budget tracking
- Bid placement
- Wishlist integration

#### `chat.js`
**Purpose:** Chat interface
- Real-time messaging
- Room switching
- Message history
- Delete messages

#### `wishlist.js`
**Purpose:** Wishlist functionality
- Add/remove players
- Priority management
- Max bid setting
- Live status updates

#### `comparison.js`
**Purpose:** Player comparison UI
- Team comparison
- Squad analysis
- Statistics visualization

#### `cinematic-effects.js`
**Purpose:** Visual effects for live auction
- Animations
- Transitions
- Particle effects

#### `lazy-loader.js`
**Purpose:** Lazy loading optimization
- Image lazy loading
- Content lazy loading
- Performance optimization

#### `realtime-optimizer.js`
**Purpose:** WebSocket optimization
- Connection management
- Message batching
- Reconnection logic

#### `ux-enhancements.js`
**Purpose:** UX improvements
- Toast notifications
- Loading spinners
- Smooth scrolling
- Form validation

#### `service-worker.js`
**Purpose:** PWA service worker
- Offline support
- Cache management
- Background sync

### CSS Files (`static/`)

#### `skit-pro.css`
**Purpose:** Main application styles
- Global styles
- Component styles
- Responsive design
- Dark mode support

#### `features.css`
**Purpose:** Feature-specific styles
- Auction-specific styles
- Dashboard styles
- Form styles

#### `mobile-optimized.css`
**Purpose:** Mobile responsive styles
- Mobile-first design
- Touch-friendly UI
- Responsive breakpoints

#### `player-cards.css`
**Purpose:** Player card styling
- Card layout
- Image display
- Badge styles
- Hover effects

---

## 📦 Deployment Configuration

### Railway Deployment

#### `Procfile`
```
web: gunicorn main_new:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
```

#### `railway.json`
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn main_new:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### `runtime.txt`
```
python-3.11
```

### Environment Variables (Railway)

**Required:**
```bash
MONGODB_URL=mongodb+srv://...
JWT_SECRET=your-secret-key-here
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

**Optional:**
```bash
REDIS_URL=redis://...
ADMIN_EMAILS=admin@example.com
CORS_ORIGINS=*
ENABLE_RATE_LIMITING=true
LOG_LEVEL=INFO
```

### Docker Support

**Dockerfile:** Not present (uses Railway's Nixpacks)
**Docker Compose:** Not present

---

## 🚀 Application Startup Flow

### `main_new.py` - Application Entry Point

#### Lifespan Events

**Startup:**
1. Log application info (name, version, environment)
2. Setup PII sanitization for logs
3. Start rate limiter cleanup task
4. Start session cleanup task (every 5 minutes)
5. Start security monitoring cleanup (every hour)
6. Create database indexes
7. Run database migration for new fields
8. Log startup complete

**Shutdown:**
1. Log shutdown message
2. Cleanup tasks automatically cancelled

#### Middleware Stack (Order Matters!)

1. **HTTPS Redirect** - Ensure HTTPS behind proxy
2. **Performance Tracking** - Measure total time
3. **Integrated Security** - IP blocking, threat detection
4. **Security Event Logging** - Log security events
5. **Strict Authentication** - Validate JWT
6. **Security Headers** - Add security headers
7. **Request Validation** - Validate requests
8. **Audit Logging** - Log sensitive operations
9. **IP Whitelist** - Optional admin IP whitelist
10. **CORS** - Cross-origin resource sharing
11. **ETag** - Caching support
12. **Static Asset Optimization** - Cache control
13. **Response Compression Optimization** - Optimize compression
14. **GZip** - Response compression (last)

#### Routes

**HTML Pages:**
- `GET /` - Player registration page
- `GET /live` - Live auction studio
- `GET /admin` - Admin dashboard
- `GET /team/dashboard` - Team dashboard
- `GET /user/dashboard` - User dashboard

**API Routers:**
- `/auth` - Authentication
- `/players` - Player management
- `/teams` - Team management
- `/auction` - Auction and bidding
- `/admin` - Admin operations
- `/reports` - Export functionality
- `/viewer` - Viewer endpoints
- `/chat` - Chat functionality
- `/wishlist` - Wishlist management
- `/comparison` - Team comparison
- `/health`, `/metrics`, `/stats` - Monitoring

**Special Endpoints:**
- `GET /health` - Health check
- `GET /debug/auth` - Debug authentication
- `GET /service-worker.js` - PWA service worker

---

## 📊 Key Metrics & Limits

### Performance Targets
- Response time: <200ms (p95)
- WebSocket latency: <50ms
- Database query: <100ms
- Image upload: <5s

### Limits
- Max file upload: 5MB (players), 2MB (logos)
- Max request size: 10MB
- Max WebSocket connections: 1000
- Session timeout: 30 minutes inactivity
- Max session duration: 8 hours
- Rate limits:
  - API: 100 requests/minute
  - Bids: 10 bids/minute
  - Auth: 10 attempts/5 minutes

### Auction Settings
- Default timer: 30 seconds
- Minimum bid increment: ₹50
- Auto-close on timer expiry: Yes
- Auto-reset timer on bid: Yes

---

## 🔧 Maintenance & Operations

### Database Maintenance

**Indexes:**
- `users.email` (unique)
- `bid_history.player_id, timestamp` (compound)
- `bid_history.team_id`
- `players.role`
- `players.category`
- `players.status`
- `players.auction_round`

**Cleanup Tasks:**
- Session cleanup: Every 5 minutes
- Security event cleanup: Every hour (90-day retention)
- Blocked IP cleanup: Every hour
- Rate limiter cleanup: Every 5 minutes

### Monitoring

**Health Checks:**
- `/health` - Basic health
- `/health/detailed` - Comprehensive health
- `/metrics` - Prometheus metrics

**Logs:**
- Structured logging with timestamps
- PII sanitization enabled
- Log level: INFO (configurable)
- Slow request logging (>1s)

### Backup & Recovery

**Database Backup:**
- MongoDB Atlas automatic backups (if using Atlas)
- Manual backup: `mongodump`

**Image Backup:**
- Cloudinary automatic backups
- Download via Cloudinary API

---

## 🎯 Future Enhancement Opportunities

### Not Yet Implemented
1. Email notifications (SMTP integration)
2. SMS notifications (Twilio integration)
3. Slack/Discord webhooks for alerts
4. Advanced analytics dashboard
5. Player performance tracking
6. Historical auction data analysis
7. Mobile app (React Native)
8. Video streaming integration
9. Multi-language support (i18n)
10. Advanced search with Elasticsearch

### Potential Improvements
1. GraphQL API alongside REST
2. Server-side rendering (SSR)
3. Progressive Web App (PWA) enhancements
4. Offline mode support
5. Real-time collaboration features
6. AI-powered bid recommendations
7. Automated testing suite
8. CI/CD pipeline
9. Load testing and benchmarking
10. Documentation site (Docusaurus)

---

## 📝 Development Guidelines

### Adding New Features

**Before implementing:**
1. Check this document for existing functionality
2. Search codebase for similar implementations
3. Review existing patterns and conventions
4. Consider security implications
5. Plan database schema changes

**Implementation checklist:**
1. Create/update schemas in `schemas/`
2. Implement business logic in `services/`
3. Create API endpoints in `routers/`
4. Add authentication/authorization
5. Implement rate limiting if needed
6. Add logging and monitoring
7. Update this documentation
8. Test thoroughly

### Code Conventions

**Python:**
- PEP 8 style guide
- Type hints for function signatures
- Docstrings for modules and functions
- Async/await for I/O operations

**JavaScript:**
- ES6+ syntax
- Async/await for promises
- Descriptive variable names
- Comments for complex logic

**Database:**
- Use ObjectId for references
- Index frequently queried fields
- Use aggregation for complex queries
- Validate data before insertion

---

## 📚 Additional Documentation

- `README.md` - Project overview and quick start
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `RAILWAY_DEPLOYMENT.md` - Railway-specific deployment
- `PRODUCTION_READY_CHECKLIST.md` - Pre-deployment checklist
- `PASSWORD_REQUIREMENTS.md` - Password policy
- `TECH_STACK_EXPLAINED.md` - Technology stack details

---

**End of Project Analysis**  
**Last Updated:** 2026-03-13  
**Version:** 1.0.0
