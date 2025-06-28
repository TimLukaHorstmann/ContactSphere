![Under Development](https://img.shields.io/badge/status-under%20development-orange)
![Issues](https://img.shields.io/github/issues/luka512/contact-circle-vision)
![License](https://img.shields.io/github/license/luka512/contact-circle-vision)

# ContactSphere

The Ultimate Personal CRM: ContactSphere is your private, all-in-one solution for mastering your network. Transform your Google Contacts into a dynamic, interactive, and insightful relationship management system. Whether you're a professional, entrepreneur, or just someone who values meaningful connections, ContactSphere empowers you to visualize, organize, and leverage your network like never before.

## Features

- 🔐 **Google OAuth 2.0**: Secure read-only access to your Google Contacts
- 📊 **Interactive Graph**: Force-directed network visualization of your contacts
- 🔍 **Smart Relationships**: Automatically infers colleague, local, alumni, and other connections
- 🏷️ **Manual Tags**: Add custom tags like mentor, investor, family
- 📝 **List View**: Table view with search and uncategorized contact detection
- 💾 **Local Neo4j Database**: Graph database for optimal relationship storage
- 📁 **Local Backup**: Download your data as JSON files for safekeeping

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ and pip
- **Neo4j Desktop** (or Neo4j server running on localhost:7687)
- Google Cloud Console project with Contacts API enabled

### 1. Setup Neo4j

1. Download and install [Neo4j Desktop](https://neo4j.com/download/)
2. Create a new local database
3. Set username: `neo4j`, password: `neo4j` (or update in .env)
4. Start the database server (it should run on bolt://localhost:7687)

### 2. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the "People API" (Google Contacts)
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Application type: "Web application"
6. Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
7. Copy your Client ID and Client Secret

### 3. Install Dependencies

```bash
# Use the automated start script (recommended)
./start.sh

# OR manually:

# Install root dependencies (for concurrent dev)
npm install

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies  
cd ../frontend
npm install
```

### 4. Configure Environment

The start script will create a `.env` file automatically, but you can also create it manually:

```bash
# In backend/ directory, create .env file with:
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Local Neo4j Database (default settings)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j
```

### 5. Run the Application

```bash
# From project root - easiest way:
./start.sh

# OR manually start both services:
npm run dev
```

This will start:
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:8080`

### 6. First Use

1. Make sure Neo4j Desktop is running
2. Open `http://localhost:8080` in your browser
3. Click "Connect Google" to authenticate
4. Grant read-only access to your contacts
5. Click "Refresh" to sync your contacts
6. Explore the graph and list views!
7. Use "Backup" button to download your data locally

## Architecture

- **Frontend**: React + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: Python + FastAPI + Neo4j (graph database)
- **Graph**: D3.js for custom force-directed graph visualization
- **Auth**: Google OAuth 2.0 web flow
- **Database**: Local Neo4j instance for graph relationships

## Relationship Inference Rules

The app automatically detects relationships based on:

- **Colleagues**: Same organization/company
- **Locals**: Same city 
- **Country-mates**: Same country
- **Alumni**: Same school/university
- **Domain-mates**: Same email domain (non-consumer)
- **Birthday-buddies**: Same birthday (month/day)

## Scripts

- `npm run dev` - Start both frontend and backend
- `npm run dev:frontend` - Frontend only
- `npm run dev:backend` - Backend only  
- `npm run test` - Run backend tests
- `npm run install:all` - Install all dependencies

## Privacy

- All data stored locally in Neo4j database
- No external services except Google Contacts API
- Read-only access to your contacts
- No data leaves your machine
- Local JSON backups for data portability

## Project Structure

```
├── backend/           # FastAPI backend
│   ├── main.py       # API endpoints
│   ├── auth.py       # Google OAuth
│   ├── graph_database.py  # Neo4j operations
│   ├── backup_service.py  # Local backup/restore
│   ├── models.py     # Data models
│   └── tests/        # Unit tests
├── frontend/         # React frontend  
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
├── start.sh          # Automated setup script
└── README.md
```
