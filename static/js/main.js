document.addEventListener('DOMContentLoaded', function() {
    // Initialize tab click listeners
    const analyzeTab = document.getElementById('analyze-tab');
    const batchTab = document.getElementById('batch-tab');
    
    // Add tab switching functionality
    if (analyzeTab && batchTab) {
        analyzeTab.addEventListener('click', function() {
            document.getElementById('analyzeTab').classList.add('show', 'active');
            document.getElementById('batchTab').classList.remove('show', 'active');
            analyzeTab.classList.add('active');
            batchTab.classList.remove('active');
        });
        
        batchTab.addEventListener('click', function() {
            document.getElementById('batchTab').classList.add('show', 'active');
            document.getElementById('analyzeTab').classList.remove('show', 'active');
            batchTab.classList.add('active');
            analyzeTab.classList.remove('active');
        });
    }
    
    // Set up form submission for analyzing a single comment
    document.getElementById('analyzeForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const comment = document.getElementById('commentInput').value.trim();
        const model = document.querySelector('input[name="modelType"]:checked').value;
        
        // Validate form data
        if (comment === '') {
            showAlert('Please enter a comment to analyze', 'danger', 'resultContainer');
            return;
        }
        
        // Show loading spinner
        const resultContainer = document.getElementById('resultContainer');
        resultContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Analyzing your content...</p>
            </div>
        `;
        
        // Make API call
        fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                comment: comment,
                model_type: model
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Store the comment in the data object for display
            data.comment = comment;
            // Display results
            displayResults(data);
        })
        .catch(error => {
            // Display error
            showAlert('An error occurred: ' + error.message, 'danger', 'resultContainer');
        });
    });
    
    // Set up form submission for batch file upload
    document.getElementById('batchForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const fileInput = document.getElementById('csvFileInput');
        const model = document.querySelector('input[name="batchModelType"]:checked').value;
        
        // Validate form data
        if (fileInput.files.length === 0) {
            showAlert('Please select a file to upload', 'danger', 'batchResultContainer');
            return;
        }
        
        // Check file type
        const file = fileInput.files[0];
        if (!file.name.endsWith('.csv')) {
            showAlert('Please select a CSV file', 'danger', 'batchResultContainer');
            return;
        }
        
        // Show loading spinner
        const batchResultContainer = document.getElementById('batchResultContainer');
        batchResultContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Processing your file. This may take a moment...</p>
            </div>
        `;
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('model_type', model);
        
        console.log('Submitting batch with model:', model); // Debug log
        
        // Make API call
        fetch('/api/batch', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || 'Network response was not ok');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Batch API response:', data); // Debug log
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            if (data.results && data.results.length === 0) {
                showAlert('No valid comments found in the CSV file.', 'warning', 'batchResultContainer');
                return;
            }
            
            // Display batch results
            displayBatchResults(data);
        })
        .catch(error => {
            console.error('Batch API error:', error); // Debug log
            // Display error
            showAlert('An error occurred: ' + error.message, 'danger', 'batchResultContainer');
        });
    });
    
    // Function to display alert
    function showAlert(message, type, containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
    
    // Function to display analysis results
    function displayResults(data) {
        const resultsElement = document.getElementById('resultContainer');
        
        // Clear previous results
        resultsElement.innerHTML = '';
        
        // Add comment information
        const commentInfo = document.createElement('div');
        commentInfo.className = 'mb-4';
        commentInfo.innerHTML = `
            <h5 class="mb-3">Analysis Results</h5>
            <p><strong>Comment:</strong> "${data.comment || 'No comment provided'}"</p>
            <p><strong>Model:</strong> <span class="badge bg-dark">${data.model}</span></p>
        `;
        resultsElement.appendChild(commentInfo);
        
        // Create primary emotion section
        const primaryEmotionSection = document.createElement('div');
        primaryEmotionSection.className = 'mb-4';
        primaryEmotionSection.innerHTML = `
            <h5 class="mb-3">Primary Emotion</h5>
            <div class="emotion-badge emotion-${data.primary_emotion.toLowerCase()}">
                <span>${capitalizeFirstLetter(data.primary_emotion)}</span>
                <span class="badge bg-dark">${(data.emotions[data.primary_emotion] * 100).toFixed(1)}%</span>
            </div>
        `;
        resultsElement.appendChild(primaryEmotionSection);
        
        // Create emotion breakdown section
        const emotionBreakdownSection = document.createElement('div');
        emotionBreakdownSection.className = 'mb-4';
        emotionBreakdownSection.innerHTML = '<h5 class="mb-3">Emotion Breakdown</h5>';
        
        // Create emotion bars
        const emotionBars = document.createElement('div');
        emotionBars.className = 'emotion-bars';
        
        // Sort emotions by score
        const sortedEmotions = Object.entries(data.emotions)
            .sort((a, b) => b[1] - a[1])
            .map(([emotion, score]) => ({
                emotion: emotion,
                score: score
            }));
        
        sortedEmotions.forEach(item => {
            const bar = document.createElement('div');
            bar.className = 'mb-3';
            const percentage = (item.score * 100).toFixed(1);
            bar.innerHTML = `
                <div class="d-flex justify-content-between mb-1">
                    <span>${capitalizeFirstLetter(item.emotion)}</span>
                    <span>${percentage}%</span>
                </div>
                <div class="progress" style="height: 15px;">
                    <div 
                        class="progress-bar emotion-${item.emotion.toLowerCase()}" 
                        role="progressbar" 
                        style="width: ${percentage}%" 
                        aria-valuenow="${percentage}" 
                        aria-valuemin="0" 
                        aria-valuemax="100">
                    </div>
                </div>
            `;
            emotionBars.appendChild(bar);
        });
        
        emotionBreakdownSection.appendChild(emotionBars);
        resultsElement.appendChild(emotionBreakdownSection);
    }
    
    // Function to display batch analysis results
    function displayBatchResults(data) {
        const resultsElement = document.getElementById('batchResultContainer');
        
        // Clear previous results
        resultsElement.innerHTML = '';
        
        // Add summary information
        const summaryInfo = document.createElement('div');
        summaryInfo.className = 'card border-0 shadow-sm mb-4';
        summaryInfo.innerHTML = `
            <div class="card-body">
                <h5 class="card-title mb-3">Batch Analysis Results</h5>
                <p><strong>Total Comments Processed:</strong> ${data.results.length}</p>
                <p><strong>Model:</strong> <span class="badge bg-dark">${data.results[0]?.analysis?.model || 'Unknown'}</span></p>
                ${data.warning ? `<div class="alert alert-warning">${data.warning}</div>` : ''}
            </div>
        `;
        resultsElement.appendChild(summaryInfo);
        
        // Create emotion distribution section
        const emotionDistribution = document.createElement('div');
        emotionDistribution.className = 'card border-0 shadow-sm mb-4';
        emotionDistribution.innerHTML = `
            <div class="card-body">
                <h5 class="card-title mb-3">Emotion Distribution</h5>
                <div class="row row-cols-1 row-cols-md-3 g-4" id="emotionStats"></div>
            </div>
        `;
        resultsElement.appendChild(emotionDistribution);
        
        const statsRow = emotionDistribution.querySelector('#emotionStats');
        
        // Sort emotions by count
        const sortedEmotions = Object.entries(data.emotion_counts)
            .sort((a, b) => b[1] - a[1])
            .map(([emotion, count]) => ({
                emotion: emotion,
                count: count,
                percentage: ((count / data.results.length) * 100).toFixed(1)
            }));
        
        // Display top emotions as stats cards
        sortedEmotions.forEach(item => {
            const statsCard = document.createElement('div');
            statsCard.className = 'col';
            statsCard.innerHTML = `
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${capitalizeFirstLetter(item.emotion)}</h5>
                        <p class="card-text fs-3 fw-bold">${item.count}</p>
                        <div class="progress mt-2" style="height: 10px;">
                            <div class="progress-bar emotion-${item.emotion.toLowerCase()}" style="width: ${item.percentage}%" 
                                aria-valuenow="${item.percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <p class="card-text mt-2">${item.percentage}% of comments</p>
                    </div>
                </div>
            `;
            statsRow.appendChild(statsCard);
        });
        
        // Create comments table section
        const commentsSection = document.createElement('div');
        commentsSection.className = 'card border-0 shadow-sm mb-4';
        commentsSection.innerHTML = `
            <div class="card-body">
                <h5 class="card-title mb-3">Comment Analysis</h5>
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th scope="col">#</th>
                                <th scope="col">Comment</th>
                                <th scope="col">Primary Emotion</th>
                            </tr>
                        </thead>
                        <tbody id="commentsTableBody"></tbody>
                    </table>
                </div>
            </div>
        `;
        
        resultsElement.appendChild(commentsSection);
        
        // Add table rows
        const tableBody = commentsSection.querySelector('#commentsTableBody');
        data.results.forEach((result, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${result.comment}</td>
                <td><span class="badge emotion-${result.analysis.primary_emotion.toLowerCase()}">${capitalizeFirstLetter(result.analysis.primary_emotion)}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }
    
    // Helper function to capitalize first letter
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
    }
}); 