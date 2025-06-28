#!/bin/bash

# ContactGraph startup script

echo "🚀 Starting ContactGraph..."
echo

# Check if backend .env file exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  No backend/.env file found. Creating from template..."
    echo "# Google OAuth credentials" > backend/.env
    echo "GOOGLE_CLIENT_ID=your_google_client_id_here" >> backend/.env
    echo "GOOGLE_CLIENT_SECRET=your_google_client_secret_here" >> backend/.env
    echo "" >> backend/.env
    echo "# Local Neo4j Database (default settings)" >> backend/.env
    echo "NEO4J_URI=bolt://localhost:7687" >> backend/.env
    echo "NEO4J_USER=neo4j" >> backend/.env
    echo "NEO4J_PASSWORD=neo4j" >> backend/.env
    echo "✅ Created backend/.env file. Please edit it with your Google OAuth credentials."
    echo "   GOOGLE_CLIENT_ID=your_google_client_id_here"
    echo "   GOOGLE_CLIENT_SECRET=your_google_client_secret_here"
    echo "   (Neo4j settings are configured for local instance)"
    echo
    echo "❌ Cannot start without OAuth credentials. Please:"
    echo "   1. Edit backend/.env file with your credentials"
    echo "   2. Run this script again"
    exit 1
fi

# Check OAuth credentials
if grep -q "your_google_client_id_here" backend/.env; then
    echo "❌ Please configure your Google OAuth credentials in backend/.env"
    echo "   Edit backend/.env and replace the placeholder values"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "backend/.venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    /Users/luka512/.local/bin/uv venv --python 3.10
    cd ..
fi

# Check if backend dependencies are installed
if [ ! -f "backend/.venv/lib/python*/site-packages/fastapi" ]; then
    echo "📦 Installing backend dependencies..."
    cd backend
    /Users/luka512/.local/bin/uv pip install -r requirements.txt
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Check if root dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing root dependencies..."
    npm install
fi

echo "✅ All dependencies installed!"
echo
echo "🌐 Starting application..."
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:8080"
echo
echo "💡 Next steps:"
echo "   1. Make sure Neo4j Desktop is running (or Neo4j server on localhost:7687)"
echo "   2. Open http://localhost:8080 in your browser"
echo "   3. Click 'Connect Google' to authenticate"
echo "   4. Click 'Refresh' to sync your contacts"
echo "   5. Explore your contact graph!"
echo "   6. Use the 'Backup' button to download your data locally"
echo

# Start both backend and frontend
npm run dev
