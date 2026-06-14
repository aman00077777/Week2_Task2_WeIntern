import os
import csv
import io
from flask import Flask, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename
import resume_parser

app = Flask(__name__)
app.secret_key = 'resume_screening_secret_key_12345'

# Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
SAMPLE_JOBS_FOLDER = os.path.join('data', 'sample_jobs')
SAMPLE_RESUMES_FOLDER = os.path.join('data', 'sample_resumes')
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Load sample job descriptions
    job_templates = {}
    if os.path.exists(SAMPLE_JOBS_FOLDER):
        for file in os.listdir(SAMPLE_JOBS_FOLDER):
            if file.endswith('.txt'):
                name = file.replace('.txt', '').replace('_', ' ').title()
                with open(os.path.join(SAMPLE_JOBS_FOLDER, file), 'r', encoding='utf-8') as f:
                    job_templates[name] = f.read()

    # Load list of sample resumes
    sample_resumes = []
    if os.path.exists(SAMPLE_RESUMES_FOLDER):
        for file in os.listdir(SAMPLE_RESUMES_FOLDER):
            if file.endswith(('.pdf', '.txt')):
                sample_resumes.append({
                    'filename': file,
                    'name': file.replace('.pdf', '').replace('.txt', '').replace('_', ' ').title()
                })

    return render_template('index.html', job_templates=job_templates, sample_resumes=sample_resumes)

@app.route('/analyze', methods=['POST'])
def analyze():
    job_description = request.form.get('job_description', '').strip()
    if not job_description:
        return jsonify({'error': 'Job description is required.'}), 400

    results = []
    
    # Track files uploaded
    uploaded_files = request.files.getlist('resumes')
    
    # Track sample resumes selected
    selected_samples = request.form.getlist('selected_samples')

    # Process sample resumes
    for filename in selected_samples:
        file_path = os.path.join(SAMPLE_RESUMES_FOLDER, filename)
        if os.path.exists(file_path):
            # Read text
            if filename.endswith('.pdf'):
                text = resume_parser.extract_text_from_pdf(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            analysis = resume_parser.analyze_resume(text, job_description)
            analysis['source'] = 'Sample'
            analysis['filename'] = filename
            results.append(analysis)

    # Process uploaded resumes
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Read text
            if filename.endswith('.pdf'):
                text = resume_parser.extract_text_from_pdf(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            # Clean up uploaded file immediately or leave for verification
            # Let's keep it for verification
            analysis = resume_parser.analyze_resume(text, job_description)
            analysis['source'] = 'Uploaded'
            analysis['filename'] = filename
            results.append(analysis)

    if not results:
        return jsonify({'error': 'No valid resumes uploaded or selected.'}), 400

    # Rank resumes by final score descending
    ranked_results = sorted(results, key=lambda x: x['final_score'], reverse=True)

    # Store in session for download
    session['last_results'] = ranked_results
    
    return jsonify({'candidates': ranked_results})

@app.route('/download-report', methods=['GET'])
def download_report():
    ranked_results = session.get('last_results')
    if not ranked_results:
        # Fallback to general report if session is empty or expired
        return "No report data found. Please run an analysis first.", 404

    # Create CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Headers
    cw.writerow([
        'Rank', 'Candidate Name', 'Email', 'Phone', 'Match Score (%)', 
        'Matched Skills', 'Missing Skills', 'Years of Experience', 'Summary Report'
    ])
    
    for idx, candidate in enumerate(ranked_results, 1):
        cw.writerow([
            idx,
            candidate.get('name', 'Candidate'),
            candidate.get('email', 'N/A'),
            candidate.get('phone', 'N/A'),
            candidate.get('final_score', 0.0),
            ", ".join(candidate.get('matched_skills', [])),
            ", ".join(candidate.get('missing_skills', [])),
            candidate.get('experience_years', 0),
            candidate.get('summary', '')
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=candidate_ranking_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def make_response(content):
    # Flask helper
    from flask import make_response as flask_make_response
    return flask_make_response(content)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
