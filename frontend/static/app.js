document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');
    const fileInput = document.getElementById('csvFile');
    const uploadArea = document.getElementById('uploadArea');
    const uploadLabel = document.getElementById('uploadLabel');
    const resultCard = document.getElementById('resultCard');
    const errorCard = document.getElementById('errorCard');
    const predictionValue = document.getElementById('predictionValue');
    const errorMessage = document.getElementById('errorMessage');
    const loadingOverlay = document.getElementById('loadingOverlay');

    let predictionChart = null; // Store chart instance

    // File input change handler
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            uploadLabel.innerHTML = `
                <div class="upload-icon"><i class="fas fa-file-csv"></i></div>
                <div class="upload-label" style="color: var(--color-success);">${this.files[0].name}</div>
                <div class="upload-hint">File selected - ready to predict</div>
            `;
        } else {
            uploadLabel.innerHTML = `
                <div class="upload-icon"><i class="fas fa-cloud-upload-alt"></i></div>
                <div class="upload-label">Drop CSV file here or click to browse</div>
                <div class="upload-hint">Must contain exactly 24 rows (hours) with 6 required columns</div>
            `;
        }
    });

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('drag-over');
        }, false);
    });

    uploadArea.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change'));
        }
    }, false);

    // Form submit handler
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Hide previous results
        resultCard.style.display = 'none';
        errorCard.style.display = 'none';
        
        // Check if file is selected
        if (!fileInput.files.length) {
            errorMessage.textContent = 'Please select a CSV file';
            errorCard.style.display = 'block';
            return;
        }
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        // Show loading state
        loadingOverlay.style.display = 'flex';
        
        try {
            // Make API request to PRD-compliant endpoint
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData  // No Content-Type header - browser sets it with boundary
            });
            
            const data = await response.json();
            
            if (response.ok && data.predicted_power_kw !== undefined) {
                // Display prediction
                predictionValue.textContent = data.predicted_power_kw.toFixed(3);
                
                // Display historical data with Chart.js
                if (data.actual_last_24h_kw && data.actual_last_24h_kw.length === 24) {
                    displayHistoricalDataChart(data.actual_last_24h_kw, data.predicted_next_hour_kw);
                }
                
                resultCard.style.display = 'block';
                
                // Smooth scroll to result
                setTimeout(() => {
                    resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            } else {
                // Show error
                errorMessage.textContent = data.error || 'An error occurred during prediction';
                errorCard.style.display = 'block';
                errorCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } catch (error) {
            // Show error
            errorMessage.textContent = 'Failed to connect to the prediction service: ' + error.message;
            errorCard.style.display = 'block';
            errorCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } finally {
            // Remove loading state
            loadingOverlay.style.display = 'none';
        }
    });

    // Display historical data with Chart.js (Dark Theme)
    function displayHistoricalDataChart(history, prediction) {
        const canvas = document.getElementById('historyChart');
        const ctx = canvas.getContext('2d');
        
        // Calculate statistics
        const avg = (history.reduce((a, b) => a + b, 0) / history.length).toFixed(3);
        const min = Math.min(...history).toFixed(3);
        const max = Math.max(...history).toFixed(3);
        
        document.getElementById('avgValue').textContent = avg;
        document.getElementById('minValue').textContent = min;
        document.getElementById('maxValue').textContent = max;
        
        // Destroy existing chart if it exists
        if (predictionChart) {
            predictionChart.destroy();
        }
        
        // Prepare data for Chart.js
        const labels = Array.from({length: 24}, (_, i) => `Hour ${i + 1}`);
        labels.push('Next');
        
        const historicalData = [...history];
        const predictionData = new Array(24).fill(null);
        predictionData.push(prediction);
        
        // Create new chart with dark theme
        predictionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Historical Data (24h)',
                        data: historicalData.concat([null]),
                        borderColor: 'rgb(99, 102, 241)',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        pointBackgroundColor: 'rgb(99, 102, 241)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    },
                    {
                        label: 'Prediction (Next Hour)',
                        data: predictionData,
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderWidth: 0,
                        pointRadius: 10,
                        pointHoverRadius: 12,
                        pointStyle: 'star',
                        pointBackgroundColor: 'rgb(16, 185, 129)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    title: {
                        display: true,
                        text: '24-Hour Historical Data with Next-Hour Prediction',
                        color: '#1a1f3a',
                        font: {
                            size: 14,
                            weight: '600'
                        },
                        padding: {
                            top: 10,
                            bottom: 20
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#1a1f3a',
                            font: {
                                size: 12,
                                weight: '500'
                            },
                            padding: 15,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(19, 24, 41, 0.95)',
                        titleColor: '#e4e7eb',
                        bodyColor: '#94a3b8',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(3) + ' kW';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: '#e5e7eb',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 11
                            },
                            callback: function(value) {
                                return value.toFixed(2) + ' kW';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Power Consumption (kW)',
                            color: '#1a1f3a',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: '#e5e7eb',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 10
                            },
                            maxRotation: 45,
                            minRotation: 45
                        },
                        title: {
                            display: true,
                            text: 'Time Series',
                            color: '#1a1f3a',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    }

    // Load model metrics on page load
    async function loadModelMetrics() {
        try {
            const response = await fetch('/api/model-metrics');
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('metricRMSE').textContent = data.rmse_kw;
                document.getElementById('metricMAE').textContent = data.mae_kw;
                document.getElementById('metricR2').textContent = data.r2;
                document.getElementById('metricLookback').textContent = data.lookback;
                document.getElementById('metricHorizon').textContent = data.horizon;
            }
        } catch (error) {
            console.error('Failed to load model metrics:', error);
        }
    }

    // Image gallery modal
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const closeBtn = document.getElementById('modalClose');
    
    // Add click handlers to all gallery items
    document.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', function() {
            modal.classList.add('active');
            const img = this.querySelector('img');
            modalImg.src = img.src;
            modalImg.alt = img.alt;
        });
    });
    
    // Close modal
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.remove('active');
        });
    }
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });

    // Initialize
    loadModelMetrics();
});

// Health check on page load
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('Service health:', data);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

checkHealth();
