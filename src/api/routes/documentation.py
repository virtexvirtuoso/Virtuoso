"""
Documentation Platform API Endpoints
Interactive documentation with search and tutorials
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import markdown
import os
from typing import List, Dict, Any

router = APIRouter(prefix="/docs", tags=["documentation"])

# Documentation root path
DOCS_ROOT = Path(__file__).parent.parent.parent.parent / 'docs'
STRATEGIC_ROADMAP_ROOT = DOCS_ROOT / 'strategic-roadmap'

@router.get("/", response_class=HTMLResponse)
async def documentation_home():
    """Interactive documentation platform home page"""

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Virtuoso CCXT Documentation</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
        <style>
            .doc-content { max-height: 80vh; overflow-y: auto; }
            .search-result { cursor: pointer; transition: all 0.2s; }
            .search-result:hover { background-color: #374151; }
            pre { background: #1a1a1a !important; padding: 1rem !important; border-radius: 0.5rem !important; }
            code { background: #2d2d2d; padding: 0.2rem 0.4rem; border-radius: 0.25rem; }
        </style>
    </head>
    <body class="bg-gray-900 text-gray-100">
        <div class="container mx-auto p-8">
            <header class="mb-12">
                <h1 class="text-5xl font-bold mb-4">📚 Virtuoso CCXT Documentation</h1>
                <p class="text-xl text-gray-400">Comprehensive guide to mastering algorithmic trading with Virtuoso CCXT</p>
            </header>

            <!-- Search Bar -->
            <div class="mb-12">
                <div class="relative">
                    <input
                        type="text"
                        id="searchInput"
                        class="w-full p-4 bg-gray-800 rounded-lg text-lg pr-12"
                        placeholder="Search documentation... (e.g., 'configuration', 'api', 'cache')"
                    >
                    <button onclick="searchDocs()" class="absolute right-2 top-2 p-2 bg-blue-500 rounded hover:bg-blue-600">
                        🔍
                    </button>
                </div>
                <div id="searchResults" class="mt-4 hidden bg-gray-800 rounded-lg p-4"></div>
            </div>

            <!-- Main Content Grid -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Quick Start -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-blue-400">🚀 Quick Start</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/quickstart" class="text-gray-300 hover:text-blue-400 block">5-Minute Setup Guide</a></li>
                        <li><a href="/api/config/wizard" class="text-gray-300 hover:text-blue-400 block">Configuration Wizard</a></li>
                        <li><a href="/docs/first-trade" class="text-gray-300 hover:text-blue-400 block">Your First Automated Trade</a></li>
                        <li><a href="/docs/troubleshooting" class="text-gray-300 hover:text-blue-400 block">Troubleshooting Guide</a></li>
                    </ul>
                </div>

                <!-- Core Concepts -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-green-400">📖 Core Concepts</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/architecture" class="text-gray-300 hover:text-green-400 block">System Architecture</a></li>
                        <li><a href="/docs/6d-analysis" class="text-gray-300 hover:text-green-400 block">6-Dimensional Analysis</a></li>
                        <li><a href="/docs/caching" class="text-gray-300 hover:text-green-400 block">Multi-Tier Caching</a></li>
                        <li><a href="/docs/performance" class="text-gray-300 hover:text-green-400 block">Performance Optimization</a></li>
                    </ul>
                </div>

                <!-- API Reference -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-purple-400">🔧 API Reference</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/api/signals" class="text-gray-300 hover:text-purple-400 block">Signal Generation API</a></li>
                        <li><a href="/docs/api/market" class="text-gray-300 hover:text-purple-400 block">Market Data API</a></li>
                        <li><a href="/docs/api/dashboard" class="text-gray-300 hover:text-purple-400 block">Dashboard API</a></li>
                        <li><a href="/docs/api/websocket" class="text-gray-300 hover:text-purple-400 block">WebSocket Streams</a></li>
                    </ul>
                </div>

                <!-- Trading Strategies -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-yellow-400">📈 Trading Strategies</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/strategies/confluence" class="text-gray-300 hover:text-yellow-400 block">Confluence Trading</a></li>
                        <li><a href="/docs/strategies/smart-money" class="text-gray-300 hover:text-yellow-400 block">Smart Money Detection</a></li>
                        <li><a href="/docs/strategies/liquidation" class="text-gray-300 hover:text-yellow-400 block">Liquidation Intelligence</a></li>
                        <li><a href="/docs/strategies/risk" class="text-gray-300 hover:text-yellow-400 block">Risk Management</a></li>
                    </ul>
                </div>

                <!-- Advanced Topics -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-red-400">🎓 Advanced Topics</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/advanced/custom-indicators" class="text-gray-300 hover:text-red-400 block">Custom Indicators</a></li>
                        <li><a href="/docs/advanced/ml-patterns" class="text-gray-300 hover:text-red-400 block">ML Pattern Recognition</a></li>
                        <li><a href="/docs/advanced/scaling" class="text-gray-300 hover:text-red-400 block">Scaling & Performance</a></li>
                        <li><a href="/docs/advanced/deployment" class="text-gray-300 hover:text-red-400 block">Production Deployment</a></li>
                    </ul>
                </div>

                <!-- Video Tutorials -->
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-pink-400">🎥 Video Tutorials</h2>
                    <ul class="space-y-3">
                        <li><a href="/docs/videos/getting-started" class="text-gray-300 hover:text-pink-400 block">Getting Started (5 min)</a></li>
                        <li><a href="/docs/videos/configuration" class="text-gray-300 hover:text-pink-400 block">Configuration Deep Dive</a></li>
                        <li><a href="/docs/videos/live-trading" class="text-gray-300 hover:text-pink-400 block">Live Trading Demo</a></li>
                        <li><a href="/docs/videos/troubleshooting" class="text-gray-300 hover:text-pink-400 block">Common Issues & Fixes</a></li>
                    </ul>
                </div>
            </div>

            <!-- Strategic Roadmap Section -->
            <div class="mt-12 bg-gray-800 p-8 rounded-lg">
                <h2 class="text-3xl font-bold mb-6 text-indigo-400">🗺️ Strategic Roadmap</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-xl font-bold mb-3">Phase 1: Foundation</h3>
                        <ul class="space-y-2">
                            <li><a href="/docs/roadmap/phase-1" class="text-gray-300 hover:text-indigo-400">✅ Performance Optimization (95% Complete)</a></li>
                            <li><a href="/docs/roadmap/phase-1" class="text-gray-300 hover:text-indigo-400">✅ Architecture Simplification (90% Complete)</a></li>
                            <li><a href="/docs/roadmap/phase-1" class="text-gray-300 hover:text-indigo-400">⚠️ User Experience (40% Complete)</a></li>
                        </ul>
                    </div>
                    <div>
                        <h3 class="text-xl font-bold mb-3">Quick Wins</h3>
                        <ul class="space-y-2">
                            <li><a href="/docs/roadmap/quick-wins" class="text-gray-300 hover:text-indigo-400">✅ CCXT Integration (75% Complete)</a></li>
                            <li><a href="/docs/roadmap/quick-wins" class="text-gray-300 hover:text-indigo-400">✅ SmartMoney Detection (Deployed)</a></li>
                            <li><a href="/docs/roadmap/quick-wins" class="text-gray-300 hover:text-indigo-400">✅ Performance Monitoring (Active)</a></li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Interactive Examples -->
            <div class="mt-12 bg-gray-800 p-8 rounded-lg">
                <h2 class="text-3xl font-bold mb-6">💻 Interactive Examples</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-xl font-bold mb-3">Quick API Test</h3>
                        <button onclick="testAPI()" class="px-4 py-2 bg-blue-500 rounded hover:bg-blue-600">Test Health Endpoint</button>
                        <pre id="apiResult" class="mt-4 hidden"><code class="language-json"></code></pre>
                    </div>
                    <div>
                        <h3 class="text-xl font-bold mb-3">Configuration Check</h3>
                        <button onclick="checkConfig()" class="px-4 py-2 bg-green-500 rounded hover:bg-green-600">Check Current Config</button>
                        <pre id="configResult" class="mt-4 hidden"><code class="language-json"></code></pre>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
        <script>
            async function searchDocs() {
                const query = document.getElementById('searchInput').value;
                if (!query) return;

                const response = await fetch(`/docs/search?q=${encodeURIComponent(query)}`);
                const results = await response.json();

                let html = '<h3 class="font-bold mb-4">Search Results</h3>';
                if (results.length === 0) {
                    html += '<p class="text-gray-400">No results found</p>';
                } else {
                    html += '<ul class="space-y-2">';
                    results.forEach(result => {
                        html += `<li class="search-result p-2 rounded" onclick="loadDoc('${result.path}')">
                            <strong>${result.title}</strong> - ${result.snippet}
                        </li>`;
                    });
                    html += '</ul>';
                }

                const resultsDiv = document.getElementById('searchResults');
                resultsDiv.innerHTML = html;
                resultsDiv.classList.remove('hidden');
            }

            async function testAPI() {
                const response = await fetch('/health');
                const data = await response.json();

                const resultDiv = document.getElementById('apiResult');
                resultDiv.querySelector('code').textContent = JSON.stringify(data, null, 2);
                resultDiv.classList.remove('hidden');
                Prism.highlightElement(resultDiv.querySelector('code'));
            }

            async function checkConfig() {
                const response = await fetch('/api/config/current');
                const data = await response.json();

                const resultDiv = document.getElementById('configResult');
                resultDiv.querySelector('code').textContent = JSON.stringify(data.summary, null, 2);
                resultDiv.classList.remove('hidden');
                Prism.highlightElement(resultDiv.querySelector('code'));
            }

            function loadDoc(path) {
                window.location.href = `/docs/view?path=${encodeURIComponent(path)}`;
            }

            // Enter key search
            document.getElementById('searchInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') searchDocs();
            });
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@router.get("/search")
async def search_documentation(q: str):
    """Search documentation files"""
    results = []
    query = q.lower()

    # Search in docs directory
    for root, dirs, files in os.walk(DOCS_ROOT):
        for file in files:
            if file.endswith('.md'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        content_lower = content.lower()

                        if query in content_lower:
                            # Extract snippet around the match
                            index = content_lower.find(query)
                            start = max(0, index - 50)
                            end = min(len(content), index + 100)
                            snippet = content[start:end].replace('\n', ' ')

                            results.append({
                                'title': file.replace('.md', '').replace('-', ' ').title(),
                                'path': str(file_path.relative_to(DOCS_ROOT)),
                                'snippet': f"...{snippet}..."
                            })

                            if len(results) >= 10:
                                break
                except Exception:
                    continue

        if len(results) >= 10:
            break

    return results

@router.get("/view", response_class=HTMLResponse)
async def view_documentation(path: str):
    """View a specific documentation file"""
    file_path = DOCS_ROOT / path

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert markdown to HTML
        html = markdown.markdown(content, extensions=['fenced_code', 'tables', 'toc'])

        # Wrap in HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{path} - Virtuoso CCXT Documentation</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
            <style>
                .markdown-body {{ max-width: 900px; margin: 0 auto; }}
                .markdown-body h1 {{ font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem; }}
                .markdown-body h2 {{ font-size: 2rem; font-weight: bold; margin-top: 2rem; margin-bottom: 1rem; }}
                .markdown-body h3 {{ font-size: 1.5rem; font-weight: bold; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
                .markdown-body p {{ margin-bottom: 1rem; line-height: 1.8; }}
                .markdown-body code {{ background: #2d2d2d; padding: 0.2rem 0.4rem; border-radius: 0.25rem; }}
                .markdown-body pre {{ background: #1a1a1a; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }}
                .markdown-body ul {{ list-style: disc; padding-left: 2rem; margin-bottom: 1rem; }}
                .markdown-body table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; }}
                .markdown-body th {{ background: #374151; padding: 0.5rem; text-align: left; }}
                .markdown-body td {{ border: 1px solid #4b5563; padding: 0.5rem; }}
            </style>
        </head>
        <body class="bg-gray-900 text-gray-100">
            <div class="container mx-auto p-8">
                <div class="mb-4">
                    <a href="/docs" class="text-blue-400 hover:text-blue-300">← Back to Documentation</a>
                </div>
                <div class="markdown-body bg-gray-800 p-8 rounded-lg">
                    {html}
                </div>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-yaml.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
            <script>Prism.highlightAll();</script>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading document: {str(e)}")

@router.get("/roadmap/{phase}")
async def get_roadmap_documentation(phase: str):
    """Get strategic roadmap documentation for a specific phase"""
    phase_map = {
        'phase-1': 'phase-1-foundation',
        'quick-wins': 'quick-wins'
    }

    if phase not in phase_map:
        raise HTTPException(status_code=404, detail="Phase not found")

    phase_dir = STRATEGIC_ROADMAP_ROOT / phase_map[phase]

    if not phase_dir.exists():
        raise HTTPException(status_code=404, detail="Phase documentation not found")

    documents = []
    for file in phase_dir.glob('*.md'):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()[:200]  # First 200 chars as preview

        documents.append({
            'name': file.stem,
            'title': file.stem.replace('-', ' ').replace('_', ' ').title(),
            'preview': content,
            'path': str(file.relative_to(DOCS_ROOT))
        })

    return documents