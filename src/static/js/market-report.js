document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const refreshBtn = document.getElementById('refresh-btn');
    const reportTimestamp = document.getElementById('report-timestamp');
    const reportContent = document.getElementById('report-content');
    const loader = document.querySelector('.loader');
    
    // Initial load
    loadReport();
    
    // Event listeners
    refreshBtn.addEventListener('click', loadReport);
    
    // Main function to load market report data
    async function loadReport() {
        showLoader();
        
        try {
            const report = await fetchMarketReport();
            displayReport(report);
        } catch (error) {
            console.error('Error loading market report:', error);
            showError('Failed to load market report. Please try again.');
        }
    }
    
    // Fetch market report data
    async function fetchMarketReport() {
        const response = await fetch('/api/market-report');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    }
    
    // Display market report
    function displayReport(report) {
        hideLoader();
        
        // Update timestamp
        if (report.timestamp) {
            reportTimestamp.textContent = `Last updated: ${formatTimestamp(report.timestamp)}`;
        }
        
        // Update Market Overview section
        if (report.overview) {
            document.getElementById('total-volume').textContent = formatCurrency(report.overview.total_volume || 0);
            document.getElementById('market-sentiment').textContent = report.overview.sentiment || 'Neutral';
            document.getElementById('volatility-index').textContent = formatNumber(report.overview.volatility_index || 0);
            document.getElementById('smart-money-flow').textContent = formatNumber(report.overview.smart_money_flow || 0);
            
            // Add sentiment class
            const sentimentEl = document.getElementById('market-sentiment');
            sentimentEl.className = '';
            if (report.overview.sentiment) {
                const sentiment = report.overview.sentiment.toLowerCase();
                if (sentiment.includes('bull')) {
                    sentimentEl.classList.add('bullish');
                } else if (sentiment.includes('bear')) {
                    sentimentEl.classList.add('bearish');
                } else {
                    sentimentEl.classList.add('neutral');
                }
            }
        }
        
        // Update Market Regime section
        if (report.market_regime) {
            const regimeLabel = document.getElementById('regime-name');
            regimeLabel.textContent = report.market_regime.name || 'Unknown';
            
            // Add class based on regime
            regimeLabel.className = 'regime-label';
            const regime = (report.market_regime.name || '').toLowerCase();
            if (regime.includes('bull')) {
                regimeLabel.classList.add('bullish');
            } else if (regime.includes('bear')) {
                regimeLabel.classList.add('bearish');
            } else {
                regimeLabel.classList.add('neutral');
            }
            
            document.getElementById('regime-description').textContent = report.market_regime.description || '';
        }
        
        // Update Top Movers section
        if (report.top_movers) {
            const gainersListEl = document.getElementById('top-gainers-list');
            const losersListEl = document.getElementById('top-losers-list');
            
            // Clear previous data
            gainersListEl.innerHTML = '';
            losersListEl.innerHTML = '';
            
            // Add top gainers
            if (report.top_movers.gainers && report.top_movers.gainers.length > 0) {
                report.top_movers.gainers.forEach(gainer => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span class="symbol">${gainer.symbol}</span>
                        <span class="change positive">+${formatPercentage(gainer.change)}</span>
                    `;
                    gainersListEl.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.textContent = 'No data available';
                gainersListEl.appendChild(li);
            }
            
            // Add top losers
            if (report.top_movers.losers && report.top_movers.losers.length > 0) {
                report.top_movers.losers.forEach(loser => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span class="symbol">${loser.symbol}</span>
                        <span class="change negative">${formatPercentage(loser.change)}</span>
                    `;
                    losersListEl.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.textContent = 'No data available';
                losersListEl.appendChild(li);
            }
        }
        
        // Update Order Flow section
        if (report.order_flow) {
            document.getElementById('order-flow-content').innerHTML = formatTextContent(report.order_flow.analysis || 'No order flow analysis available');
        }
        
        // Update Whale Activity section
        if (report.whale_activity) {
            document.getElementById('whale-activity-content').innerHTML = formatTextContent(report.whale_activity.analysis || 'No whale activity data available');
        }
        
        // Update Market Outlook section
        if (report.market_outlook) {
            document.getElementById('market-outlook-content').innerHTML = formatTextContent(report.market_outlook || 'No market outlook available');
        }
        
        // Show the report content
        reportContent.style.display = 'block';
    }
    
    // Format text content with line breaks and highlighting
    function formatTextContent(text) {
        if (!text) return '';
        
        // Replace newlines with HTML breaks
        let formatted = text.replace(/\n/g, '<br>');
        
        // Highlight important parts
        formatted = formatted.replace(/BULLISH|BEARISH|NEUTRAL/gi, match => {
            const lowerMatch = match.toLowerCase();
            let className = 'neutral';
            
            if (lowerMatch.includes('bull')) {
                className = 'bullish';
            } else if (lowerMatch.includes('bear')) {
                className = 'bearish';
            }
            
            return `<span class="${className}">${match}</span>`;
        });
        
        return formatted;
    }
    
    // Format currency values
    function formatCurrency(value) {
        if (typeof value !== 'number') {
            value = parseFloat(value) || 0;
        }
        
        if (value >= 1e9) {
            return `$${(value / 1e9).toFixed(2)}B`;
        } else if (value >= 1e6) {
            return `$${(value / 1e6).toFixed(2)}M`;
        } else if (value >= 1e3) {
            return `$${(value / 1e3).toFixed(2)}K`;
        }
        
        return `$${value.toFixed(2)}`;
    }
    
    // Format number with commas
    function formatNumber(value) {
        if (typeof value !== 'number') {
            value = parseFloat(value) || 0;
        }
        
        if (value % 1 !== 0) {
            // Has decimal part
            return value.toFixed(2);
        }
        
        return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    
    // Format percentage values
    function formatPercentage(value) {
        if (typeof value !== 'number') {
            value = parseFloat(value) || 0;
        }
        
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }
    
    // Format timestamp to readable date
    function formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown';
        
        // Convert timestamp to Date object
        const date = new Date(timestamp);
        
        // Check if date is valid
        if (isNaN(date.getTime())) return 'Unknown';
        
        // Format the date
        return date.toLocaleString();
    }
    
    // Show loader
    function showLoader() {
        reportContent.style.display = 'none';
        loader.style.display = 'block';
    }
    
    // Hide loader
    function hideLoader() {
        loader.style.display = 'none';
    }
    
    // Show error message
    function showError(message) {
        hideLoader();
        reportContent.style.display = 'none';
        loader.textContent = message;
        loader.style.display = 'block';
        loader.classList.add('error');
    }
}); 