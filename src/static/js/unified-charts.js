/**
 * Virtuoso Unified Charts System
 * High-performance charting library for trading dashboards
 * Optimized for mobile and real-time data updates
 */

// Global charts registry
window.virtuosoCharts = {
    charts: new Map(),
    defaultColors: {
        primary: '#ffbf00',
        secondary: '#b8860b',
        accent: '#ff9900',
        positive: '#4caf50',
        negative: '#f44336',
        neutral: '#64b5f6',
        background: '#1a2332',
        grid: '#1a2a40'
    },
    
    // Create price chart
    createPriceChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: data.timestamps.map(ts => new Date(ts).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                })),
                datasets: [{
                    label: options.dataset?.label || data.symbol || 'Price',
                    data: data.prices || [],
                    borderColor: this.defaultColors.primary,
                    backgroundColor: this.defaultColors.primary + '20',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointBackgroundColor: this.defaultColors.primary,
                    pointBorderColor: this.defaultColors.background,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: this.defaultColors.grid,
                            borderColor: this.defaultColors.grid
                        },
                        ticks: {
                            color: this.defaultColors.secondary,
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        display: true,
                        position: 'right',
                        grid: {
                            color: this.defaultColors.grid,
                            borderColor: this.defaultColors.grid
                        },
                        ticks: {
                            color: this.defaultColors.secondary,
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: this.defaultColors.background,
                        titleColor: this.defaultColors.primary,
                        bodyColor: this.defaultColors.secondary,
                        borderColor: this.defaultColors.grid,
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `Price: $${context.parsed.y.toLocaleString()}`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeOutQuart'
                },
                ...options.chartOptions
            }
        };
        
        const chart = new Chart(ctx, chartConfig);
        this.charts.set(canvasId, chart);
        return chart;
    },
    
    // Create volume chart
    createVolumeChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: data.timestamps.map(ts => new Date(ts).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                })),
                datasets: [{
                    label: 'Volume',
                    data: data.volumes || [],
                    backgroundColor: data.volumes.map((vol, idx) => {
                        if (data.prices && data.prices[idx] && data.prices[idx - 1]) {
                            return data.prices[idx] >= data.prices[idx - 1] 
                                ? this.defaultColors.positive + '80'
                                : this.defaultColors.negative + '80';
                        }
                        return this.defaultColors.accent + '80';
                    }),
                    borderColor: this.defaultColors.accent,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: this.defaultColors.grid,
                            borderColor: this.defaultColors.grid
                        },
                        ticks: {
                            color: this.defaultColors.secondary,
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        display: true,
                        position: 'right',
                        grid: {
                            color: this.defaultColors.grid,
                            borderColor: this.defaultColors.grid
                        },
                        ticks: {
                            color: this.defaultColors.secondary,
                            callback: function(value) {
                                return value >= 1000000 
                                    ? (value / 1000000).toFixed(1) + 'M'
                                    : value >= 1000 
                                        ? (value / 1000).toFixed(1) + 'K'
                                        : value.toFixed(0);
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: this.defaultColors.background,
                        titleColor: this.defaultColors.primary,
                        bodyColor: this.defaultColors.secondary,
                        borderColor: this.defaultColors.grid,
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                return `Volume: ${value >= 1000000 
                                    ? (value / 1000000).toFixed(2) + 'M'
                                    : value >= 1000 
                                        ? (value / 1000).toFixed(2) + 'K'
                                        : value.toFixed(0)}`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeOutQuart'
                }
            }
        };
        
        const chart = new Chart(ctx, chartConfig);
        this.charts.set(canvasId, chart);
        return chart;
    },
    
    // Create confluence indicator (gauge chart)
    createConfluenceIndicator(canvasId, score, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chartConfig = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        score >= 70 ? this.defaultColors.positive :
                        score >= 50 ? this.defaultColors.accent :
                        this.defaultColors.negative,
                        this.defaultColors.grid + '40'
                    ],
                    borderWidth: 0,
                    cutout: '70%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                rotation: -90,
                circumference: 180,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            },
            plugins: [{
                id: 'centerText',
                beforeDraw: (chart) => {
                    const { ctx, chartArea } = chart;
                    const centerX = (chartArea.left + chartArea.right) / 2;
                    const centerY = (chartArea.top + chartArea.bottom) / 2 + 20;
                    
                    ctx.save();
                    ctx.font = 'bold 32px Inter, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = this.defaultColors.primary;
                    ctx.fillText(Math.round(score), centerX, centerY);
                    
                    ctx.font = '14px Inter, sans-serif';
                    ctx.fillStyle = this.defaultColors.secondary;
                    ctx.fillText('Confluence Score', centerX, centerY + 25);
                    ctx.restore();
                }
            }]
        };
        
        const chart = new Chart(ctx, chartConfig);
        this.charts.set(canvasId, chart);
        return chart;
    },
    
    // Create market breadth chart
    createMarketBreadthChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: ['Strong Sell', 'Sell', 'Neutral', 'Buy', 'Strong Buy'],
                datasets: [{
                    label: 'Market Sentiment',
                    data: [
                        data.strongSell || 0,
                        data.sell || 0,
                        data.neutral || 0,
                        data.buy || 0,
                        data.strongBuy || 0
                    ],
                    backgroundColor: [
                        this.defaultColors.negative,
                        this.defaultColors.negative + '80',
                        this.defaultColors.neutral,
                        this.defaultColors.positive + '80',
                        this.defaultColors.positive
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: this.defaultColors.grid,
                            borderColor: this.defaultColors.grid
                        },
                        ticks: {
                            color: this.defaultColors.secondary
                        }
                    },
                    y: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: this.defaultColors.secondary
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: this.defaultColors.background,
                        titleColor: this.defaultColors.primary,
                        bodyColor: this.defaultColors.secondary,
                        borderColor: this.defaultColors.grid,
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.parsed.x} symbols`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeOutQuart'
                }
            }
        };
        
        const chart = new Chart(ctx, chartConfig);
        this.charts.set(canvasId, chart);
        return chart;
    },
    
    // Update existing chart data
    updateChart(canvasId, newData, options = {}) {
        const chart = this.charts.get(canvasId);
        if (!chart) return false;
        
        if (newData.labels) {
            chart.data.labels = newData.labels;
        }
        
        if (newData.datasets) {
            newData.datasets.forEach((dataset, index) => {
                if (chart.data.datasets[index]) {
                    Object.assign(chart.data.datasets[index], dataset);
                }
            });
        }
        
        chart.update(options.animation === false ? 'none' : undefined);
        return true;
    },
    
    // Destroy specific chart
    destroyChart(canvasId) {
        const chart = this.charts.get(canvasId);
        if (chart) {
            chart.destroy();
            this.charts.delete(canvasId);
            return true;
        }
        return false;
    },
    
    // Destroy all charts
    destroyAllCharts() {
        this.charts.forEach((chart, canvasId) => {
            chart.destroy();
        });
        this.charts.clear();
    },
    
    // Utility: Format number for display
    formatNumber(value, decimals = 2) {
        if (value >= 1000000000) {
            return (value / 1000000000).toFixed(decimals) + 'B';
        } else if (value >= 1000000) {
            return (value / 1000000).toFixed(decimals) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(decimals) + 'K';
        }
        return value.toFixed(decimals);
    },
    
    // Utility: Get color by value change
    getColorByChange(current, previous) {
        if (current > previous) return this.defaultColors.positive;
        if (current < previous) return this.defaultColors.negative;
        return this.defaultColors.neutral;
    }
};

// Auto-initialization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Virtuoso Unified Charts System loaded successfully');
    
    // Add Chart.js default configuration
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = window.virtuosoCharts.defaultColors.secondary;
        Chart.defaults.backgroundColor = window.virtuosoCharts.defaultColors.background;
        
        console.log('📊 Chart.js configuration applied');
    } else {
        console.warn('⚠️ Chart.js not found. Please include Chart.js before unified-charts.js');
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.virtuosoCharts;
}