# CodeClinic

CodeClinic is a hybrid coding-support platform that combines persistent AI conversations with live human collaboration.

Instead of giving you a one-off answer, each coding problem becomes a shared thread:

- the AI keeps conversational memory for follow-up questions
- human contributors can post solutions in real time
- problem owners can accept the best community contribution
- admins can monitor usage and resolution trends from a reports dashboard

## Why CodeClinic

Most developer-support tools do one thing well:

- AI tools are fast, but often isolated
- community forums are insightful, but slower

CodeClinic brings both together in one workflow so a user can start with AI guidance and continue with live human insight inside the same problem thread.

## Core Features

- Persistent AI problem threads using `google.genai`
- Real-time human collaboration with Django Channels and WebSockets
- Votes, comments, and accepted contributions
- Email-based authentication and password reset
- User profiles and admin analytics dashboard
- Docker-ready deployment setup with PostgreSQL, Redis, and Celery support

## Tech Stack

- Python `3.13`
- Django `5.2`
- Django Channels
- Redis / `channels-redis`
- Celery
- Google GenAI
- SQLite for local development
- PostgreSQL for production
- WhiteNoise for static files
- Docker + Docker Compose

## Project Structure

```text
CodeClinic/
├── Dockerfile
├── docker-compose.yml
├── README.md
├── core/
│   ├── manage.py
│   ├── requirements.txt
│   ├── core/
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── urls.py
│   │   └── settings/
│   └── main/
│       ├── models.py
│       ├── views.py
│       ├── consumers.py
│       ├── services/
│       ├── templates/
│       └── static/
└── generated_docs/
```

## Domain Model

The system is built around a clean split between AI and community collaboration:

- `Problem`: the main coding issue submitted by a user
- `Thread`: the persistent AI conversation container for a problem
- `Message`: user and assistant chat turns in the AI thread
- `Solution`: human contribution posted by another user
- `Comment`: discussion attached to a human contribution
- `Vote`: upvote/downvote on a contribution
- `ProblemPresence`: tracks active users in a thread
- `EmailLog`: stores authentication email delivery outcomes

## How It Works

### 1. Problem submission

An authenticated user submits a coding problem.  
The system creates:

- a `Problem`
- a linked `Thread`
- an initial user `Message`
- an AI assistant `Message`

### 2. AI follow-up

The problem owner can continue the AI chat.  
Previous thread messages are passed back to the model so the AI keeps context.

### 3. Human collaboration

Other users can post human contributions.  
New contributions are broadcast live over WebSockets and appear instantly in the UI.

### 4. Resolution

The problem owner can mark one human contribution as accepted, allowing the thread to be treated as resolved.

## Local Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd CodeClinic
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r core/requirements.txt
```

### 4. Configure environment variables

```bash
cp core/.env.example core/.env
```

Update `core/.env` with your values, especially:

- `SECRET_KEY`
- `GENAI_API_KEY`
- `EMAIL_HOST`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

## Run Locally

### Apply migrations

```bash
cd core
../venv/bin/python manage.py migrate
```

### Start the app

```bash
../venv/bin/python -m uvicorn core.asgi:application --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Redis in Development

CodeClinic is configured to work locally even when Redis is not running.

- local development can fall back to an in-memory channel layer
- production should use Redis for WebSocket backplane and Celery broker

If you want Redis-backed channels locally, enable it in `core/.env`:

```env
USE_REDIS_CHANNELS=true
REDIS_URL=redis://127.0.0.1:6379/1
```

## Create an Admin User

```bash
cd core
../venv/bin/python manage.py createsuperuser
```

## Run Tests

```bash
./venv/bin/python core/manage.py test main
./venv/bin/python core/manage.py check
```

## Docker

The project includes:

- `web` service
- `worker` service
- `db` service
- `redis` service

To build and run:

```bash
docker-compose up --build
```

## Reports Dashboard

The admin reports dashboard provides visibility into:

- total problems
- AI-assisted threads
- human contribution volume
- resolution rate
- active contributors
- most active problem threads

## Documentation

Project PDFs generated for the final year project include:

- Project Proposal
- SRS
- SDD
- Test Plan
- UML / ER / System Design Diagrams
- Project Overview

## Future Improvements

- mention notifications
- richer moderation tools
- async AI task queue integration
- better thread search and filtering
- contribution reputation scoring

## License

This project is intended for academic and educational use unless you define another license for publication.
