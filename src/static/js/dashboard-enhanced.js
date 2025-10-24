/**
 * Virtuoso Trading Dashboard - Enhanced JavaScript
 * Real-time trading intelligence with WebSocket updates
 */

class VirtuosoDashboard {
    constructor() {
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.lastUpdate = null;
        this.updateInterval = null;
        this.isReconnecting = false;
        
        // Configuration
        this.config = {
            monitoring: {
                scan_interval: 5,
                max_alerts: 3,
                alert_cooldown: 60
            },
            signals: {
                min_score: 65,
                min_reliability: 75
            },
            alpha: {
                confidence_threshold: 75,
                risk_level: "Medium"
            }
        };
        
        this.init();
    }
    
    async init() {
        console.log('Initializing Virtuoso Dashboard...');
        this.setupEventListeners();
        await this.loadInitialData();
        this.connectWebSocket();
        this.startHeartbeat();
        
        // Initialize signal matrix
        this.initializeSignalMatrix();
    }
    
    setupEventListeners() {
        // Config panel toggles
        const configBtn = document.getElementById('config-btn');
        const configClose = document.getElementById('config-close');
        const configPanel = document.getElementById('config-panel');
        
        if (configBtn) {
            configBtn.addEventListener('click', () => {
                configPanel.classList.add('open');
            });
        }
        
        if (configClose) {
            configClose.addEventListener('click', () => {
                configPanel.classList.remove('open');
            });
        }
        
        // Config save/reset
        const saveBtn = document.getElementById('save-config');
        const resetBtn = document.getElementById('reset-config');
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConfiguration();
            });
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetConfiguration();
            });
        }
        
        // Close config panel when clicking outside
        document.addEventListener('click', (event) => {
            if (configPanel && !configPanel.contains(event.target) && !configBtn.contains(event.target)) {
                configPanel.classList.remove('open');
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                configPanel.classList.remove('open');
            }
            if (event.ctrlKey && event.key === 'r') {
                event.preventDefault();
                this.refreshData();
            }
        });
    }
    
    connectWebSocket() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/dashboard/ws`;
        
        console.log(`Connecting to WebSocket: ${wsUrl}`);
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('Dashboard WebSocket connected');
            this.reconnectAttempts = 0;
            this.isReconnecting = false;
            this.updateConnectionStatus('online');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = (event) => {
            console.log('Dashboard WebSocket disconnected:', event.code, event.reason);
            this.updateConnectionStatus('error');
            this.attemptReconnect();
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }
    
    attemptReconnect() {
        if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached or already reconnecting');
            return;
        }
        
        this.isReconnecting = true;
        this.reconnectAttempts++;
        
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }
    
    updateConnectionStatus(status) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.className = `status-indicator status-${status} pulse`;
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('WebSocket message received:', data.type);
        
        switch (data.type) {
            case 'dashboard_update':
                this.updateDashboard(data.data);
                break;
            case 'new_signal':
                this.addNewSignal(data.signal);
                break;
            case 'new_alert':
                this.addNewAlert(data.alert);
                break;
            case 'alpha_opportunity':
                this.addAlphaOpportunity(data.opportunity);
                break;
            case 'config_update':
                this.updateConfig(data.config);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }
    
    async loadInitialData() {
        try {
            this.showLoadingState();
            
            const response = await fetch('/api/dashboard/overview');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.updateDashboard(data);
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showErrorState('Failed to load dashboard data');
        }
    }
    
    showLoadingState() {
        const elements = ['signals-list', 'market-metrics', 'alpha-list', 'alerts-list'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = '<div class="loading">Loading...</div>';
            }
        });
    }
    
    showErrorState(message) {
        const elements = ['signals-list', 'market-metrics', 'alpha-list', 'alerts-list'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = `<div class="error">${message}</div>`;
            }
        });
    }
    
    updateDashboard(data) {
        this.lastUpdate = new Date();
        
        try {
            // Update signals
            if (data.signals) {
                this.updateSignalsPanel(data.signals);
            }
            
            // Update market overview
            if (data.market) {
                this.updateMarketPanel(data.market);
            }
            
            // Update alpha opportunities
            if (data.alpha_opportunities) {
                this.updateAlphaPanel(data.alpha_opportunities);
            }
            
            // Update alerts
            if (data.alerts) {
                this.updateAlertsPanel(data.alerts);
            }
            
            // Update system status
            if (data.system_status) {
                this.updateSystemStatus(data.system_status);
            }
            
            console.log('Dashboard updated successfully');
            
        } catch (error) {
            console.error('Error updating dashboard:', error);
        }
    }
    
    updateSignalsPanel(signals) {
        const container = document.getElementById('signals-list');
        const countElement = document.getElementById('signals-count');
        
        if (!container) return;
        
        if (countElement) {
            countElement.textContent = signals.length;
        }
        
        if (signals.length === 0) {
            container.innerHTML = '<div class="no-data">No signals available</div>';
            return;
        }
        
        container.innerHTML = signals.slice(0, 8).map(signal => {
            const score = signal.score || 0;
            const scoreClass = score >= 70 ? 'score-bullish' : 
                             score <= 40 ? 'score-bearish' : 'score-neutral';
            
            const signalType = signal.signal || 'HOLD';
            const typeClass = signalType.toUpperCase() === 'LONG' ? 'signal-buy' :
                             signalType.toUpperCase() === 'SHORT' ? 'signal-sell' : 'signal-hold';
            
            return `
                <div class="signal-item" data-symbol="${signal.symbol}">
                    <div class="signal-left">
                        <span class="signal-symbol">${signal.symbol || 'N/A'}</span>
                        <span class="signal-type ${typeClass}">${signalType}</span>
                    </div>
                    <div class="signal-right">
                        <span class="signal-score ${scoreClass}">${score.toFixed(1)}</span>
                        <span class="signal-time">${this.formatTime(signal.timestamp)}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers for signals
        container.querySelectorAll('.signal-item').forEach(item => {
            item.addEventListener('click', () => {
                const symbol = item.dataset.symbol;
                this.showSignalDetails(symbol);
            });
        });
    }
    
    updateAlphaPanel(opportunities) {
        const container = document.getElementById('alpha-list');
        const countElement = document.getElementById('alpha-count');
        
        if (!container) return;
        
        if (countElement) {
            countElement.textContent = opportunities.length;
        }
        
        if (opportunities.length === 0) {
            container.innerHTML = '<div class="no-data">No alpha opportunities detected</div>';
            return;
        }
        
        container.innerHTML = opportunities.slice(0, 5).map(opp => `
            <div class="alpha-item" data-symbol="${opp.symbol}">
                <div class="alpha-symbol">${opp.symbol}</div>
                <div class="alpha-pattern">${opp.pattern}</div>
                <div class="alpha-metrics">
                    <span class="alpha-confidence">Confidence: ${(opp.confidence * 100).toFixed(1)}%</span>
                    <span class="alpha-potential">Alpha: ${(opp.alpha_potential * 100).toFixed(1)}%</span>
                </div>
            </div>
        `).join('');
        
        // Add click handlers for alpha opportunities
        container.querySelectorAll('.alpha-item').forEach(item => {
            item.addEventListener('click', () => {
                const symbol = item.dataset.symbol;
                this.showAlphaDetails(symbol);
            });
        });
    }
    
    updateMarketPanel(market) {
        const container = document.getElementById('market-metrics');
        const regimeElement = document.getElementById('market-regime');
        
        if (!container) return;
        
        if (regimeElement && market.regime) {
            regimeElement.textContent = market.regime;
            regimeElement.className = `market-regime regime-${market.regime.toLowerCase()}`;
        }
        
        const metrics = [
            { label: 'Active Pairs', value: market.active_pairs || 0 },
            { label: 'Avg Volume', value: this.formatNumber(market.avg_volume || 0) },
            { label: 'Market Cap', value: this.formatNumber(market.market_cap || 0) },
            { label: 'Volatility', value: `${(market.volatility || 0).toFixed(1)}%` }
        ];
        
        container.innerHTML = metrics.map(metric => `
            <div class="metric-card">
                <div class="metric-value">${metric.value}</div>
                <div class="metric-label">${metric.label}</div>
            </div>
        `).join('');
    }
    
    updateAlertsPanel(alerts) {
        const container = document.getElementById('alerts-list');
        const countElement = document.getElementById('alerts-count');
        
        if (!container) return;
        
        if (countElement) {
            countElement.textContent = alerts.length;
        }
        
        if (alerts.length === 0) {
            container.innerHTML = '<div class="no-data">No alerts</div>';
            return;
        }
        
        container.innerHTML = alerts.slice(0, 15).map(alert => `
            <div class="alert-item alert-priority-${alert.priority}">
                <div class="alert-content">
                    <div class="alert-type">${alert.type}</div>
                    <div class="alert-message">${alert.message}</div>
                </div>
                <div class="alert-time">${this.formatTime(alert.timestamp)}</div>
            </div>
        `).join('');
    }
    
    updateSystemStatus(status) {
        // Update connection status if system is healthy
        if (status.status === 'online') {
            this.updateConnectionStatus('online');
        }
    }
    
    async saveConfiguration() {
        try {
            const config = this.getConfigurationFromUI();
            
            const response = await fetch('/api/dashboard/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                this.config = config;
                this.showNotification('Configuration saved successfully', 'success');
                document.getElementById('config-panel').classList.remove('open');
            } else {
                throw new Error('Failed to save configuration');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showNotification('Failed to save configuration', 'error');
        }
    }
    
    resetConfiguration() {
        // Reset to default values
        document.getElementById('scan-interval').value = 5;
        document.getElementById('max-alerts').value = 3;
        document.getElementById('alert-cooldown').value = 60;
        document.getElementById('min-score').value = 65;
        document.getElementById('min-reliability').value = 75;
        document.getElementById('alpha-confidence').value = 75;
        document.getElementById('risk-level').value = 'Medium';
        
        this.showNotification('Configuration reset to defaults', 'success');
    }
    
    getConfigurationFromUI() {
        return {
            monitoring: {
                scan_interval: parseInt(document.getElementById('scan-interval').value),
                max_alerts: parseInt(document.getElementById('max-alerts').value),
                alert_cooldown: parseInt(document.getElementById('alert-cooldown').value)
            },
            signals: {
                min_score: parseInt(document.getElementById('min-score').value),
                min_reliability: parseInt(document.getElementById('min-reliability').value)
            },
            alpha: {
                confidence_threshold: parseInt(document.getElementById('alpha-confidence').value),
                risk_level: document.getElementById('risk-level').value
            }
        };
    }
    
    async refreshData() {
        console.log('Refreshing dashboard data...');
        await this.loadInitialData();
        this.showNotification('Dashboard refreshed', 'success');
    }
    
    startHeartbeat() {
        // Send periodic ping to keep WebSocket alive
        setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Every 30 seconds
    }
    
    // Event handlers for detailed views
    showSignalDetails(symbol) {
        console.log(`Showing signal details for ${symbol}`);
        // In production, this would open a detailed signal analysis view
        this.showNotification(`Signal details for ${symbol}`, 'info');
    }
    
    showAlphaDetails(symbol) {
        console.log(`Showing alpha details for ${symbol}`);
        // In production, this would open a detailed alpha opportunity view
        this.showNotification(`Alpha opportunity for ${symbol}`, 'info');
    }
    
    // Utility methods
    formatTime(timestamp) {
        if (!timestamp) return 'N/A';
        
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            
            if (diffMins < 1) return 'just now';
            if (diffMins < 60) return `${diffMins} min ago`;
            
            const diffHours = Math.floor(diffMins / 60);
            if (diffHours < 24) return `${diffHours}h ago`;
            
            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays}d ago`;
        } catch (error) {
            console.error('Error formatting time:', error);
            return 'N/A';
        }
    }
    
    formatNumber(num) {
        if (typeof num !== 'number') return '0';
        
        if (num >= 1e12) return (num / 1e12).toFixed(1) + 'T';
        if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return num.toString();
    }
    
    showNotification(message, type = 'info') {
        // Remove existing notifications
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
    
    // Public methods for external access
    getConnectionStatus() {
        return this.websocket ? this.websocket.readyState : WebSocket.CLOSED;
    }
    
    getLastUpdate() {
        return this.lastUpdate;
    }
    
    getCurrentConfig() {
        return { ...this.config };
    }

    // Signal Matrix Functionality
    initializeSignalMatrix() {
        // Asset pairs for the matrix
        this.assets = [
            'BTCUSDT', 'ETHUSDT', 'AVAXUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
            'SOLUSDT', 'MATICUSDT', 'ATOMUSDT', 'NEARUSDT', 'FTMUSDT', 'ALGOUSDT'
        ];

        // Signal types
        this.signalTypes = [
            'momentum', 'technical', 'volume', 'orderflow', 
            'sentiment', 'whaleAct', 'betaExp', 'corrBreak', 'liquidation', 'largeOrd'
        ];

        // Signal weights for composite scoring
        this.signalWeights = {
            momentum: 0.20,
            technical: 0.15,
            volume: 0.12,
            orderflow: 0.10,
            sentiment: 0.06,
            whaleAct: 0.15,
            betaExp: 0.05,
            corrBreak: 0.04,
            liquidation: 0.08,
            largeOrd: 0.05
        };

        this.populateSignalMatrix();
        
        // Update matrix every 15 seconds
        setInterval(() => this.updateMatrix(), 15000);
    }

    generateSignalData() {
        const data = {};
        this.assets.forEach(asset => {
            data[asset] = {};
            let totalScore = 0;
            let totalWeight = 0;
            
            this.signalTypes.forEach(signal => {
                const confidence = Math.random() * 100;
                const direction = Math.random() < 0.55 ? 'bullish' : 'bearish';
                const strength = confidence > 75 ? 'strong' : confidence > 45 ? 'medium' : 'weak';
                
                data[asset][signal] = {
                    confidence: Math.max(30, confidence),
                    direction: direction,
                    strength: strength
                };
                
                const weight = this.signalWeights[signal] || 0.05;
                let scoreContribution = 0;
                
                if (direction === 'bullish') {
                    scoreContribution = confidence * weight;
                } else {
                    scoreContribution = (100 - confidence) * weight;
                }
                
                totalScore += scoreContribution;
                totalWeight += weight;
            });
            
            data[asset].compositeScore = Math.round(totalScore / totalWeight);
        });
        
        return data;
    }

    getSignalClass(signal) {
        return `signal-${signal.strength}-${signal.direction}`;
    }

    getSignalIcon(signal) {
        switch(signal.direction) {
            case 'bullish': return '↑';
            case 'bearish': return '↓';
            default: return '↑';
        }
    }

    getCompositeScoreClass(score) {
        if (score >= 85) return 'score-excellent';
        if (score >= 75) return 'score-good';
        if (score >= 60) return 'score-fair';
        if (score >= 45) return 'score-poor';
        return 'score-avoid';
    }

    createCompositeScoreCell(asset, compositeScore) {
        const cell = document.createElement('div');
        cell.className = `matrix-cell composite-score-cell ${this.getCompositeScoreClass(compositeScore)}`;
        
        const value = document.createElement('div');
        value.className = 'composite-score-value';
        value.textContent = compositeScore;
        
        const label = document.createElement('div');
        label.className = 'composite-score-label';
        if (compositeScore >= 85) label.textContent = 'EXCELLENT';
        else if (compositeScore >= 75) label.textContent = 'GOOD';
        else if (compositeScore >= 60) label.textContent = 'FAIR';
        else if (compositeScore >= 45) label.textContent = 'POOR';
        else label.textContent = 'AVOID';
        
        cell.appendChild(value);
        cell.appendChild(label);
        
        return cell;
    }

    createMatrixCell(asset, signalType, signalData) {
        const cell = document.createElement('div');
        cell.className = `matrix-cell ${this.getSignalClass(signalData)}`;
        
        const icon = document.createElement('div');
        icon.className = 'signal-icon';
        icon.textContent = this.getSignalIcon(signalData);
        
        const confidence = document.createElement('div');
        confidence.className = 'signal-confidence';
        confidence.textContent = `${signalData.confidence.toFixed(0)}%`;
        
        cell.appendChild(icon);
        cell.appendChild(confidence);
        
        // Add hover tooltip
        cell.addEventListener('mouseenter', (e) => this.showMatrixTooltip(e, asset, signalType, signalData));
        cell.addEventListener('mouseleave', () => this.hideMatrixTooltip());
        
        return cell;
    }

    showMatrixTooltip(event, asset, signalType, signalData) {
        const tooltip = document.getElementById('matrixTooltip');
        const title = document.getElementById('tooltipTitle');
        const details = document.getElementById('tooltipDetails');
        
        if (!tooltip || !title || !details) return;
        
        title.textContent = `${asset} - ${signalType.toUpperCase()}`;
        
        details.innerHTML = `
            <span>Direction:</span><span>${signalData.direction.toUpperCase()}</span>
            <span>Confidence:</span><span>${signalData.confidence.toFixed(1)}%</span>
            <span>Strength:</span><span>${signalData.strength.toUpperCase()}</span>
            <span>Signal Type:</span><span>${signalType.replace(/([A-Z])/g, ' $1').toUpperCase()}</span>
        `;
        
        tooltip.style.display = 'block';
        tooltip.style.left = event.pageX + 10 + 'px';
        tooltip.style.top = event.pageY - 50 + 'px';
    }

    hideMatrixTooltip() {
        const tooltip = document.getElementById('matrixTooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    populateSignalMatrix() {
        const matrixGrid = document.getElementById('signalMatrix');
        if (!matrixGrid) return;

        const signalData = this.generateSignalData();
        
        // Clear existing content
        matrixGrid.innerHTML = '';
        
        // Sort assets by composite score for better visual hierarchy
        const sortedAssets = this.assets
            .map(asset => ({ asset, score: signalData[asset].compositeScore }))
            .sort((a, b) => b.score - a.score);
        
        sortedAssets.forEach(item => {
            const asset = item.asset;
            
            // Asset row header
            const rowHeader = document.createElement('div');
            rowHeader.className = 'matrix-row-header';
            rowHeader.textContent = asset;
            matrixGrid.appendChild(rowHeader);
            
            // Composite score cell
            const scoreCell = this.createCompositeScoreCell(asset, signalData[asset].compositeScore);
            matrixGrid.appendChild(scoreCell);
            
            // Signal cells for this asset
            this.signalTypes.forEach(signalType => {
                const cell = this.createMatrixCell(asset, signalType, signalData[asset][signalType]);
                matrixGrid.appendChild(cell);
            });
        });
        
        // Update signals panel with compact signals
        this.updateSignalsCompact(signalData, sortedAssets.slice(0, 6));
        
        // Update alpha opportunities
        this.updateAlphaOpportunities(signalData, sortedAssets);
    }

    updateSignalsCompact(signalData, topAssets) {
        const signalsList = document.getElementById('signals-list');
        if (!signalsList) return;

        signalsList.innerHTML = '';

        topAssets.forEach(item => {
            const asset = item.asset;
            const score = item.score;
            
            const signalItem = document.createElement('div');
            signalItem.className = 'signal-compact';
            signalItem.style.cssText = `
                background: linear-gradient(135deg, var(--bg-hero), var(--bg-satellite));
                border-left: 3px solid var(--accent-positive);
                padding: 8px 12px;
                margin: 8px 0;
                border-radius: 4px;
                border: 1px solid var(--border-light);
                transition: all 0.3s ease;
            `;
            
            const action = score > 70 ? 'LONG' : score < 40 ? 'SHORT' : 'WATCH';
            const actionClass = action === 'LONG' ? 'action-long' : action === 'SHORT' ? 'action-short' : 'action-watch';
            
            signalItem.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 600; color: var(--text-primary); font-size: 11px; font-family: 'JetBrains Mono', monospace;">${asset}</span>
                    <span style="font-size: 8px; padding: 2px 6px; border-radius: 2px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;" class="${actionClass}">${action}</span>
                </div>
                <div style="font-size: 9px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center;">
                    <span>Multi-factor confluence</span>
                    <span>${score.toFixed(1)}%</span>
                </div>
            `;
            
            signalItem.addEventListener('mouseenter', function() {
                this.style.transform = 'translateX(4px)';
                this.style.boxShadow = '0 4px 15px rgba(255, 153, 0, 0.3)';
            });
            
            signalItem.addEventListener('mouseleave', function() {
                this.style.transform = '';
                this.style.boxShadow = '';
            });
            
            signalsList.appendChild(signalItem);
        });
    }

    updateAlphaOpportunities(signalData, sortedAssets) {
        const alphaList = document.getElementById('alpha-list');
        if (!alphaList) return;

        alphaList.innerHTML = '';

        // Get high-scoring assets for alpha opportunities
        const highBetaAssets = sortedAssets.filter(item => item.score > 75).slice(0, 4);
        
        highBetaAssets.forEach((item, index) => {
            const asset = item.asset.split('/')[0];
            const score = item.score;
            
            const alphaItem = document.createElement('div');
            alphaItem.className = 'alpha-item';
            alphaItem.style.cssText = `
                background: linear-gradient(135deg, var(--bg-hero), var(--bg-satellite));
                border-left: 3px solid var(--accent-positive);
                padding: 12px;
                margin: 10px 0;
                border-radius: 4px;
                border: 1px solid var(--border-light);
                transition: all 0.3s ease;
            `;
            
            const patterns = ['MOMENTUM_BREAKOUT', 'BETA_DIVERGENCE', 'CORRELATION_ANOMALY', 'VOLATILITY_EXPANSION'];
            const pattern = patterns[index % patterns.length];
            
            alphaItem.innerHTML = `
                <div style="font-weight: 600; color: var(--accent-positive); font-size: 13px; font-family: 'JetBrains Mono', monospace; margin-bottom: 4px;">🎯 ${asset}/USDT</div>
                <div style="font-size: 9px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">${pattern.replace('_', ' ')}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; color: var(--accent-positive); font-weight: 600; font-family: 'JetBrains Mono', monospace;">Confidence: ${score.toFixed(0)}%</span>
                    <span style="font-size: 11px; color: var(--text-primary); font-weight: 600; font-family: 'JetBrains Mono', monospace;">+${(Math.random() * 15 + 5).toFixed(1)}%</span>
                </div>
            `;
            
            alphaItem.addEventListener('mouseenter', function() {
                this.style.transform = 'translateX(6px)';
                this.style.boxShadow = '0 6px 20px rgba(255, 193, 7, 0.3)';
            });
            
            alphaItem.addEventListener('mouseleave', function() {
                this.style.transform = '';
                this.style.boxShadow = '';
            });
            
            alphaList.appendChild(alphaItem);
        });

        // Update count
        const alphaCount = document.getElementById('alpha-count');
        if (alphaCount) {
            alphaCount.textContent = `${highBetaAssets.length} IDENTIFIED`;
        }
    }

    // Auto-update matrix periodically
    updateMatrix() {
        if (Math.random() > 0.8) {
            this.populateSignalMatrix();
        }
    }
}

