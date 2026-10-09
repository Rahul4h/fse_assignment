# FSE Production Event Processing Dashboard

Full Stack Engineering Practical Assessment — Production Event Processing Dashboard + MQTT Device Integration.

## 🚀 Stack
- **Backend:** Django 5.x + Django REST Framework
- **Database:** SQLite (development) / PostgreSQL (production)
- **MQTT:** paho-mqtt
- **Frontend:** Vanilla HTML/CSS/JS dashboard

## 📋 Prerequisites
- Python 3.11+
- pip + virtualenv
- (Optional) PostgreSQL for production

## 🛠️ Setup

```bash
# 1. Create virtualenv
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate    # Linux/Mac

# 2. Install dependencies
pip install django djangorestframework paho-mqtt psycopg2-binary

# 3. Run migrations
cd config
python manage.py makemigrations
python manage.py migrate

# 4. Create superuser (for admin)
python manage.py createsuperuser