#!/bin/sh

until pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER"; do
  echo "Waiting for database..."
  sleep 1
done

python manage.py makemigrations
python manage.py makemigrations counter
python manage.py migrate
python manage.py migrate counter

./load_fixtures.sh

echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@myproject.com', 'password')" | python manage.py shell

exec python manage.py runserver 0.0.0.0:8000