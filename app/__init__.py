import os

from flask import Flask


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "repasse.sqlite"),
    )
    os.makedirs(app.instance_path, exist_ok=True)

    from . import db, routes

    db.init_app(app)
    app.register_blueprint(routes.bp)
    return app
