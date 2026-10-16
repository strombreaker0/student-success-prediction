import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_app import create_app
from flask_app.config import ProductionConfig, DevelopmentConfig

# Default to ProductionConfig unless FLASK_ENV explicitly set to development
env = os.environ.get('FLASK_ENV', 'production').strip().lower()
config_class = DevelopmentConfig if env == 'development' else ProductionConfig

app = create_app(config_class)

# Apply ProxyFix reverse-proxy middleware in production for Render HTTPS edge routing
if config_class == ProductionConfig:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Render and Gunicorn WSGI callable
application = app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
