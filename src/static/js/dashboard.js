document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const analysisContainer = document.getElementById('analysis-container');
    const refreshBtn = document.getElementById('refresh-btn');
    const timeframeSelector = document.getElementById('timeframe-selector');
    
    // Store the template
    const cardTemplate = document.getElementById('analysis-card-template');
    
    // Top symbols to analyze (if not fetched dynamically)
    const defaultSymbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT'];
    
    // Initial load
    loadData();
    
    // Event listeners
    refreshBtn.addEventListener('click', loadData);
    timeframeSelector.addEventListener('change', loadData);
    
    // Main function to load analysis data
    async function loadData() {
        showLoader();
        
        try {
            // First fetch top symbols if available
            let symbols = await fetchTopSymbols() || defaultSymbols;
            
            // Fetch analysis for each symbol
            const analysisPromises = symbols.map(symbol => fetchAnalysis(symbol));
            const results = await Promise.allSettled(analysisPromises);
            
            // Process successful results
            const analysisData = results
                .filter(result => result.status === 'fulfilled' && result.value)
                .map(result => result.value);
            
            // Display the analysis cards
            displayAnalysisCards(analysisData);
        } catch (error) {
            console.error('Error loading data:', error);
            showError('Failed to load analysis data. Please try again.');
        }
    }
    
    // Fetch top symbols from the API
    async function fetchTopSymbols() {
        try {
            const response = await fetch('/api/top-symbols');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.symbols || null;
        } catch (error) {
            console.warn('Could not fetch top symbols:', error);
            return null; // Return null to use default symbols
        }
    }
    
    // Fetch analysis for a specific symbol
    async function fetchAnalysis(symbol) {
        try {
            const response = await fetch(`/analysis/${symbol}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return processAnalysisData(symbol, data);
        } catch (error) {
            console.error(`Error fetching analysis for ${symbol}:`, error);
            return null;
        }
    }
    
    // Process raw analysis data into display format
    function processAnalysisData(symbol, data) {
        // Default values in case properties are missing
        const components = data.components || {};
        
        // Placeholder - Replace with actual mapping based on your API response
        const result = {
            symbol: symbol,
            score: data.score || 0,
            technical: components.trend_score ? components.trend_score.toFixed(1) : 0,
            volume: components.volume_score ? components.volume_score.toFixed(1) : 0,
            orderflow: components.momentum_score ? components.momentum_score.toFixed(1) : 0,
            orderbook: components.support_resistance_score ? components.support_resistance_score.toFixed(1) : 0,
            sentiment: data.interpretation?.trend || 'Neutral',
            confidence: `${data.interpretation?.confidence || 0}%`,
            insights: [
                // Placeholder insights
                data.interpretation?.recommendation || 'No recommendation available',
                components.trend_score > 70 ? 'Strong trend detected in price action' : 'Analyzing price trends...',
                components.volume_score > 70 ? 'Volume profile indicates accumulation phase' : 'Volume analysis inconclusive',
                components.momentum_score > 70 ? 'Momentum indicators show positive divergence' : 'Monitoring momentum shifts'
            ],
            timestamp: data.timestamp,
            recommendation: getRecommendation(data.score || 0)
        };
        
        return result;
    }
    
    // Determine recommendation based on score
    function getRecommendation(score) {
        if (score >= 80) return { text: 'STRONG BUY', class: 'strong-buy' };
        if (score >= 60) return { text: 'BUY', class: 'buy' };
        if (score <= 30) return { text: 'SELL', class: 'sell' };
        return { text: 'HOLD', class: 'hold' };
    }
    
    // Display analysis cards
    function displayAnalysisCards(analysisData) {
        // Clear previous cards (except loader)
        const loader = analysisContainer.querySelector('.loader');
        analysisContainer.innerHTML = '';
        
        if (analysisData.length === 0) {
            showError('No analysis data available');
            return;
        }
        
        // Create a card for each analysis
        analysisData.forEach(analysis => {
            const card = createAnalysisCard(analysis);
            analysisContainer.appendChild(card);
        });
    }
    
    // Create a single analysis card
    function createAnalysisCard(analysis) {
        // Clone the template
        const cardFragment = document.importNode(cardTemplate.content, true);
        const card = cardFragment.querySelector('.analysis-card');
        
        // Set card header
        card.querySelector('.symbol').textContent = analysis.symbol;
        const badge = card.querySelector('.badge');
        badge.textContent = analysis.recommendation.text;
        badge.classList.add(analysis.recommendation.class);
        
        // Set score and metrics
        card.querySelector('.score').textContent = analysis.score.toFixed(2);
        card.querySelector('.technical').textContent = analysis.technical;
        card.querySelector('.volume').textContent = analysis.volume;
        card.querySelector('.orderflow').textContent = analysis.orderflow;
        card.querySelector('.orderbook').textContent = analysis.orderbook;
        
        // Set AI analysis
        const sentimentValue = card.querySelector('.sentiment-value');
        sentimentValue.textContent = analysis.sentiment;
        
        // Add sentiment class
        if (analysis.sentiment.toLowerCase() === 'bullish') {
            sentimentValue.classList.add('bullish');
        } else if (analysis.sentiment.toLowerCase() === 'bearish') {
            sentimentValue.classList.add('bearish');
        } else {
            sentimentValue.classList.add('neutral');
        }
        
        card.querySelector('.confidence-value').textContent = analysis.confidence;
        
        // Add insights
        const insightsList = card.querySelector('.insights-list');
        analysis.insights.forEach(insight => {
            if (insight) {
                const li = document.createElement('li');
                li.textContent = insight;
                insightsList.appendChild(li);
            }
        });
        
        // Set updated time
        const updatedTime = card.querySelector('.updated-time');
        updatedTime.textContent = analysis.timestamp 
            ? `Updated: ${formatTimestamp(analysis.timestamp)}` 
            : 'Recently updated';
        
        // Add detail button click event
        card.querySelector('.details-btn').addEventListener('click', () => {
            window.location.href = `/detail/${analysis.symbol}`;
        });
        
        return card;
    }
    
    // Format timestamp to human-readable time
    function formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        
        // Convert timestamp to Date object
        const date = new Date(timestamp);
        
        // Check if date is valid
        if (isNaN(date.getTime())) return 'N/A';
        
        // Format the date
        return date.toLocaleString();
    }
    
    // Show loader
    function showLoader() {
        if (analysisContainer.querySelector('.loader')) return;
        
        const loader = document.createElement('div');
        loader.className = 'loader';
        loader.textContent = 'Loading analysis data...';
        analysisContainer.appendChild(loader);
    }
    
    // Show error message
    function showError(message) {
        analysisContainer.innerHTML = '';
        const errorElement = document.createElement('div');
        errorElement.className = 'loader error';
        errorElement.textContent = message;
        analysisContainer.appendChild(errorElement);
    }
}); 