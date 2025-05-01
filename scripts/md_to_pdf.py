import markdown
import os
from weasyprint import HTML
from pygments.formatters import HtmlFormatter
import sys

def md_to_pdf(input_file, output_file):
    # Read Markdown content
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Define CSS styles for the PDF
    css_styles = """
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 2em;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #333;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    p, ul, ol, dl, table, pre {
        margin-bottom: 1em;
    }
    code, pre {
        font-family: Monaco, Consolas, monospace;
        font-size: 90%;
        background-color: #f8f8f8;
        padding: 0.2em 0.4em;
        border-radius: 3px;
    }
    pre {
        padding: 1em;
        overflow: auto;
        line-height: 1.4;
    }
    a {
        color: #0366d6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    table {
        border-collapse: collapse;
        width: 100%;
    }
    table th, table td {
        border: 1px solid #ddd;
        padding: 8px;
    }
    table th {
        padding-top: 12px;
        padding-bottom: 12px;
        text-align: left;
        background-color: #f2f2f2;
    }
    blockquote {
        border-left: 3px solid #ddd;
        color: #666;
        margin: 0;
        padding-left: 1em;
    }
    img {
        max-width: 100%;
    }
    """
    
    # Add Pygments CSS for code highlighting
    css_styles += HtmlFormatter().get_style_defs('.codehilite')
    
    # Convert Markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code'
        ]
    )
    
    # Create full HTML with CSS
    html_full = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{os.path.basename(input_file)}</title>
        <style>
            {css_styles}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF using WeasyPrint
    HTML(string=html_full).write_pdf(output_file)
    print(f"PDF generated: {output_file}")

if __name__ == "__main__":
    # Check if parameters are provided
    if len(sys.argv) != 3:
        print("Usage: python md_to_pdf.py <input_markdown_file> <output_pdf_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    md_to_pdf(input_file, output_file) 