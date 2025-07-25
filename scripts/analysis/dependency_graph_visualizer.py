#!/usr/bin/env python3
"""
Dependency Graph Visualizer
Creates a visual representation of module dependencies
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import re

def create_mermaid_diagram(dependencies):
    """Create a Mermaid diagram of dependencies."""
    lines = ["graph TD"]
    
    # Define node styles for different modules
    styles = {
        'core': 'classDef core fill:#ff9999,stroke:#333,stroke-width:2px',
        'monitoring': 'classDef monitoring fill:#99ccff,stroke:#333,stroke-width:2px', 
        'analysis': 'classDef analysis fill:#99ff99,stroke:#333,stroke-width:2px',
        'indicators': 'classDef indicators fill:#ffcc99,stroke:#333,stroke-width:2px',
        'api': 'classDef api fill:#cc99ff,stroke:#333,stroke-width:2px',
        'signal_generation': 'classDef signal fill:#ffff99,stroke:#333,stroke-width:2px'
    }
    
    # Add nodes and edges
    edges = []
    circular_edges = []
    
    # Identify major modules and their relationships
    major_modules = ['core', 'monitoring', 'analysis', 'indicators', 'api', 'signal_generation']
    
    for from_module in major_modules:
        if from_module in dependencies:
            for to_module in major_modules:
                if to_module in dependencies[from_module]:
                    count = dependencies[from_module][to_module]
                    
                    # Check if this is a circular dependency
                    is_circular = (to_module in dependencies and 
                                 from_module in dependencies[to_module])
                    
                    if is_circular:
                        circular_edges.append(f"    {from_module} -.->|{count}| {to_module}")
                    else:
                        edges.append(f"    {from_module} -->|{count}| {to_module}")
    
    # Add edges to diagram
    lines.extend(edges)
    lines.extend(circular_edges)
    
    # Add styles
    lines.append("")
    for module, style in styles.items():
        lines.append(f"    {style}")
    
    # Add class assignments
    lines.append("")
    for module in major_modules:
        lines.append(f"    class {module} {module}")
    
    return "\n".join(lines)

def analyze_coupling_strength():
    """Analyze and categorize coupling strength."""
    # Data from our analysis
    coupling_data = {
        'core': {'monitoring': 9, 'analysis': 4, 'data_processing': 3, 'utils': 3, 'data_storage': 2, 'data_acquisition': 1},
        'monitoring': {'core': 28, 'utils': 7, 'reports': 4, 'signal_generation': 2, 'indicators': 2, 'analysis': 2},
        'analysis': {'indicators': 21, 'core': 6, 'api': 1},
        'indicators': {'analysis': 20, 'core': 9, 'utils': 15, 'config': 3, 'validation': 2},
        'api': {'core': 15, 'analysis': 6, 'monitoring': 5, 'dashboard': 3, 'data_storage': 1, 'validation': 1, 'reports': 1},
        'signal_generation': {'indicators': 6, 'core': 2, 'monitoring': 1, 'analysis': 1, 'data_processing': 1, 'models': 1, 'utils': 3}
    }
    
    return coupling_data

def generate_summary_report():
    """Generate a summary report of the analysis."""
    coupling_data = analyze_coupling_strength()
    
    report = ["# Circular Dependency Analysis Summary\n"]
    
    # Circular dependencies
    report.append("## 🔴 Critical Circular Dependencies\n")
    
    circular_deps = [
        ("core", "monitoring", 9, 28, "CRITICAL - Highest coupling strength (37)"),
        ("analysis", "indicators", 21, 20, "CRITICAL - Direct circular import detected"),
        ("core", "analysis", 4, 6, "MODERATE - Indirect coupling"),
        ("core", "data_processing", 3, 8, "MODERATE - Infrastructure coupling")
    ]
    
    for module1, module2, count1, count2, severity in circular_deps:
        report.append(f"### {module1.title()} ↔ {module2.title()}")
        report.append(f"- **{module1}** → **{module2}**: {count1} dependencies")
        report.append(f"- **{module2}** → **{module1}**: {count2} dependencies") 
        report.append(f"- **Total Coupling**: {count1 + count2}")
        report.append(f"- **Severity**: {severity}\n")
    
    # High coupling modules
    report.append("## 📊 Module Coupling Rankings\n")
    
    total_coupling = {}
    for module, deps in coupling_data.items():
        outgoing = sum(deps.values())
        incoming = sum(coupling_data[other].get(module, 0) for other in coupling_data)
        total_coupling[module] = outgoing + incoming
    
    sorted_modules = sorted(total_coupling.items(), key=lambda x: x[1], reverse=True)
    
    for i, (module, coupling) in enumerate(sorted_modules, 1):
        status = "🔴 CRITICAL" if coupling > 80 else "🟡 HIGH" if coupling > 40 else "🟢 MODERATE"
        report.append(f"{i}. **{module.title()}**: {coupling} total dependencies - {status}")
    
    report.append("\n")
    
    # Recommendations
    report.append("## 🛠️ Immediate Action Items\n")
    report.append("### Priority 1: Break Core-Monitoring Cycle")
    report.append("- Move AlertManager, MetricsManager to services layer")
    report.append("- Implement dependency injection")
    report.append("- Create monitoring interfaces in core")
    
    report.append("\n### Priority 2: Resolve Analysis-Indicators Cycle") 
    report.append("- Move DataValidator to shared/validation/")
    report.append("- Create abstract validator interfaces")
    report.append("- Update import statements")
    
    report.append("\n### Priority 3: Service Layer Architecture")
    report.append("- Create src/services/ for business logic")
    report.append("- Create src/interfaces/ for contracts")
    report.append("- Implement event-driven communication")
    
    report.append("\n### Priority 4: Shared Utilities")
    report.append("- Create src/shared/ for common utilities")
    report.append("- Move formatting, validation, error handling")
    report.append("- Reduce cross-module utility dependencies")
    
    return "\n".join(report)

def main():
    # Generate Mermaid diagram
    coupling_data = analyze_coupling_strength()
    mermaid_diagram = create_mermaid_diagram(coupling_data)
    
    # Generate summary report
    summary_report = generate_summary_report()
    
    # Write outputs
    root_path = Path(__file__).parent.parent.parent
    
    # Write Mermaid diagram
    with open(root_path / "docs/analysis/dependency_graph.mmd", 'w') as f:
        f.write(mermaid_diagram)
    
    # Write summary report
    with open(root_path / "docs/analysis/circular_dependency_summary.md", 'w') as f:
        f.write(summary_report)
    
    print("Generated dependency analysis files:")
    print("- docs/analysis/dependency_graph.mmd")
    print("- docs/analysis/circular_dependency_summary.md")
    print("\nMermaid Diagram Preview:")
    print("=" * 50)
    print(mermaid_diagram)
    print("=" * 50)
    print("\nSummary Report Preview:")
    print("=" * 50)
    print(summary_report[:1000] + "..." if len(summary_report) > 1000 else summary_report)

if __name__ == "__main__":
    main()