/**
 * Unified Chart System for Virtuoso Trading Dashboard
 * Standardizes all chart implementations with consistent styling and performance
 */

class VirtuosoCharts {
    constructor() {
        this.theme = this.getThemeConfig();
        this.defaultOptions = this.getDefaultOptions();
        this.charts = new Map(); // Track active charts
        
        // Performance optimizations
        Chart.defaults.font.family = 'Inter';
        Chart.defaults.animation.duration = 300; // Reduced animation time
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    }

    /**
     * Get consistent theme configuration matching dashboard
     */
    getThemeConfig() {
        return {
            colors: {
                primary: '#ffbf00',      // Amber
                secondary: '#b8860b',    // Dark amber
                positive: '#4caf50',     // Green
                negative: '#f44336',     // Red
                warning: '#ff9900',      // Orange
                background: '#0c1a2b',   // Navy
                panel: '#1a2332',        // Lighter navy
                border: '#1a2a40',       // Border color
                text: '#ffbf00',         // Text color
                textSecondary: '#b8860b' // Secondary text
            },
            gradients: {
                positive: ['rgba(76, 175, 80, 0.8)', 'rgba(76, 175, 80, 0.1)'],
                negative: ['rgba(244, 67, 54, 0.8)', 'rgba(244, 67, 54, 0.1)'],
                primary: ['rgba(255, 191, 0, 0.8)', 'rgba(255, 191, 0, 0.1)']
            }
        };
    }

