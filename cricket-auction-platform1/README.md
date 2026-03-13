# 🏏 Cricket Auction Platform

A production-ready, real-time cricket auction platform built with FastAPI, WebSocket, and MongoDB. Features live bidding, role-based access control, comprehensive dashboards, and export functionality.

## ✨ Features

### 🔐 Authentication & Security
- JWT-based authentication with access and refresh tokens
- Role-based access control (Admin, Team Member, Viewer)
- Password hashing with bcrypt
- Protected API routes
- WebSocket authentication
- Rate limiting for bids
- CORS configuration
- Environment-based configuration

### 🎯 Real-Time Live Auction System
- WebSocket-based live bidding
- Connection manager for multiple concurrent clients
- Live highest bid broadcast
- 30-second countdown timer (configurable)
- Auto-reset timer on new bids
- Auto-sell when timer ends
- Auto-mark unsold if no bids
- Race condition prevention
- Bid validation (minimum increment, budget checks)
- Sound effect trigger events

### 💰 Team Purse & Business Logic
- Team budget management
- Automatic purse deduction after winning bid
- Negative purse prevention
- Live purse updates via WebSocket
- Minimum bid increment logic
- Base price per player
- Player status tracking (Sold/Unsold/Available/In Auction)

### 📊 Advanced Dashboard
**Admin Dashboard:**
- Total players, sold, unsold statistics
- Total revenue tracking
- Team count and overview
- Live auction statistics
- Revenue graphs (Chart.js)
- Sold vs Unsold charts
- Category-wise revenue breakdown

**Team Dashboard:**
- Purchased players list
- Remaining purse display
- Total spent tracking
- Team composition by category

### 📜 Auction History System
- Complete bid history storage
- Bid timeline per player
- Team bid tracking
- Winner details
- Timestamp for every bid
- Activity logs

### 🗄️ Database & Models
- MongoDB with proper indexing
- Player ↔ Team relations
- Auction ↔ Player relations
- Bid ↔ Player ↔ Team relations
- Optimized queries
- Migration-ready structure

### 🎨 Professional UI/UX
- Modern card-based layout
- Responsive design (mobile-friendly)
- Dark mode toggle
- Animated bid updates
- Toast notifications
- Loading spinners
- Smooth transitions
- Clean dashboard layout
- Professional color theme
- Team logo upload support
- Player image upload support

### 📤 Export & Reports
- Export sold players to Excel/CSV
- Export auction summary
- Export team-wise reports
- Downloadable reports with timestamps

### 🚀 Deployment Ready
- Production configuration
- Structured logging system
- Docker support
- Docker Compose configuration
- Gunicorn/Uvicorn ready
- Health check endpoint
- Environment variable management

## 🏗️ Architecture

```
cricket-auction/
├── core/                    # Core configuration and security
│   ├── config.py           # Settings management
│   ├── security.py         # JWT & authentication
│   └── dependencies.py     # Dependency injection
├── models/                  # Data models
├── schemas/                 # Pydantic schemas
│   ├── user.py
│   ├── player.py
│   ├── team.py
│   ├── auction.py
│   └── bid.py
├── routers/                 # API routes
│   ├── auth.py             # Authentication endpoints
│   ├── players.py          # Player CRUD
│   ├── teams.py            # Team CRUD
│   ├── auction.py          # Auction & bidding
│   ├── admin.py            # Admin operations
│   └── reports.py          # Export functionality
├── services/                # Business logic
│   ├── auction_service.py  # Auction management
│   └── bid_service.py      # Bid processing
├── websocket/               # WebSocket management
│   └── manager.py          # Connection manager
├── database/                # Database connection
│   └── session.py
├── utils/                   # Utility functions
├── static/                  # Frontend assets
├── templates/               # HTML templates
├── tests/                   # Unit tests
├── main_new.py             # Application entry
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MongoDB 7.0+
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd cricket-auction
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**
```bash
# Development
uvicorn main_new:app --reload

# Production
uvicorn main_new:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Environment Variables

See `.env.example` for all configuration options:

```env
# Core Settings
JWT_SECRET=your-secret-key
DATABASE_URL=mongodb://localhost:27017
ADMIN_EMAILS=admin@example.com

# Auction Settings
BID_INCREMENT=50
AUCTION_TIMER_SECONDS=30
MAX_CONCURRENT_CONNECTIONS=1000
```

## 👥 User Roles

1. **Admin**: Full control over auction, players, teams
2. **Team Member**: Can bid for assigned team
3. **Viewer**: Read-only access to auction

## 🎯 Key Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token

### Auction
- `GET /auction/status` - Get auction status
- `POST /auction/start` - Start auction (Admin)
- `POST /auction/bid` - Place a bid
- `WS /auction/ws` - WebSocket connection

### Admin
- `GET /admin/dashboard/stats` - Dashboard statistics
- `GET /admin/players/pending` - Pending players
- `PATCH /admin/player/{id}/base-price` - Set base price

### Reports
- `GET /reports/export/sold-players` - Export sold players
- `GET /reports/export/team-summary` - Export team summary

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For support, email support@example.com or open an issue in the repository.