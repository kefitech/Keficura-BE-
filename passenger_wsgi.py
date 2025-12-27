import sys
import os

# Add project directory to Python path
sys.path.insert(0, '/home/qbvntafpy1x0/Django_back_end/backend')

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hospital_project.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