    /**
     * Default chart options optimized for financial data
     */
    getDefaultOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: this.theme.colors.text,
                        font: { size: 12, weight: '500' },
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: this.theme.colors.panel,
                    titleColor: this.theme.colors.text,
                    bodyColor: this.theme.colors.textSecondary,
                    borderColor: this.theme.colors.border,
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        title: (context) => {
                            return this.formatTooltipTitle(context[0]);
                        },
                        label: (context) => {
                            return this.formatTooltipLabel(context);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 191, 0, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: this.theme.colors.textSecondary,
                        font: { size: 11 }
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 191, 0, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: this.theme.colors.textSecondary,
                        font: { size: 11 },
                        callback: (value) => this.formatYAxisLabel(value)
                    }
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 4
                },
                line: {
                    borderWidth: 2,
                    tension: 0.1
                }
            }
        };
    }

    /**
     * Create a price chart optimized for crypto trading
     */
    createPriceChart(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas with id ${canvasId} not found`);
            return null;
        }

        const ctx = canvas.getContext('2d');
        
        // Optimize canvas for performance
        this.optimizeCanvas(canvas);

        const config = {
            type: 'line',
            data: {
                labels: data.timestamps,
                datasets: [{
                    label: data.symbol || 'Price',
                    data: data.prices,
                    borderColor: this.theme.colors.primary,
                    backgroundColor: this.createGradient(ctx, this.theme.gradients.primary),
                    fill: true,
                    ...options.dataset
                }]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    ...this.defaultOptions.scales,
                    y: {
                        ...this.defaultOptions.scales.y,
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: (value) => this.formatPrice(value)
                        }
                    }
                },
                ...options.chartOptions
            }
        };

        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }

    /**
     * Create a volume chart
     */
    createVolumeChart(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        this.optimizeCanvas(canvas);

        const config = {
            type: 'bar',
            data: {
                labels: data.timestamps,
                datasets: [{
                    label: 'Volume',
                    data: data.volumes,
                    backgroundColor: data.volumes.map((_, i) => 
                        data.prices && data.prices[i] >= data.prices[i-1] 
                            ? this.theme.colors.positive + '80'
                            : this.theme.colors.negative + '80'
                    ),
                    borderColor: 'transparent',
                    ...options.dataset
                }]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    ...this.defaultOptions.scales,
                    y: {
                        ...this.defaultOptions.scales.y,
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: (value) => this.formatVolume(value)
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: { display: false }
                },
                ...options.chartOptions
            }
        };

        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }

    /**
     * Create confluence score indicator (circular progress)
     */
    createConfluenceIndicator(canvasId, score, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        this.optimizeCanvas(canvas);

        const config = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        this.getScoreColor(score),
                        'rgba(26, 35, 50, 0.3)'
                    ],
                    borderWidth: 0,
                    cutout: '80%',
                    ...options.dataset
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                animation: {
                    animateRotate: true,
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                ...options.chartOptions
            },
            plugins: [{
                id: 'centerText',
                beforeDraw: (chart) => {
                    this.drawCenterText(chart, score);
                }
            }]
        };

        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }

    /**
     * Create market breadth chart
     */
    createMarketBreadthChart(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        this.optimizeCanvas(canvas);

        const config = {
            type: 'bar',
            data: {
                labels: ['Strong Sell', 'Sell', 'Neutral', 'Buy', 'Strong Buy'],
                datasets: [{
                    data: [data.strongSell, data.sell, data.neutral, data.buy, data.strongBuy],
                    backgroundColor: [
                        '#f44336cc', '#ff9800cc', '#9e9e9ecc', '#4caf50cc', '#2e7d32cc'
                    ],
                    borderColor: [
                        '#f44336', '#ff9800', '#9e9e9e', '#4caf50', '#2e7d32'
                    ],
                    borderWidth: 1,
                    ...options.dataset
                }]
            },
            options: {
                ...this.defaultOptions,
                indexAxis: options.horizontal ? 'y' : 'x',
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: { display: false }
                },
                ...options.chartOptions
            }
        };

        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    }

    // Utility methods
    optimizeCanvas(canvas) {
        // Enable hardware acceleration
        canvas.style.willChange = 'transform';
        canvas.style.transform = 'translateZ(0)';
        
        // Optimize for crisp rendering
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
    }

    createGradient(ctx, colors) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1]);
        return gradient;
    }

    getScoreColor(score) {
        if (score >= 80) return '#4caf50';
        if (score >= 60) return '#8bc34a';
        if (score >= 40) return '#ffbf00';
        if (score >= 20) return '#ff9800';
        return '#f44336';
    }

    drawCenterText(chart, score) {
        const { width, height, ctx } = chart;
        ctx.restore();
        
        const fontSize = Math.min(width, height) * 0.15;
        ctx.font = `bold ${fontSize}px Inter`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = this.theme.colors.text;
        
        const text = `${score}%`;
        const textX = width / 2;
        const textY = height / 2;
        
        ctx.fillText(text, textX, textY);
        ctx.save();
    }

    formatPrice(value) {
        if (value >= 1) return `$${value.toFixed(2)}`;
        if (value >= 0.01) return `$${value.toFixed(4)}`;
        return `$${value.toFixed(8)}`;
    }

    formatVolume(value) {
        if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
        if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
        if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
        return value.toFixed(0);
    }

    formatYAxisLabel(value) {
        if (typeof value === 'number') {
            if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
            if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
            if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
            return value.toFixed(2);
        }
        return value;
    }

    formatTooltipTitle(context) {
        if (context.parsed && context.parsed.x) {
            return new Date(context.parsed.x).toLocaleDateString();
        }
        return context.label;
    }

    formatTooltipLabel(context) {
        const value = context.parsed.y;
        const label = context.dataset.label || '';
        
        if (label.toLowerCase().includes('price')) {
            return `${label}: ${this.formatPrice(value)}`;
        }
        if (label.toLowerCase().includes('volume')) {
            return `${label}: ${this.formatVolume(value)}`;
        }
        
        return `${label}: ${value.toFixed(2)}`;
    }

    /**
     * Update chart data efficiently
     */
    updateChart(chartId, newData, options = {}) {
        const chart = this.charts.get(chartId);
        if (!chart) {
            console.warn(`Chart ${chartId} not found`);
            return;
        }

        // Batch updates for performance
        chart.data.labels = newData.labels || chart.data.labels;
        
        newData.datasets?.forEach((dataset, index) => {
            if (chart.data.datasets[index]) {
                Object.assign(chart.data.datasets[index], dataset);
            }
        });

        // Use efficient update mode
        chart.update(options.animation === false ? 'none' : 'active');
    }

    /**
     * Destroy chart and cleanup
     */
    destroyChart(chartId) {
        const chart = this.charts.get(chartId);
        if (chart) {
            chart.destroy();
            this.charts.delete(chartId);
        }
    }

    /**
     * Destroy all charts (useful for page cleanup)
     */
    destroyAllCharts() {
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
    }

    /**
     * Resize all charts (useful for responsive design)
     */
    resizeAllCharts() {
        this.charts.forEach(chart => chart.resize());
    }
}

// Create global instance
window.VirtuosoCharts = VirtuosoCharts;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.virtuosoCharts = new VirtuosoCharts();
});

// Handle window resize
window.addEventListener('resize', () => {
    if (window.virtuosoCharts) {
        window.virtuosoCharts.resizeAllCharts();
    }
});