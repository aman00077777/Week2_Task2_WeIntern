import re
import os
import pdfplumber
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure NLTK resources are downloaded
def setup_nltk():
    resources = ['punkt', 'punkt_tab', 'stopwords', 'wordnet', 'omw-1.4']
    for resource in resources:
        try:
            if resource == 'punkt_tab':
                nltk.data.find('tokenizers/punkt_tab')
            elif resource in ['stopwords', 'wordnet', 'omw-1.4']:
                nltk.data.find(f'corpora/{resource}')
            else:
                nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

setup_nltk()

# Comprehensive skill dictionary grouped by category
SKILL_DICTIONARY = {
    # Programming Languages
    'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'rust', 'go', 'sql', 'r', 'scala', 'shell', 'bash', 'html', 'css',
    # Frameworks & Libraries
    'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'next.js', 'nextjs', 'node.js', 'nodejs', 'express', 'spring boot', 'spring', 'rails', 'laravel', 'bootstrap', 'tailwind', 'jquery', 'redux',
    # Data Science & ML
    'pandas', 'numpy', 'scipy', 'scikit-learn', 'sklearn', 'tensorflow', 'pytorch', 'keras', 'matplotlib', 'seaborn', 'nltk', 'spacy', 'opencv', 'huggingface', 'transformers', 'machine learning', 'deep learning', 'nlp', 'computer vision', 'data analytics', 'neural networks',
    # AI & Generative AI
    'langchain', 'llama_index', 'llamaindex', 'langgraph', 'llm', 'gpt-4', 'gpt', 'claude', 'prompt engineering', 'rag', 'vector databases', 'pinecone', 'chroma', 'chromadb', 'milvus', 'weaviate', 'openai', 'fine-tuning', 'rlhf', 'generative ai', 'genai', 'agentic workflows', 'mlops', 'mlflow', 'dvc', 'model deployment', 'semantic search',
    # Databases
    'postgresql', 'postgres', 'mysql', 'mongodb', 'mongo', 'redis', 'cassandra', 'elasticsearch', 'sqlite', 'oracle', 'mariadb', 'dynamodb', 'firebase',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'jenkins', 'git', 'github actions', 'gitlab ci', 'ci/cd', 'cicd', 'prometheus', 'grafana', 'elk stack', 'elk', 'cloudformation',
    # Core Concepts & Architecture
    'rest api', 'restful api', 'rest', 'graphql', 'microservices', 'system design', 'agile', 'scrum', 'oop', 'data structures', 'algorithms', 'unit testing', 'tdd', 'clean code'
}

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def preprocess_text(text):
    """Applies NLP preprocessing: lowercasing, tokenization, stop word removal, and lemmatization."""
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords and non-alphanumeric tokens
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    
    cleaned_tokens = []
    for token in tokens:
        # Keep alphanumeric, but filter out standard punctuation
        if token.isalnum() and token not in stop_words:
            # Lemmatize
            cleaned_tokens.append(lemmatizer.lemmatize(token))
            
    return " ".join(cleaned_tokens)

def segment_resume(text):
    """
    Segments the resume into standard sections: Skills, Education, Experience.
    Returns a dictionary of raw section texts.
    """
    sections = {
        'skills': '',
        'education': '',
        'experience': ''
    }
    
    # Normalize line breaks and spaces
    text_lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Define section headers regex patterns
    headers = {
        'skills': re.compile(r'^(skills|technical skills|key skills|technologies|competencies|skills & tools)', re.IGNORECASE),
        'education': re.compile(r'^(education|academic background|qualifications|academic credentials)', re.IGNORECASE),
        'experience': re.compile(r'^(experience|work experience|professional experience|employment history|work history|projects)', re.IGNORECASE)
    }
    
    current_section = None
    section_content = {k: [] for k in sections.keys()}
    
    for line in text_lines:
        matched = False
        for sec_name, pattern in headers.items():
            if pattern.match(line) and len(line) < 30: # Section headers are usually short
                current_section = sec_name
                matched = True
                break
        
        if matched:
            continue
            
        if current_section:
            section_content[current_section].append(line)
            
    for k in sections.keys():
        sections[k] = "\n".join(section_content[k])
        
    return sections

def extract_contact_info(text):
    """Extracts candidate name, email, and phone number from resume."""
    name = "Candidate"
    email = "N/A"
    phone = "N/A"
    
    # Simple email extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        email = email_match.group(0)
        
    # Simple phone number extraction (handles formats like +1-123-456-7890, 1234567890, etc.)
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        phone = phone_match.group(0)
        
    # Attempt to extract Name: Usually the first line of the resume, or near it.
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        for line in lines[:3]:
            # Filter out lines that look like emails, phone numbers, website links, or contain common labels
            if '@' not in line and not re.search(r'\d{4}', line) and 'resume' not in line.lower() and len(line.split()) <= 4:
                # Capitalization check (name is usually capitalized)
                words = line.split()
                if all(w[0].isupper() for w in words if w.isalpha()):
                    name = line
                    break
                    
    return {"name": name, "email": email, "phone": phone}

def extract_skills_from_text(text):
    """Extracts known skills from text using phrase matching."""
    extracted = set()
    text_lower = text.lower()
    
    for skill in SKILL_DICTIONARY:
        # Use word boundaries to avoid partial matches (e.g. "git" matching "digital")
        # Handle multi-word skills
        escaped_skill = re.escape(skill)
        pattern = rf'\b{escaped_skill}\b'
        if re.search(pattern, text_lower):
            extracted.add(skill)
            
    return list(extracted)

