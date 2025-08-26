#!/usr/bin/env python3
"""
Migration script to consolidate charting technologies
Replaces mixed chart implementations with unified system
"""

import os
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class ChartMigrationScript:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.backup_dir = self.project_root / 'backups' / f'chart_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.logger = self._setup_logger()
        
        # File patterns to migrate
        self.patterns = {
            'matplotlib_imports': [
                r'import matplotlib.*',
                r'from matplotlib.*',
                r'import matplotlib\.pyplot as plt',
                r'plt\.'
            ],
            'canvas_usage': [
                r'canvas\.getContext\([\'"]2d[\'"]\)',
                r'ctx\.(beginPath|moveTo|lineTo|stroke|fill)',
                r'new Chart\(',
                r'Chart\.js'
            ],
            'plotly_usage': [
                r'import plotly.*',
                r'from plotly.*',
                r'plotly\.',
                r'go\.'
            ]
        }
    
    def _setup_logger(self):
        """Setup logging for migration process"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('chart_migration.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def create_backup(self):
        """Create backup of files before migration"""
        self.logger.info("Creating backup...")
        
        files_to_backup = [
            'src/dashboard/templates/',
            'src/core/reporting/',
            'src/monitoring/monitor.py',
            'src/monitoring/visualizers/',
        ]
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in files_to_backup:
            source = self.project_root / file_path
            if source.exists():
                if source.is_file():
                    dest = self.backup_dir / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                else:
                    dest = self.backup_dir / file_path
                    shutil.copytree(source, dest, dirs_exist_ok=True)
                
                self.logger.info(f"Backed up: {file_path}")
    
    def scan_existing_implementations(self) -> Dict[str, List[str]]:
        """Scan codebase for existing chart implementations"""
        self.logger.info("Scanning existing chart implementations...")
        
        results = {
            'matplotlib_files': [],
            'canvas_files': [],
            'plotly_files': [],
            'chartjs_files': []
        }
        
        # Scan Python files
        for py_file in self.project_root.rglob('*.py'):
            if self._should_skip_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                if any(re.search(pattern, content, re.IGNORECASE) 
                       for pattern in self.patterns['matplotlib_imports']):
                    results['matplotlib_files'].append(str(py_file))
                
                if any(re.search(pattern, content, re.IGNORECASE)
                       for pattern in self.patterns['plotly_usage']):
                    results['plotly_files'].append(str(py_file))
                    
            except Exception as e:
                self.logger.warning(f"Could not read {py_file}: {e}")
        
        # Scan HTML files  
        for html_file in self.project_root.rglob('*.html'):
            if self._should_skip_file(html_file):
                continue
                
            try:
                content = html_file.read_text(encoding='utf-8')
                
                if any(re.search(pattern, content, re.IGNORECASE)
                       for pattern in self.patterns['canvas_usage']):
                    results['canvas_files'].append(str(html_file))
                
                if 'chart.js' in content.lower() or 'chartjs' in content.lower():
                    results['chartjs_files'].append(str(html_file))
                    
            except Exception as e:
                self.logger.warning(f"Could not read {html_file}: {e}")
        
        # Log results
        for category, files in results.items():
            self.logger.info(f"{category}: {len(files)} files found")
            for file in files[:5]:  # Show first 5
                self.logger.info(f"  - {file}")
            if len(files) > 5:
                self.logger.info(f"  ... and {len(files) - 5} more")
        
        return results
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during migration"""
        skip_patterns = [
            'backup', 'test', '__pycache__', '.git', 
            'node_modules', 'venv', '.pyc'
        ]
        
        return any(pattern in str(file_path).lower() for pattern in skip_patterns)
    
    def migrate_backend_charts(self):
        """Migrate backend matplotlib usage to unified system"""
        self.logger.info("Migrating backend chart implementations...")
        
        # Files to migrate
        backend_files = [
            'src/core/reporting/pdf_generator.py',
            'src/monitoring/monitor.py', 
            'src/monitoring/market_reporter.py',
            'src/reports/bitcoin_beta_report.py'
        ]
        
        for file_path in backend_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            self.logger.info(f"Migrating: {file_path}")
            
            try:
                content = full_path.read_text(encoding='utf-8')
                
                # Add unified chart import
                if 'from src.core.charts.chart_generator import chart_generator' not in content:
                    # Find import section
                    lines = content.split('\n')
                    import_section_end = 0
                    
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            import_section_end = i
                    
                    # Insert unified chart import
                    lines.insert(import_section_end + 1, 
                                'from src.core.charts.chart_generator import chart_generator')
                    content = '\n'.join(lines)
                
                # Create migration comment
                migration_comment = f"""
# MIGRATION NOTE: Chart generation migrated to unified system
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Replace matplotlib calls with chart_generator methods:
# - chart_generator.create_price_chart(data)
# - chart_generator.create_volume_chart(data) 
# - chart_generator.create_confluence_indicator(score)
"""
                
                # Add comment at top of file
                if 'MIGRATION NOTE' not in content:
                    lines = content.split('\n')
                    # Find first non-comment, non-import line
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if (not line.strip().startswith('#') and 
                            not line.strip().startswith('"""') and
                            not line.strip().startswith("'''") and
                            not line.startswith('import ') and
                            not line.startswith('from ') and
                            line.strip()):
                            insert_pos = i
                            break
                    
                    lines.insert(insert_pos, migration_comment)
                    content = '\n'.join(lines)
                
                # Write back
                full_path.write_text(content, encoding='utf-8')
                self.logger.info(f"Successfully migrated: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to migrate {file_path}: {e}")
    
    def migrate_frontend_charts(self):
        """Migrate frontend chart implementations"""
        self.logger.info("Migrating frontend chart implementations...")
        
        # Template files to migrate
        template_files = [
            'src/dashboard/templates/dashboard_mobile_v1.html',
            'src/dashboard/templates/performance_dashboard.html'
        ]
        
        for file_path in template_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            self.logger.info(f"Migrating template: {file_path}")
            
            try:
                content = full_path.read_text(encoding='utf-8')
                
                # Add unified chart script
                if '/static/js/unified-charts.js' not in content:
                    # Find script section or head
                    if '<script src="https://cdn.jsdelivr.net/npm/chart.js' in content:
                        chart_js_line = content.find('<script src="https://cdn.jsdelivr.net/npm/chart.js')
                        end_of_line = content.find('>', chart_js_line) + 1
                        
                        unified_script = '\n    <script src="/static/js/unified-charts.js"></script>'
                        content = content[:end_of_line] + unified_script + content[end_of_line:]
                    else:
                        # Add to head section
                        head_end = content.find('</head>')
                        if head_end > -1:
                            scripts = '''
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="/static/js/unified-charts.js"></script>
'''
                            content = content[:head_end] + scripts + content[head_end:]
                
                # Add migration comment
                migration_comment = f'''
<!-- MIGRATION NOTE: Charts migrated to unified system -->
<!-- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->
<!-- Use window.virtuosoCharts for all chart creation -->
<!-- Example: window.virtuosoCharts.createPriceChart('canvasId', data) -->
'''
                
                if 'MIGRATION NOTE' not in content:
                    body_start = content.find('<body>')
                    if body_start > -1:
                        content = content[:body_start] + migration_comment + content[body_start:]
                
                # Write back
                full_path.write_text(content, encoding='utf-8')
                self.logger.info(f"Successfully migrated template: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to migrate template {file_path}: {e}")
    
    def create_migration_guide(self):
        """Create comprehensive migration guide"""
        guide_content = f"""
# Chart Migration Guide
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This migration consolidates all charting technologies in the Virtuoso trading platform to use a unified system:
- **Frontend**: Standardized on Chart.js with unified wrapper
- **Backend**: Standardized matplotlib usage with consistent theming

## Migration Summary

### Files Created:
1. `src/dashboard/static/js/unified-charts.js` - Frontend unified chart system
2. `src/core/charts/chart_generator.py` - Backend unified chart generator  
3. `src/dashboard/templates/unified_dashboard_template.html` - Reference template
4. `scripts/migrate_to_unified_charts.py` - This migration script

### Key Changes:

#### Backend (Python):
**Before:**
```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(data)
plt.savefig('chart.png')
```

**After:**
```python
from src.core.charts.chart_generator import chart_generator
chart_base64 = chart_generator.create_price_chart(data, title="Price Chart")
```

#### Frontend (JavaScript):
**Before:**
```javascript
const ctx = canvas.getContext('2d');
// Manual canvas drawing or mixed Chart.js usage
```

**After:**
```javascript
window.virtuosoCharts.createPriceChart('canvasId', data, options);
```

## Benefits:
1. **Consistent Styling**: All charts use the same Virtuoso theme
2. **Performance**: Optimized rendering and hardware acceleration  
3. **Maintainability**: Single point of chart configuration
4. **Responsive**: Charts automatically adapt to different screen sizes
5. **Real-time Updates**: Efficient data update mechanisms

## Implementation Steps:

### Phase 1: Update Backend Code
1. Replace matplotlib chart generation with `chart_generator` methods
2. Update imports to use unified system
3. Test PDF generation and report charts

### Phase 2: Update Frontend Templates  
1. Replace custom canvas/Chart.js code with `virtuosoCharts` methods
2. Update data fetching to work with unified APIs
3. Test responsive behavior

### Phase 3: Performance Testing
1. Measure chart rendering performance
2. Test real-time data updates
3. Validate memory usage

### Phase 4: Cleanup
1. Remove obsolete chart code
2. Update documentation
3. Archive old implementations

## API Reference:

### Backend Methods:
- `chart_generator.create_price_chart(data, title, figsize, save_path)`
- `chart_generator.create_volume_chart(data, title, figsize, save_path)`
- `chart_generator.create_confluence_indicator(score, title, figsize, save_path)`
- `chart_generator.create_multi_symbol_comparison(data, title, figsize, save_path)`

### Frontend Methods:
- `virtuosoCharts.createPriceChart(canvasId, data, options)`
- `virtuosoCharts.createVolumeChart(canvasId, data, options)`  
- `virtuosoCharts.createConfluenceIndicator(canvasId, score, options)`
- `virtuosoCharts.createMarketBreadthChart(canvasId, data, options)`
- `virtuosoCharts.updateChart(chartId, newData, options)`

## Rollback Plan:
If issues arise, restore from backup directory: `{self.backup_dir}`

## Support:
- Check migration log: `chart_migration.log`
- Reference template: `src/dashboard/templates/unified_dashboard_template.html`
- Test with mock data before connecting real APIs

## Next Steps:
1. Review migrated files
2. Test chart rendering  
3. Update API endpoints to provide data in expected format
4. Deploy unified dashboard template
5. Monitor performance and user feedback
"""
        
        guide_path = self.project_root / 'CHART_MIGRATION_GUIDE.md'
        guide_path.write_text(guide_content, encoding='utf-8')
        self.logger.info(f"Migration guide created: {guide_path}")
    
    def run_migration(self):
        """Run complete migration process"""
        self.logger.info("Starting chart migration process...")
        
        try:
            # Step 1: Create backup
            self.create_backup()
            
            # Step 2: Scan existing implementations
            scan_results = self.scan_existing_implementations()
            
            # Step 3: Migrate backend
            self.migrate_backend_charts()
            
            # Step 4: Migrate frontend
            self.migrate_frontend_charts()
            
            # Step 5: Create guide
            self.create_migration_guide()
            
            self.logger.info("Migration completed successfully!")
            self.logger.info(f"Backup created at: {self.backup_dir}")
            self.logger.info("Next steps:")
            self.logger.info("1. Review migrated files")
            self.logger.info("2. Test chart rendering")
            self.logger.info("3. Update API endpoints")
            self.logger.info("4. Deploy unified template")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.logger.error("Restore from backup if needed")
            return False

if __name__ == "__main__":
    migrator = ChartMigrationScript()
    success = migrator.run_migration()
    exit(0 if success else 1)