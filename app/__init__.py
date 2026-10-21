from flask import Flask
from flask_cors import CORS
from config import Config
from app.database import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Wix ve harici sitelerden API istekleri gelebilmesi için tam CORS desteği
    CORS(app)

    # Wix iframe gömmelerine izin veren güvenlik başlıkları
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'ALLOWALL'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        return response

    # Veritabanını başlat
    with app.app_context():
        init_db()

    # Rotaları bağla
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