def parse_experience_years(text):
    """
    Parses resume text to estimate years of experience.
    Looks for phrases like 'X years of experience' or scans for year ranges.
    """
    years = 0
    # Pattern 1: X+ years of experience
    match = re.search(r'(\d+)\+?\s*(years?|yrs?)\s*(of\s*)?experience', text, re.IGNORECASE)
    if match:
        years = int(match.group(1))
        return years
        
    # Pattern 2: Scan for year ranges (e.g., 2018 - 2022, 2020 to Present)
    # Filter valid years between 1990 and 2030
    year_ranges = re.findall(r'\b(199\d|200\d|201\d|202\d)\b\s*[-–to]+\s*\b(199\d|200\d|201\d|202\d|present|current)\b', text, re.IGNORECASE)
    total_years = 0
    for start, end in year_ranges:
        start_yr = int(start)
        if end.lower() in ['present', 'current']:
            end_yr = 2026 # Let's assume current year is 2026 based on local time
        else:
            end_yr = int(end)
            
        diff = end_yr - start_yr
        if 0 < diff < 20: # Valid range
            total_years += diff
            
    if total_years > 0:
        years = total_years
        
    return years

def analyze_resume(resume_text, job_desc_text):
    """
    Analyzes a single resume against a job description.
    Returns scores, extracted details, and a candidate summary.
    """
    # 1. Contact info & basic metadata
    contact = extract_contact_info(resume_text)
    
    # 2. Section segmentation
    sections = segment_resume(resume_text)
    
    # 3. Skills Extraction
    job_skills = extract_skills_from_text(job_desc_text)
    resume_skills = extract_skills_from_text(resume_text)
    
    # Matches and missing skills
    matched_skills = [s for s in job_skills if s in resume_skills]
    missing_skills = [s for s in job_skills if s not in resume_skills]
    
    # 4. Years of experience
    resume_exp_years = parse_experience_years(resume_text)
    
    # Job description experience requirement
    job_exp_match = re.search(r'(\d+)\+?\s*(years?|yrs?)\s*(of\s*)?experience', job_desc_text, re.IGNORECASE)
    req_years = int(job_exp_match.group(1)) if job_exp_match else 0
    
    # 5. NLP similarity (TF-IDF + Cosine)
    preprocessed_job = preprocess_text(job_desc_text)
    preprocessed_resume = preprocess_text(resume_text)
    
    cosine_sim = 0.0
    if preprocessed_job and preprocessed_resume:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([preprocessed_job, preprocessed_resume])
        cosine_sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        
    # 6. Scoring Calculations
    # Skills score: ratio of matched skills to total skills required by job description
    skills_score = len(matched_skills) / len(job_skills) if job_skills else 1.0
    
    # Experience score: 1.0 if candidate has >= req_years, otherwise ratio
    if req_years == 0:
        exp_score = 1.0
    else:
        exp_score = min(1.0, resume_exp_years / req_years)
        
    # Scale cosine similarity (which rarely exceeds 0.35 in practice) to a 0-100 scale
    tfidf_contrib = min(100.0, (cosine_sim / 0.35) * 100)
    skills_contrib = skills_score * 100
    exp_contrib = exp_score * 100
    
    final_score = round((tfidf_contrib * 0.5) + (skills_contrib * 0.4) + (exp_contrib * 0.1), 1)
    
    # 7. Summary Report Generation
    summary = generate_summary_report(contact['name'], matched_skills, missing_skills, resume_exp_years, req_years, final_score)
    
    return {
        'name': contact['name'],
        'email': contact['email'],
        'phone': contact['phone'],
        'experience_years': resume_exp_years,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'resume_skills': resume_skills,
        'cosine_similarity': round(tfidf_contrib, 1),
        'skills_score': round(skills_contrib, 1),
        'experience_score': round(exp_contrib, 1),
        'final_score': final_score,
        'summary': summary
    }

def generate_summary_report(name, matched, missing, candidate_exp, required_exp, score):
    """Generates a text summary report for the candidate."""
    skills_summary = f"Matches {len(matched)} key skills requested (including {', '.join(matched[:4])})." if matched else "No direct matching skills found."
    missing_summary = f"Missing critical skills: {', '.join(missing[:4])}." if missing else "Possesses all identified skills from the job description!"
    
    exp_status = ""
    if required_exp > 0:
        if candidate_exp >= required_exp:
            exp_status = f"Meets experience requirement (has {candidate_exp} years, requires {required_exp}+)."
        else:
            exp_status = f"Under-experienced (has {candidate_exp} years, requires {required_exp}+)."
    else:
        exp_status = f"Has {candidate_exp} years of relevant professional experience."
        
    evaluation = ""
    if score >= 80:
        evaluation = "Highly recommended candidate. Excellent alignment of skills, experience, and terminology."
    elif score >= 60:
        evaluation = "Strong candidate. Good skill fit, though minor skill gaps or experience differences exist."
    elif score >= 40:
        evaluation = "Potential candidate. Requires upskilling or closer review of transferrable experience."
    else:
        evaluation = "Low alignment. Key skills or qualifications are missing."

    report = (
        f"Candidate {name} has a match rating of {score}%. "
        f"{skills_summary} {missing_summary} "
        f"{exp_status} Overall Assessment: {evaluation}"
    )
    return report