// Global dashboard instance
let dashboardInstance = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Virtuoso Dashboard...');
    try {
        dashboardInstance = new VirtuosoDashboard();
        
        // Make dashboard accessible globally for debugging
        window.dashboard = dashboardInstance;
        
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        
        // Show error message to user
        const container = document.querySelector('.dashboard-container');
        if (container) {
            container.innerHTML = `
                <div class="error" style="text-align: center; padding: 50px;">
                    <h2>Dashboard Initialization Failed</h2>
                    <p>Error: ${error.message}</p>
                    <button onclick="location.reload()" class="btn">Reload Page</button>
                </div>
            `;
        }
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (dashboardInstance) {
        if (document.hidden) {
            console.log('Page hidden, reducing update frequency');
        } else {
            console.log('Page visible, resuming normal updates');
            dashboardInstance.refreshData();
        }
    }
});

// Handle before unload
window.addEventListener('beforeunload', () => {
    if (dashboardInstance && dashboardInstance.websocket) {
        dashboardInstance.websocket.close();
    }
});

// Error handling for uncaught errors
window.addEventListener('error', (event) => {
    console.error('Uncaught error:', event.error);
    if (dashboardInstance) {
        dashboardInstance.showNotification('An error occurred. Check console for details.', 'error');
    }
});

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VirtuosoDashboard;
} 