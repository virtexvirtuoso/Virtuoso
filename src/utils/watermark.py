"""
Virtuoso Watermark Utility

Production-ready watermark generation using Playwright for browser-quality rendering.
The watermark PNG is generated once and cached for reuse.

Usage:
    from src.utils.watermark import add_watermark

    fig, ax = plt.subplots()
    ax.plot(x, y)
    add_watermark(fig)  # Adds watermark to bottom-right
    plt.savefig('chart.png')
"""

import os
import logging
from pathlib import Path
from typing import Optional, Literal
import numpy as np

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / 'assets' / 'branding'
WATERMARK_PATH = ASSETS_DIR / 'virtuoso_watermark_browser.png'

# Watermark HTML template with brand styling
WATERMARK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@700&display=swap');

        * { margin: 0; padding: 0; }
        body {
            background: transparent;
            display: inline-block;
        }
        .watermark {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #0a0a0a;
            border: 2px solid #fbbf24;
            border-radius: 8px;
            padding: 8px 16px 8px 12px;
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 700;
            font-size: 18px;
            color: #fbbf24;
        }
        .icon {
            width: 24px;
            height: 24px;
        }
        .icon path {
            stroke: #fbbf24;
            stroke-width: 2.5;
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
    </style>
</head>
<body>
    <div class="watermark">
        <svg class="icon" viewBox="0 0 24 24">
            <path d="M2 20L8 14L12 18L22 8"/>
            <path d="M16 8H22V14"/>
        </svg>
        <span>VIRTUOSO</span>
    </div>
</body>
</html>
"""


def generate_watermark_png(force_regenerate: bool = False) -> Path:
    """
    Generate the watermark PNG using Playwright browser rendering.

    The PNG is cached and only regenerated if it doesn't exist or force_regenerate=True.

    Args:
        force_regenerate: Force regeneration even if PNG exists

    Returns:
        Path to the generated PNG file
    """
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Use cached version if available
    if WATERMARK_PATH.exists() and not force_regenerate:
        logger.debug(f"Using cached watermark: {WATERMARK_PATH}")
        return WATERMARK_PATH

    logger.info("Generating watermark PNG with Playwright...")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 400, 'height': 100})

            page.set_content(WATERMARK_HTML)
            page.wait_for_load_state('networkidle')

            watermark_element = page.locator('.watermark')
            watermark_element.screenshot(
                path=str(WATERMARK_PATH),
                omit_background=True,
                scale='device'
            )

            browser.close()

        logger.info(f"Watermark generated: {WATERMARK_PATH}")
        return WATERMARK_PATH

    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        raise
    except Exception as e:
        logger.error(f"Failed to generate watermark: {e}")
        raise


def add_watermark(
    fig,
    position: Literal['bottom-right', 'bottom-left', 'top-right', 'top-left'] = 'bottom-right',
    zoom: float = 0.5,
    padding: float = 0.02,
    alpha: float = 1.0
) -> None:
    """
    Add the Virtuoso watermark to a matplotlib figure.

    Uses axes fraction coordinates to work properly with bbox_inches='tight'.

    Args:
        fig: matplotlib Figure object
        position: Corner position for the watermark
        zoom: Scale factor (0.5 = 50% of original size)
        padding: Padding from axes edges (in axes fraction)
        alpha: Transparency (1.0 = fully opaque)

    Example:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        add_watermark(fig, position='bottom-right')
        plt.savefig('chart.png', dpi=150, bbox_inches='tight')
    """
    from PIL import Image
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox

    # Ensure watermark PNG exists
    watermark_path = generate_watermark_png()

    # Load watermark image
    watermark_img = Image.open(watermark_path)
    if alpha < 1.0:
        # Apply alpha to the image
        watermark_img = watermark_img.copy()
        watermark_img.putalpha(int(255 * alpha))

    watermark_array = np.array(watermark_img)

    # Get the primary axes
    ax = fig.axes[0] if fig.axes else fig.add_subplot(111)

    # Position relative to axes (works with bbox_inches='tight')
    position_map = {
        'bottom-right': (1.0 - padding, padding),
        'bottom-left': (padding, padding),
        'top-right': (1.0 - padding, 1.0 - padding),
        'top-left': (padding, 1.0 - padding),
    }

    alignment_map = {
        'bottom-right': (1.0, 0.0),
        'bottom-left': (0.0, 0.0),
        'top-right': (1.0, 1.0),
        'top-left': (0.0, 1.0),
    }

    x, y = position_map[position]
    box_alignment = alignment_map[position]

    # Create image box
    imagebox = OffsetImage(watermark_array, zoom=zoom)

    # Use axes fraction for positioning - this works with tight bbox
    ab = AnnotationBbox(
        imagebox,
        (x, y),
        xycoords='axes fraction',
        box_alignment=box_alignment,
        pad=0,
        frameon=False
    )

    ax.add_artist(ab)


def add_watermark_to_axes(
    ax,
    position: Literal['bottom-right', 'bottom-left', 'top-right', 'top-left'] = 'bottom-right',
    zoom: float = 0.5,
    padding: float = 0.02
) -> None:
    """
    Add watermark relative to axes bounds (useful for subplots).

    Args:
        ax: matplotlib Axes object
        position: Corner position for the watermark
        zoom: Scale factor
        padding: Padding from axes edges
    """
    from PIL import Image
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox

    watermark_path = generate_watermark_png()
    watermark_img = Image.open(watermark_path)
    watermark_array = np.array(watermark_img)

    position_map = {
        'bottom-right': (1.0 - padding, padding),
        'bottom-left': (padding, padding),
        'top-right': (1.0 - padding, 1.0 - padding),
        'top-left': (padding, 1.0 - padding),
    }

    alignment_map = {
        'bottom-right': (1.0, 0.0),
        'bottom-left': (0.0, 0.0),
        'top-right': (1.0, 1.0),
        'top-left': (0.0, 1.0),
    }

    x, y = position_map[position]
    box_alignment = alignment_map[position]

    imagebox = OffsetImage(watermark_array, zoom=zoom)

    ab = AnnotationBbox(
        imagebox,
        (x, y),
        xycoords='axes fraction',
        box_alignment=box_alignment,
        pad=0,
        frameon=False
    )

    ax.add_artist(ab)


def add_watermark_to_figure(
    fig,
    position: Literal['bottom-right', 'bottom-left', 'top-right', 'top-left'] = 'bottom-right',
    zoom: float = 0.5,
    padding: float = 0.02
) -> None:
    """
    Add watermark at figure level (useful for multi-panel charts like mplfinance).

    This positions the watermark relative to the entire figure, not a specific axes.
    Ideal for charts with volume panels where you want the watermark below all content.

    Note: When using this function, avoid using bbox_inches='tight' when saving,
    or the watermark may be cropped. Use pad_inches instead.

    Args:
        fig: matplotlib Figure object
        position: Corner position for the watermark
        zoom: Scale factor (0.5 = 50% of original size)
        padding: Padding from figure edges (in figure fraction, 0.02 = 2%)

    Example:
        fig, axes = mpf.plot(df, returnfig=True, volume=True)
        add_watermark_to_figure(fig, position='bottom-right')
        fig.savefig('chart.png', dpi=150, pad_inches=0.1, facecolor=fig.get_facecolor())
    """
    from PIL import Image
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox

    watermark_path = generate_watermark_png()
    watermark_img = Image.open(watermark_path)
    watermark_array = np.array(watermark_img)

    position_map = {
        'bottom-right': (1.0 - padding, padding),
        'bottom-left': (padding, padding),
        'top-right': (1.0 - padding, 1.0 - padding),
        'top-left': (padding, 1.0 - padding),
    }

    alignment_map = {
        'bottom-right': (1.0, 0.0),
        'bottom-left': (0.0, 0.0),
        'top-right': (1.0, 1.0),
        'top-left': (0.0, 1.0),
    }

    x, y = position_map[position]
    box_alignment = alignment_map[position]

    imagebox = OffsetImage(watermark_array, zoom=zoom)

    ab = AnnotationBbox(
        imagebox,
        (x, y),
        xycoords='figure fraction',
        box_alignment=box_alignment,
        pad=0,
        frameon=False
    )

    fig.add_artist(ab)


# Pre-generate watermark on module import (optional, can be commented out)
# This ensures the PNG exists before first use
if __name__ != '__main__':
    try:
        # Only generate if not already cached
        if not WATERMARK_PATH.exists():
            generate_watermark_png()
    except Exception:
        # Don't fail on import, will fail when actually used
        pass
