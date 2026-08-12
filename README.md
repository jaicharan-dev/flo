# Flo - Personal Finance API & AI Assistant

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![Database](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-336791)
![AI](https://img.shields.io/badge/AI-Google_Gemini_2.0-F9AB00)

**Flo** is a robust, modular, and AI-powered personal finance backend application built to handle user authentication, transaction management, advanced analytics, and AI-driven financial insights.

This repository focuses on backend engineering best practices, featuring a modular layered architecture, asynchronous AI integration, data integrity with Alembic migrations, and 100% test coverage using Pytest.

## 🚀 Key Features

### 1. Robust Architecture (Separation of Concerns)
The application is structured into clearly defined layers to maximize testability and maintainability:
- **Routers (`/routers`)**: Defines API endpoints, dependency injection (Auth), and request validation.
- **Services (`/services`)**: Contains core business logic (Transaction management, Analytics calculations).
- **Models & Schemas (`models.py`, `schemas.py`)**: Strict database models using SQLAlchemy and validation schemas using Pydantic.

### 2. Advanced Analytics Engine
Calculates deep financial insights efficiently using SQLAlchemy aggregations:
- **Budget vs. Actual:** Tracks utilization percentages across dynamic user-defined categories.
- **Statistical Outliers:** Automatically detects anomalous transactions using mathematically robust Interquartile Range (IQR) detection.
- **Rolling Averages & KPIs:** Computes real-time trends, month-over-month percentage changes, and net balances.

### 3. Asynchronous AI Assistant (`Gemini 2.0`)
Integrated with Google's GenAI SDK to provide personalized financial insights:
- Analyzes the user's transaction history contextually.
- Uses **Asynchronous I/O (`client.aio`)** to prevent blocking the FastAPI event loop, ensuring high throughput and preventing connection timeouts in production environments.

### 4. Database Migrations
- Uses **Alembic** to safely track, version, and apply schema changes.
- Complex data migrations successfully backfill relationships (e.g., scoping global categories to individual users).

## 🛠️ Technology Stack
- **Framework:** FastAPI
- **Database ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT (JSON Web Tokens) with Bcrypt password hashing
- **AI Integration:** Google Gemini GenAI SDK
- **Testing:** Pytest (100% Pass Rate using in-memory SQLite)
- **Deployment:** Render (Dockerized)

## ⚙️ Getting Started (Local Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jaicharan-dev/flo.git
   cd flo/flo-backend
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables (`.env`):**
   ```env
   DATABASE_URL=sqlite:///./test_flo.db
   SECRET_KEY=your-secure-secret-key
   GEMINI_API_KEY=your-google-gemini-key
   ```

4. **Run Database Migrations & Seed Data:**
   ```bash
   alembic upgrade head
   python seed_db.py  # Generates 180 days of realistic financial data
   ```

5. **Start the FastAPI Server:**
   ```bash
   uvicorn main:app --reload
   ```
   *Visit `http://localhost:8000/docs` to view the interactive Swagger API documentation.*

## 🧪 Testing
The project includes a comprehensive test suite covering authentication, database constraints, and service logic. Tests are run against a clean, isolated in-memory SQLite database.
```bash
pytest
```

## 🏗️ Future Enhancements
- Implementing Redis for caching intensive analytics queries.
- Expanding CI/CD pipelines (GitHub Actions) for automated testing on pull requests.
