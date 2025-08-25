import os
import random
import string
from flask import Flask, request, jsonify, redirect, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import desc
from flask_cors import CORS

# --- Application Setup ---

app = Flask(__name__)
CORS(app)

# --- DATABASE CONNECTION CHANGE ---
# The connection string has been updated from PostgreSQL to MySQL.
# Make sure to replace 'YOUR_LOCAL_PASSWORD' with your actual local MySQL root password.
# Make sure this line says 'mysql+pymysql'
db_uri = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:Ga321tor!@localhost/url_shortener')

if not db_uri:
    raise ValueError("DATABASE_URL environment variable not set and no default URI provided.")

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# --- Database Model (No changes needed here) ---

class Link(db.Model):
    """Represents a shortened link in the database."""
    __tablename__ = 'links'

    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(512), nullable=False)
    short_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    clicks = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Link {self.short_code}>'


# --- Core Logic (No changes needed here) ---

def generate_short_code(length=6):
    """Generates a random alphanumeric string of a specified length."""
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))

def create_unique_short_code():
    """Generates a unique short code by checking against the database."""
    with app.app_context():
        while True:
            short_code = generate_short_code()
            if not Link.query.filter_by(short_code=short_code).first():
                return short_code


# --- API Endpoints (No changes needed here) ---

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    """API endpoint to create a new short link."""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    original_url = data['url']
    short_code = create_unique_short_code()

    new_link = Link(original_url=original_url, short_code=short_code)

    try:
        db.session.add(new_link)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'Could not save to database'}), 500

    short_url = f"{request.host_url}{short_code}"
    return jsonify({'short_url': short_url}), 201


@app.route('/<string:short_code>')
def redirect_to_url(short_code):
    """
    Redirects a short code to its original URL and tracks the click.
    """
    link = Link.query.filter_by(short_code=short_code).first_or_404()
    link.clicks += 1
    db.session.commit()
    return redirect(link.original_url)


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """
    API endpoint to retrieve analytics data for all links.
    """
    links = Link.query.order_by(desc(Link.clicks)).all()
    analytics_data = []
    for link in links:
        analytics_data.append({
            'id': link.id,
            'original_url': link.original_url,
            'short_code': link.short_code,
            'short_url': f"{request.host_url}{link.short_code}",
            'clicks': link.clicks
        })
    return jsonify(analytics_data)


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error handler."""
    return jsonify(error="Short link not found"), 404


# --- Main execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)