document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');
    const fileInput = document.getElementById('csvFile');
    const fileName = document.getElementById('fileName');
    const resultCard = document.getElementById('resultCard');
    const errorCard = document.getElementById('errorCard');
    const predictionValue = document.getElementById('predictionValue');
    const errorMessage = document.getElementById('errorMessage');
    const downloadSample = document.getElementById('downloadSample');

    let predictionChart = null; // Store chart instance

    // File input change handler
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileName.textContent = this.files[0].name;
        } else {
            fileName.textContent = 'Choose CSV File (24 rows required)';
        }
    });

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
        form.classList.add('loading');
        
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
                
                // Phase 2: Show history save notification
                if (data.saved_to_history) {
                    const historyMsg = document.createElement('div');
                    historyMsg.style.cssText = 'background:#d4edda;color:#155724;padding:10px;border-radius:4px;margin-bottom:15px;border:1px solid #c3e6cb;';
                    historyMsg.innerHTML = '✓ Prediction saved to <a href="/history" style="color:#155724;font-weight:600;">your history</a>';
                    resultCard.insertBefore(historyMsg, resultCard.firstChild);
                }
                
                // Display historical data with Chart.js
                if (data.actual_last_24h_kw && data.actual_last_24h_kw.length === 24) {
                    displayHistoricalDataChart(data.actual_last_24h_kw, data.predicted_next_hour_kw);
                }
                
                resultCard.style.display = 'block';
                
                // Smooth scroll to result
                resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                // Show error
                errorMessage.textContent = data.error || 'An error occurred during prediction';
                errorCard.style.display = 'block';
            }
        } catch (error) {
            // Show error
            errorMessage.textContent = 'Failed to connect to the prediction service: ' + error.message;
            errorCard.style.display = 'block';
        } finally {
            // Remove loading state
            form.classList.remove('loading');
        }
    });

    // Download sample CSV template (JavaScript-based)
    downloadSample.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Create sample CSV with 24 rows
        const csvContent = `Global_intensity,Sub_metering_3,Voltage,Global_reactive_power,Sub_metering_2,Global_active_power
4.628,17.0,234.84,0.226,1.0,1.088
4.588,17.0,234.35,0.224,1.0,1.080
4.548,17.0,233.86,0.222,1.0,1.072
4.510,16.0,233.29,0.220,1.0,1.064
4.470,16.0,233.74,0.218,1.0,1.056
4.432,17.0,234.22,0.216,1.0,1.048
4.392,17.0,233.95,0.214,1.0,1.040
4.354,17.0,234.45,0.212,1.0,1.032
4.314,17.0,234.99,0.210,1.0,1.024
4.276,17.0,234.53,0.208,1.0,1.016
4.236,16.0,234.06,0.206,1.0,1.008
4.198,16.0,233.58,0.204,1.0,1.000
4.158,16.0,234.11,0.202,1.0,0.992
4.120,17.0,234.64,0.200,1.0,0.984
4.080,17.0,234.16,0.198,1.0,0.976
4.042,17.0,233.69,0.196,1.0,0.968
4.002,17.0,234.21,0.194,1.0,0.960
3.964,17.0,234.74,0.192,1.0,0.952
3.924,16.0,234.27,0.190,1.0,0.944
3.886,16.0,233.79,0.188,1.0,0.936
3.846,16.0,234.32,0.186,1.0,0.928
3.808,17.0,234.85,0.184,1.0,0.920
3.768,17.0,234.37,0.182,1.0,0.912
3.730,17.0,233.90,0.180,1.0,0.904`;
        
        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sample_24hour_data.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    });

    // Display historical data with Chart.js
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
        labels.push('Pred');
        
        const historicalData = [...history];
        const predictionData = new Array(24).fill(null);
        predictionData.push(prediction);
        
        // Create new chart
        predictionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Historical Data (24h)',
                        data: historicalData.concat([null]),
                        borderColor: 'rgb(102, 126, 234)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Prediction (Next Hour)',
                        data: predictionData,
                        borderColor: 'rgb(231, 76, 60)',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)',
                        borderWidth: 0,
                        pointRadius: 8,
                        pointHoverRadius: 10,
                        pointStyle: 'star'
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
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
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
                        title: {
                            display: true,
                            text: 'Power Consumption (kW)',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2) + ' kW';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time Series',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
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
    const modalCaption = document.getElementById('modalCaption');
    const closeBtn = document.querySelector('.modal-close');
    
    // Add click handlers to all gallery items
    document.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', function() {
            modal.style.display = 'flex';
            const img = this.querySelector('img');
            modalImg.src = img.src;
            modalCaption.textContent = this.querySelector('p').textContent;
        });
    });
    
    // Close modal
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
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
