from flask import Flask, render_template, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional
from datetime import date
from flask_sqlalchemy import SQLAlchemy
import os


# Create the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET", "default_key_used_for_dev")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///job_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

STATUS_CHOICES = [
    ('Waiting for Response', 'Waiting for Response'),
    ('Interviewing', 'Interviewing'),
    ('Rejected Application', 'Rejected Application'),
    ('Ghosted Application', 'Ghosted Application')
]

RESUME_CHOICES = [
    ('Default Resume', 'Default Resume')
]

JOBS_LIST = []

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(200), nullable=False)
    resume_used = db.Column(db.String(100), nullable=False)
    job_url = db.Column(db.String(500), nullable=True)
    job_description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    salary = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Job {self.company} - {self.position}>'

class JobForm(FlaskForm):
    application_date = DateField("Application Date", validators=[DataRequired()], default=date.today)
    status = SelectField("Status", choices=STATUS_CHOICES)
    company = StringField('Company Name', validators=[DataRequired()])
    position = StringField('Job Title', validators=[DataRequired()])
    resume_used = SelectField("Resume Used", choices=RESUME_CHOICES, validators=[DataRequired()])
    job_url = StringField("Job URL", validators=[Optional()])
    job_description = TextAreaField('Job Description', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    salary = StringField("Salary", validators=[Optional()])
    submit = SubmitField('Add Job')

@app.route('/')
def home():
    # Dashboard stats
    total_jobs = Job.query.count()
    recent_jobs = Job.query.order_by(Job.application_date.desc()).limit(5).all()
    
    # Status counts
    statuses = {}
    for status_choice in STATUS_CHOICES:
        status = status_choice[0]
        count = Job.query.filter_by(status=status).count()
        if count > 0:
            statuses[status] = count
    
    return render_template('dashboard.html', 
                         title="Dashboard", 
                         total_jobs=total_jobs,
                         recent_jobs=recent_jobs,
                         statuses=statuses)

@app.route('/jobs')
def jobs():
    # Get filter parameter from URL
    status_filter = request.args.get('status')

    if status_filter:
        # Filter by status
        all_jobs = Job.query.filter_by(status=status_filter).order_by(Job.application_date.desc()).all()
    else:
        # Show all jobs
        all_jobs = Job.query.order_by(Job.application_date.desc()).all()

    return render_template('jobs.html', title="Jobs", jobs=all_jobs)

@app.route('/add-job', methods=["GET", "POST"])
def add_job():
    form = JobForm() # Take out job form class
    if form.validate_on_submit(): # Check if validation passes
        new_job = Job(
            application_date = form.application_date.data,
            status = form.status.data,
            company = form.company.data,
            position = form.position.data,
            resume_used = form.resume_used.data,
            job_url = form.job_url.data,
            job_description = form.job_description.data,
            notes = form.notes.data,
            salary = form.salary.data
        )

        # Save to db
        db.session.add(new_job)
        db.session.commit()
        return redirect(url_for('jobs')) 

    return render_template('add_job.html', form=form, title="Add Job")

@app.route("/job/<int:job_id>")
def job_details(job_id):
    # Get job by ID, or return 404 if not found
    job = Job.query.get_or_404(job_id)
    return render_template("job_details.html", job=job, job_id=job_id)

@app.route("/job/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    # Get job or return 404
    job = Job.query.get_or_404(job_id)
    form = JobForm()

    if form.validate_on_submit():
        # Update the existing job with new data
        job.application_date = form.application_date.data
        job.status = form.status.data
        job.company = form.company.data
        job.position = form.position.data
        job.resume_used = form.resume_used.data
        job.job_url = form.job_url.data
        job.job_description = form.job_description.data
        job.notes = form.notes.data
        job.salary = form.salary.data

        # Save changes in db
        db.session.commit() 
        return redirect(url_for('job_details', job_id=job_id))
    
    # Pre-populate form with existing data (on GET request)
    if not form.is_submitted():
        form.application_date.data = job.application_date
        form.status.data = job.status
        form.company.data = job.company
        form.position.data = job.position
        form.resume_used.data = job.resume_used
        form.job_url.data = job.job_url
        form.job_description.data = job.job_description
        form.notes.data = job.notes
        form.salary.data = job.salary
    
    return render_template('edit_job.html', form=form, job=job, job_id=job_id)

@app.route("/testpage")
def test_page():
    return "This page is only a test"


# Health Checks
@app.route("/healthz/live")
def health_live():
    return "OK", 200

@app.route("/healthz/readiness")
def health_readiness():
    try:
        # Create connection, simple query
        with db.engine.connect() as connection:
            connection.execute(db.text("SELECT 1"))
        return "OK", 200
    except Exception:
        return "Not Ready", 500

def create_tables():
    """Create database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created!")

if __name__ == '__main__':
    create_tables()  # Create tables when app starts
    app.run(debug=True, host='0.0.0.0', port=8080)
