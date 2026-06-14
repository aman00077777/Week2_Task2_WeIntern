document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const templateSelect = document.getElementById('template-select');
    const jobDescription = document.getElementById('job-description');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('resume-files');
    const selectedFilesContainer = document.getElementById('selected-files-container');
    const fileList = document.getElementById('file-list');
    const analyzeForm = document.getElementById('analyze-form');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    const resultsPanel = document.getElementById('results-panel');
    const candidatesList = document.getElementById('candidates-list');
    
    let selectedFiles = [];

    // 1. Job Description Template Autofill
    templateSelect.addEventListener('change', (e) => {
        const selectedVal = e.target.value;
        const divId = `template-${selectedVal.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '')}`;
        const templateDiv = document.getElementById(divId);
        if (templateDiv) {
            jobDescription.value = templateDiv.textContent.trim();
        }
    });

    // 2. Drag & Drop File Handling
    // Trigger file input click when browse button is clicked
    document.querySelector('.browse-btn').addEventListener('click', () => {
        fileInput.click();
    });

    // Handle file changes via browser dialog
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleFiles(files) {
        const allowedExtensions = ['pdf', 'txt'];
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const ext = file.name.split('.').pop().toLowerCase();
            
            if (allowedExtensions.includes(ext)) {
                // Avoid duplicates
                if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                    selectedFiles.push(file);
                }
            } else {
                alert(`File "${file.name}" is not supported. Please upload PDF or TXT files.`);
            }
        }
        updateFileList();
    }

    function updateFileList() {
        fileList.innerHTML = '';
        if (selectedFiles.length > 0) {
            selectedFilesContainer.style.display = 'block';
            selectedFiles.forEach((file, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span><i class="fa-regular fa-file-lines"></i> ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                    <span class="remove-file" data-index="${index}"><i class="fa-solid fa-xmark"></i></span>
                `;
                fileList.appendChild(li);
            });

            // Re-bind remove triggers
            document.querySelectorAll('.remove-file').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const index = parseInt(e.currentTarget.getAttribute('data-index'));
                    selectedFiles.splice(index, 1);
                    updateFileList();
                });
            });
        } else {
            selectedFilesContainer.style.display = 'none';
        }
    }

    // 3. Form Submit - AJAX Call to Backend
    analyzeForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const jobText = jobDescription.value.strip ? jobDescription.value.strip() : jobDescription.value.trim();
        if (!jobText) {
            alert('Please provide a job description first.');
            return;
        }

        // Check if quick load checkboxes are selected
        const selectedSamples = Array.from(document.querySelectorAll('input[name="selected_samples"]:checked'))
            .map(cb => cb.value);

        if (selectedFiles.length === 0 && selectedSamples.length === 0) {
            alert('Please select at least one quick load sample resume or upload your own resumes.');
            return;
        }

        // Build FormData
        const formData = new FormData();
        formData.append('job_description', jobText);
        
        // Append sample resumes selected
        selectedSamples.forEach(sample => {
            formData.append('selected_samples', sample);
        });

        // Append custom files
        selectedFiles.forEach(file => {
            formData.append('resumes', file);
        });

        // UI Loading State
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';

        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Server error occurred') });
            }
            return response.json();
        })
        .then(data => {
            renderResults(data.candidates);
        })
        .catch(error => {
            alert(`Error: ${error.message}`);
        })
        .finally(() => {
            // Restore UI State
            submitBtn.disabled = false;
            btnText.style.display = 'inline-block';
            btnLoader.style.display = 'none';
        });
    });

    // 4. Render Results Function
    function renderResults(candidates) {
        candidatesList.innerHTML = '';
        resultsPanel.style.display = 'block';

        candidates.forEach((candidate, idx) => {
            const rank = idx + 1;
            const score = candidate.final_score;
            
            // Score categories for color borders
            let matchClass = 'low-match';
            if (score >= 80) {
                matchClass = 'high-match';
            } else if (score >= 55) {
                matchClass = 'medium-match';
            }

            // Calculate progress ring dashoffset (dasharray = 176)
            const strokeDashoffset = Math.round(176 - (176 * score) / 100);

            // Generate Tags HTML
            let matchedTags = candidate.matched_skills.map(s => `<span class="tag tag-matched">${s}</span>`).join('');
            let missingTags = candidate.missing_skills.map(s => `<span class="tag tag-missing">${s}</span>`).join('');
            
            // Show all skills from resume that are not in job requirements
            const extraSkills = candidate.resume_skills.filter(s => !candidate.matched_skills.includes(s));
            let extraTags = extraSkills.map(s => `<span class="tag tag-neutral">${s}</span>`).join('');

            const card = document.createElement('div');
            card.className = `candidate-card ${matchClass}`;
            card.innerHTML = `
                <div class="candidate-card-summary" data-id="${idx}">
                    <div class="candidate-info">
                        <div class="candidate-rank">${rank}</div>
                        <div class="candidate-meta">
                            <h3>${candidate.name}</h3>
                            <div class="candidate-sub">
                                <span><i class="fa-solid fa-briefcase"></i> ${candidate.experience_years} years exp</span>
                                <span><i class="fa-regular fa-file"></i> ${candidate.filename}</span>
                                <span><i class="fa-solid fa-cloud-arrow-up"></i> ${candidate.source}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="candidate-score-block">
                        <div class="score-ring">
                            <svg>
                                <circle class="ring-bg" cx="30" cy="30" r="28"></circle>
                                <circle class="ring-progress" cx="30" cy="30" r="28" style="stroke-dashoffset: 176;"></circle>
                            </svg>
                            <span class="score-text">${Math.round(score)}%</span>
                        </div>
                        <i class="fa-solid fa-chevron-down toggle-icon" id="toggle-chevron-${idx}"></i>
                    </div>
                </div>

                <div class="candidate-card-details" id="details-panel-${idx}">
                    <div class="details-grid">
                        <div class="details-main">
                            <div class="report-section">
                                <h4><i class="fa-solid fa-file-contract"></i> Evaluation Report</h4>
                                <div class="report-summary-text">${candidate.summary}</div>
                            </div>
                            
                            <div class="report-section">
                                <h4><i class="fa-solid fa-cubes"></i> Skill Matching Analysis</h4>
                                <div class="skills-tags-container">
                                    ${matchedTags ? `
                                        <div class="skills-subgroup">
                                            <h5>Matched Skills</h5>
                                            <div class="tags-list">${matchedTags}</div>
                                        </div>
                                    ` : ''}
                                    ${missingTags ? `
                                        <div class="skills-subgroup">
                                            <h5>Missing Requirements</h5>
                                            <div class="tags-list">${missingTags}</div>
                                        </div>
                                    ` : ''}
                                    ${extraTags ? `
                                        <div class="skills-subgroup">
                                            <h5>Other Extracted Skills</h5>
                                            <div class="tags-list">${extraTags}</div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>

                        <div class="details-sidebar">
                            <div class="contact-card">
                                <div class="contact-item">
                                    <i class="fa-solid fa-envelope"></i>
                                    <span>${candidate.email}</span>
                                </div>
                                <div class="contact-item">
                                    <i class="fa-solid fa-phone"></i>
                                    <span>${candidate.phone}</span>
                                </div>
                            </div>

                            <div class="contact-card">
                                <h4>Metric Scores</h4>
                                <div class="metric-bars-container" style="margin-top: 8px;">
                                    <div class="metric-bar-item">
                                        <div class="metric-bar-label">
                                            <span>Semantic Match (50%)</span>
                                            <span>${candidate.cosine_similarity.toFixed(1)}%</span>
                                        </div>
                                        <div class="metric-bar-bg">
                                            <div class="metric-bar-fill bar-blue" id="metric-cosine-${idx}" style="width: 0;"></div>
                                        </div>
                                    </div>
                                    <div class="metric-bar-item">
                                        <div class="metric-bar-label">
                                            <span>Skills Match (40%)</span>
                                            <span>${candidate.skills_score.toFixed(1)}%</span>
                                        </div>
                                        <div class="metric-bar-bg">
                                            <div class="metric-bar-fill bar-purple" id="metric-skills-${idx}" style="width: 0;"></div>
                                        </div>
                                    </div>
                                    <div class="metric-bar-item">
                                        <div class="metric-bar-label">
                                            <span>Experience Fit (10%)</span>
                                            <span>${candidate.experience_score.toFixed(1)}%</span>
                                        </div>
                                        <div class="metric-bar-bg">
                                            <div class="metric-bar-fill bar-green" id="metric-experience-${idx}" style="width: 0;"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            candidatesList.appendChild(card);

            // Animate progress ring on card render
            setTimeout(() => {
                const progressRing = card.querySelector('.ring-progress');
                if (progressRing) {
                    progressRing.style.strokeDashoffset = strokeDashoffset;
                }
            }, 100);
        });

        // Bind Accordion Click Toggles
        document.querySelectorAll('.candidate-card-summary').forEach(summary => {
            summary.addEventListener('click', (e) => {
                const id = summary.getAttribute('data-id');
                const details = document.getElementById(`details-panel-${id}`);
                const chevron = document.getElementById(`toggle-chevron-${id}`);
                
                const isExpanded = details.style.display === 'block';

                if (isExpanded) {
                    details.style.display = 'none';
                    chevron.style.transform = 'rotate(0deg)';
                } else {
                    details.style.display = 'block';
                    chevron.style.transform = 'rotate(180deg)';
                    
                    // Animate Sub-Metric Bars once expanded
                    setTimeout(() => {
                        const candidate = candidates[id];
                        document.getElementById(`metric-cosine-${id}`).style.width = `${candidate.cosine_similarity}%`;
                        document.getElementById(`metric-skills-${id}`).style.width = `${candidate.skills_score}%`;
                        document.getElementById(`metric-experience-${id}`).style.width = `${candidate.experience_score}%`;
                    }, 50);
                }
            });
        });

        // Scroll smooth to results panel
        resultsPanel.scrollIntoView({ behavior: 'smooth' });
    }
});
