from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from sqlalchemy.sql import func

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost/job_listings_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    location_country = db.Column(db.String(100), nullable=False)
    location_city = db.Column(db.String(100), nullable=False)
    salary_range = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    posted_time = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# Endpoint to get unique countries, cities, and companies with counts
@app.route('/filters', methods=['GET'])
def get_filters():
    # Get unique countries with counts
    countries = db.session.query(Job.location_country, func.count(Job.id).label('count'))\
        .group_by(Job.location_country).all()
    countries_dict = {country: count for country, count in countries}

    # Get unique cities with counts
    cities = db.session.query(Job.location_city, func.count(Job.id).label('count'))\
        .group_by(Job.location_city).all()
    cities_dict = {city: count for city, count in cities}

    # Get unique companies with counts
    companies = db.session.query(Job.company, func.count(Job.id).label('count'))\
        .group_by(Job.company).all()
    companies_dict = {company: count for company, count in companies}

    return jsonify({
        'countries': countries_dict,
        'cities': cities_dict,
        'companies': companies_dict
    })

@app.route('/jobs', methods=['GET'])
def get_jobs():
    sort_by = request.args.get('sort_by', 'posted_time')
    order = request.args.get('order', 'desc')
    filters = {
        key: request.args[key] for key in request.args 
        if key in ['location_country', 'location_city', 'company']
    }

    query = Job.query.filter_by(**filters)
    if sort_by in ['title', 'company', 'location_country', 'location_city', 'posted_time']:
        if order == 'asc':
            query = query.order_by(getattr(Job, sort_by).asc())
        else:
            query = query.order_by(getattr(Job, sort_by).desc())
    jobs = query.all()

    jobs_list = [
        {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location_country': job.location_country,
            'location_city': job.location_city,
            'salary_range': job.salary_range,
            'tags': job.tags.split(',') if job.tags else [],
            'posted_time': (datetime.utcnow() - job.posted_time).total_seconds() // 3600
        } for job in jobs
    ]
    return jsonify(jobs_list)

@app.route('/jobs', methods=['POST'])
def add_job():
    data = request.get_json()
    required_fields = ['title', 'company', 'location_country', 'location_city']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    new_job = Job(
        title=data['title'],
        company=data['company'],
        location_country=data['location_country'],
        location_city=data['location_city'],
        salary_range=data.get('salary_range'),
        tags=','.join(data.get('tags', []))
    )
    db.session.add(new_job)
    db.session.commit()
    return jsonify({'message': 'Job added successfully'}), 201

@app.route('/jobs/<int:id>', methods=['PUT'])
def update_job(id):
    job = Job.query.get(id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    data = request.get_json()
    required_fields = ['title', 'company', 'location_country', 'location_city']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    job.title = data['title']
    job.company = data['company']
    job.location_country = data['location_country']
    job.location_city = data['location_city']
    job.salary_range = data.get('salary_range')
    job.tags = ','.join(data.get('tags', []))
    db.session.commit()
    return jsonify({'message': 'Job updated successfully'})

@app.route('/jobs/<int:id>', methods=['DELETE'])
def delete_job(id):
    job = Job.query.get(id)
    if job:
        db.session.delete(job)
        db.session.commit()
        return jsonify({'message': 'Job deleted successfully'})
    return jsonify({'error': 'Job not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)