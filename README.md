# Setup Backend (FastAPI + LangGraph)
🧩 Create a Python virtual environment
python -m venv venv
source venv/bin/activate   # on macOS/Linux
venv\Scripts\activate 

# Install dependencies
pip install -r requirements.txt

# Create a .env file in the project root
touch .env

# Add the following variables inside .env:

HUGGINGFACEHUB_API_TOKEN="xyz"
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT='xyz'
LANGCHAIN_API_KEY='xyz'
LANGCHAIN_PROJECT='Chatbot-project'

# Run the Backend Server

uvicorn main:app --reload

# Your backend will start on:

http://127.0.0.1:8000
