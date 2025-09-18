"""
Configuration Management API Endpoints
Provides web interface for configuration wizard
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
import asyncio
import yaml
import os
from pathlib import Path

from src.config.wizard_enhanced import ConfigurationWizard

router = APIRouter(prefix="/api/config", tags=["configuration"])

# Pydantic models for API validation
class ExchangeCredentials(BaseModel):
    api_key: str = Field(..., min_length=10)
    api_secret: str = Field(..., min_length=10)

class ExchangeConfig(BaseModel):
    enabled: bool = True
    use_ccxt: bool = True
    testnet: bool = False
    primary: bool = False
    api_credentials: Optional[ExchangeCredentials] = None

class AnalysisConfig(BaseModel):
    orderflow_enabled: bool = True
    sentiment_enabled: bool = True
    liquidity_enabled: bool = True
    bitcoin_beta_enabled: bool = False
    smart_money_enabled: bool = False
    ml_patterns_enabled: bool = False

class MonitoringConfig(BaseModel):
    enabled: bool = True
    interval: int = Field(default=30, ge=15, le=300)
    alerts_enabled: bool = False
    discord_webhook: Optional[str] = None

class ConfigurationRequest(BaseModel):
    template: Optional[str] = None
    environment: str = "production"
    exchanges: Dict[str, ExchangeConfig] = {}
    analysis: AnalysisConfig = AnalysisConfig()
    monitoring: MonitoringConfig = MonitoringConfig()

class ConfigurationResponse(BaseModel):
    success: bool
    message: str
    config: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None

# Initialize wizard
wizard = ConfigurationWizard()

@router.get("/templates")
async def get_configuration_templates():
    """Get available configuration templates"""
    return {
        "templates": wizard.templates,
        "current_config": wizard.get_config_summary(wizard.current_config)
    }

@router.post("/apply-template")
async def apply_configuration_template(template_name: str):
    """Apply a configuration template"""
    try:
        config = wizard.apply_template(template_name)
        validation = wizard.validate_config(config)

        return ConfigurationResponse(
            success=validation['valid'],
            message=f"Template '{template_name}' applied",
            config=config,
            validation=validation
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate")
async def validate_configuration(request: ConfigurationRequest):
    """Validate a configuration"""
    config_dict = request.dict()

    # Build full configuration
    full_config = wizard.current_config.copy()
    full_config.update(config_dict)

    validation = wizard.validate_config(full_config)

    return {
        "valid": validation['valid'],
        "errors": validation['errors'],
        "warnings": validation['warnings'],
        "suggestions": validation['suggestions']
    }

@router.post("/test-exchange")
async def test_exchange_connection(exchange_name: str):
    """Test connection to an exchange"""
    if exchange_name not in wizard.current_config.get('exchanges', {}):
        raise HTTPException(status_code=404, detail=f"Exchange '{exchange_name}' not configured")

    result = await wizard.test_exchange_connection(exchange_name, wizard.current_config)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return result

@router.post("/save")
async def save_configuration(request: ConfigurationRequest):
    """Save configuration to file"""
    config_dict = request.dict()

    # Build full configuration
    full_config = wizard.current_config.copy()

    # Update with new values
    for key in ['environment', 'exchanges', 'analysis', 'monitoring']:
        if key in config_dict:
            full_config[key] = config_dict[key]

    # Validate before saving
    validation = wizard.validate_config(full_config)

    if not validation['valid']:
        return ConfigurationResponse(
            success=False,
            message="Configuration is invalid",
            config=None,
            validation=validation
        )

    # Save configuration
    if wizard.save_config(full_config):
        return ConfigurationResponse(
            success=True,
            message="Configuration saved successfully",
            config=full_config,
            validation=validation
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to save configuration")

@router.get("/current")
async def get_current_configuration():
    """Get current configuration"""
    return {
        "config": wizard.current_config,
        "summary": wizard.get_config_summary(wizard.current_config)
    }

@router.get("/wizard", response_class=HTMLResponse)
async def configuration_wizard_ui():
    """Web-based configuration wizard interface"""

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Virtuoso CCXT Configuration Wizard</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            .step { display: none; }
            .step.active { display: block; }
            .template-card { cursor: pointer; transition: all 0.3s; }
            .template-card:hover { transform: scale(1.02); }
            .template-card.selected { border-color: #3B82F6; background-color: #1F2937; }
        </style>
    </head>
    <body class="bg-gray-900 text-gray-100">
        <div class="container mx-auto p-8 max-w-4xl">
            <h1 class="text-4xl font-bold mb-8 text-center">🚀 Virtuoso CCXT Configuration Wizard</h1>

            <!-- Progress Bar -->
            <div class="mb-8">
                <div class="flex justify-between mb-2">
                    <span class="text-sm">Step <span id="currentStep">1</span> of 5</span>
                    <span class="text-sm" id="stepName">Select Template</span>
                </div>
                <div class="w-full bg-gray-700 rounded-full h-2">
                    <div id="progressBar" class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: 20%"></div>
                </div>
            </div>

            <!-- Step 1: Template Selection -->
            <div id="step1" class="step active">
                <h2 class="text-2xl font-bold mb-6">Choose Configuration Template</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="template-card bg-gray-800 p-6 rounded-lg border-2 border-gray-700" data-template="beginner">
                        <h3 class="text-xl font-bold mb-2">🌱 Beginner</h3>
                        <p class="text-gray-400 mb-4">Simple configuration for getting started</p>
                        <ul class="text-sm text-gray-500">
                            <li>• Single exchange (testnet)</li>
                            <li>• Basic analysis tools</li>
                            <li>• Minimal monitoring</li>
                        </ul>
                    </div>

                    <div class="template-card bg-gray-800 p-6 rounded-lg border-2 border-gray-700" data-template="advanced">
                        <h3 class="text-xl font-bold mb-2">⚡ Advanced</h3>
                        <p class="text-gray-400 mb-4">Full-featured configuration</p>
                        <ul class="text-sm text-gray-500">
                            <li>• Multiple exchanges</li>
                            <li>• All analysis tools</li>
                            <li>• Alert system enabled</li>
                        </ul>
                    </div>

                    <div class="template-card bg-gray-800 p-6 rounded-lg border-2 border-gray-700" data-template="professional">
                        <h3 class="text-xl font-bold mb-2">🏆 Professional</h3>
                        <p class="text-gray-400 mb-4">Enterprise configuration</p>
                        <ul class="text-sm text-gray-500">
                            <li>• Maximum performance</li>
                            <li>• Multi-tier caching</li>
                            <li>• Full monitoring suite</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Step 2: Exchange Configuration -->
            <div id="step2" class="step">
                <h2 class="text-2xl font-bold mb-6">Configure Exchanges</h2>
                <div id="exchangeConfig" class="space-y-4">
                    <!-- Dynamically populated -->
                </div>
            </div>

            <!-- Step 3: Analysis Components -->
            <div id="step3" class="step">
                <h2 class="text-2xl font-bold mb-6">Select Analysis Components</h2>
                <div class="space-y-4">
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="orderflow" class="w-5 h-5" checked>
                        <span>📊 Order Flow Analysis</span>
                    </label>
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="sentiment" class="w-5 h-5" checked>
                        <span>💭 Sentiment Analysis</span>
                    </label>
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="liquidity" class="w-5 h-5" checked>
                        <span>💧 Liquidity Analysis</span>
                    </label>
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="bitcoin_beta" class="w-5 h-5">
                        <span>₿ Bitcoin Beta Tracking</span>
                    </label>
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="smart_money" class="w-5 h-5">
                        <span>🧠 Smart Money Detection</span>
                    </label>
                    <label class="flex items-center space-x-3">
                        <input type="checkbox" id="ml_patterns" class="w-5 h-5">
                        <span>🤖 ML Pattern Recognition</span>
                    </label>
                </div>
            </div>

            <!-- Step 4: Monitoring & Alerts -->
            <div id="step4" class="step">
                <h2 class="text-2xl font-bold mb-6">Configure Monitoring</h2>
                <div class="space-y-4">
                    <div>
                        <label class="block mb-2">Monitoring Interval (seconds)</label>
                        <input type="number" id="monitoringInterval" class="w-full p-2 bg-gray-800 rounded" value="30" min="15" max="300">
                    </div>
                    <div>
                        <label class="block mb-2">Discord Webhook URL (optional)</label>
                        <input type="text" id="discordWebhook" class="w-full p-2 bg-gray-800 rounded" placeholder="https://discord.com/api/webhooks/...">
                    </div>
                </div>
            </div>

            <!-- Step 5: Review & Save -->
            <div id="step5" class="step">
                <h2 class="text-2xl font-bold mb-6">Review Configuration</h2>
                <div id="configSummary" class="bg-gray-800 p-6 rounded-lg mb-6">
                    <!-- Dynamically populated -->
                </div>
                <div id="validationResults" class="mb-6">
                    <!-- Dynamically populated -->
                </div>
            </div>

            <!-- Navigation Buttons -->
            <div class="flex justify-between mt-8">
                <button id="prevBtn" class="px-6 py-2 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50" disabled>Previous</button>
                <button id="nextBtn" class="px-6 py-2 bg-blue-500 rounded hover:bg-blue-600">Next</button>
            </div>
        </div>

        <script>
            let currentStep = 1;
            let totalSteps = 5;
            let selectedTemplate = null;
            let configuration = {};

            // Step names
            const stepNames = {
                1: 'Select Template',
                2: 'Configure Exchanges',
                3: 'Analysis Components',
                4: 'Monitoring Setup',
                5: 'Review & Save'
            };

            // Template selection
            document.querySelectorAll('.template-card').forEach(card => {
                card.addEventListener('click', () => {
                    document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedTemplate = card.dataset.template;
                });
            });

            // Navigation
            document.getElementById('nextBtn').addEventListener('click', async () => {
                if (currentStep === 1 && !selectedTemplate) {
                    alert('Please select a template');
                    return;
                }

                if (currentStep === totalSteps) {
                    // Save configuration
                    await saveConfiguration();
                } else {
                    currentStep++;
                    updateStep();
                }
            });

            document.getElementById('prevBtn').addEventListener('click', () => {
                currentStep--;
                updateStep();
            });

            function updateStep() {
                // Hide all steps
                document.querySelectorAll('.step').forEach(step => {
                    step.classList.remove('active');
                });

                // Show current step
                document.getElementById(`step${currentStep}`).classList.add('active');

                // Update progress
                document.getElementById('currentStep').textContent = currentStep;
                document.getElementById('stepName').textContent = stepNames[currentStep];
                document.getElementById('progressBar').style.width = `${(currentStep / totalSteps) * 100}%`;

                // Update buttons
                document.getElementById('prevBtn').disabled = currentStep === 1;
                document.getElementById('nextBtn').textContent = currentStep === totalSteps ? 'Save Configuration' : 'Next';

                // Load step-specific content
                if (currentStep === 2) {
                    loadExchangeConfig();
                } else if (currentStep === 5) {
                    loadSummary();
                }
            }

            async function loadExchangeConfig() {
                // Load template configuration
                const response = await fetch(`/api/config/apply-template?template_name=${selectedTemplate}`, {
                    method: 'POST'
                });
                const data = await response.json();

                let html = '';
                for (const [name, config] of Object.entries(data.config.exchanges || {})) {
                    html += `
                        <div class="bg-gray-800 p-4 rounded-lg">
                            <h3 class="font-bold mb-2">${name.toUpperCase()}</h3>
                            <label class="flex items-center space-x-3 mb-2">
                                <input type="checkbox" id="${name}_enabled" ${config.enabled ? 'checked' : ''}>
                                <span>Enable ${name}</span>
                            </label>
                            <div class="grid grid-cols-2 gap-4">
                                <input type="text" id="${name}_api_key" placeholder="API Key" class="p-2 bg-gray-700 rounded">
                                <input type="password" id="${name}_api_secret" placeholder="API Secret" class="p-2 bg-gray-700 rounded">
                            </div>
                        </div>
                    `;
                }
                document.getElementById('exchangeConfig').innerHTML = html;
            }

            async function loadSummary() {
                // Gather configuration
                configuration = {
                    template: selectedTemplate,
                    environment: 'production',
                    exchanges: {},
                    analysis: {
                        orderflow_enabled: document.getElementById('orderflow').checked,
                        sentiment_enabled: document.getElementById('sentiment').checked,
                        liquidity_enabled: document.getElementById('liquidity').checked,
                        bitcoin_beta_enabled: document.getElementById('bitcoin_beta').checked,
                        smart_money_enabled: document.getElementById('smart_money').checked,
                        ml_patterns_enabled: document.getElementById('ml_patterns').checked
                    },
                    monitoring: {
                        enabled: true,
                        interval: parseInt(document.getElementById('monitoringInterval').value),
                        discord_webhook: document.getElementById('discordWebhook').value
                    }
                };

                // Validate configuration
                const response = await fetch('/api/config/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configuration)
                });
                const validation = await response.json();

                // Display summary
                let summaryHtml = `
                    <h3 class="font-bold mb-2">Configuration Summary</h3>
                    <p>Template: ${selectedTemplate}</p>
                    <p>Analysis Components: ${Object.keys(configuration.analysis).filter(k => configuration.analysis[k]).length}</p>
                    <p>Monitoring Interval: ${configuration.monitoring.interval}s</p>
                `;
                document.getElementById('configSummary').innerHTML = summaryHtml;

                // Display validation results
                let validationHtml = '';
                if (validation.errors && validation.errors.length > 0) {
                    validationHtml += '<div class="bg-red-900 p-4 rounded mb-2">❌ Errors: ' + validation.errors.join(', ') + '</div>';
                }
                if (validation.warnings && validation.warnings.length > 0) {
                    validationHtml += '<div class="bg-yellow-900 p-4 rounded mb-2">⚠️ Warnings: ' + validation.warnings.join(', ') + '</div>';
                }
                if (validation.suggestions && validation.suggestions.length > 0) {
                    validationHtml += '<div class="bg-blue-900 p-4 rounded">💡 Suggestions: ' + validation.suggestions.join(', ') + '</div>';
                }
                document.getElementById('validationResults').innerHTML = validationHtml;
            }

            async function saveConfiguration() {
                const response = await fetch('/api/config/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configuration)
                });

                if (response.ok) {
                    alert('✅ Configuration saved successfully!');
                    window.location.href = '/';
                } else {
                    alert('❌ Failed to save configuration');
                }
            }
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)