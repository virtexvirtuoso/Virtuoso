"""
Watermark utility for adding Virtuoso branding to matplotlib charts.

This module provides functions to render and embed the Virtuoso logo watermark
with correct aspect ratio preservation and high-quality anti-aliasing.
"""

import os
from io import BytesIO
import numpy as np
from PIL import Image
import cairosvg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox


def get_watermark_path():
    """Get the path to the SVG watermark file."""
    # Navigate from src/utils/ to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(project_root, 'assets', 'branding', 'virtuoso_watermark.svg')


def render_watermark_to_array(svg_path=None, target_width=160, scale_factor=3):
    """
    Render SVG watermark to numpy array with proper aspect ratio.

    Args:
        svg_path: Path to SVG file (defaults to virtuoso_watermark.svg)
        target_width: Target display width in pixels (default: 160)
        scale_factor: Render at this multiple for crispness (default: 3)

    Returns:
        numpy.ndarray: RGBA image array ready for matplotlib OffsetImage

    Technical notes:
        - Renders at scale_factor*target_width for anti-aliasing
        - CairoSVG preserves viewBox aspect ratio when height not specified
        - Returns high-res array to be scaled down via OffsetImage zoom parameter
    """
    if svg_path is None:
        svg_path = get_watermark_path()

    # Render at high resolution for crispness
    # CairoSVG will maintain aspect ratio from SVG viewBox
    png_data = cairosvg.svg2png(
        url=svg_path,
        output_width=target_width * scale_factor,
    )

    # Convert to PIL Image then numpy array
    img = Image.open(BytesIO(png_data))
    return np.array(img)


def add_watermark_to_axes(
    ax,
    position='bottom-right',
    target_width=160,
    scale_factor=3,
    offset=(0.02, -0.05),
    svg_path=None
):
    """
    Add Virtuoso watermark to matplotlib axes.

    Args:
        ax: Matplotlib axes object
        position: One of 'bottom-right', 'bottom-left', 'top-right', 'top-left'
        target_width: Display width in pixels (default: 160)
        scale_factor: Render scale for crispness (default: 3)
        offset: (x, y) offset from corner as fraction (default: (0.02, -0.05))
        svg_path: Custom SVG path (defaults to Virtuoso watermark)

    Returns:
        AnnotationBbox: The added watermark artist

    Example:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 9])
        >>> add_watermark_to_axes(ax, position='bottom-right')
        >>> plt.savefig('chart.png', dpi=150)
    """
    # Render watermark
    logo_array = render_watermark_to_array(
        svg_path=svg_path,
        target_width=target_width,
        scale_factor=scale_factor
    )

    # Create OffsetImage with Lanczos interpolation for quality
    # Zoom = 1/scale_factor to scale down from high-res rendering
    imagebox = OffsetImage(
        logo_array,
        zoom=1/scale_factor,
        interpolation='lanczos'
    )

    # Determine position coordinates and alignment
    position_map = {
        'bottom-right': ((1.0, 0.0), (1.0 + offset[0], offset[1])),
        'bottom-left': ((0.0, 0.0), (0.0 - offset[0], offset[1])),
        'top-right': ((1.0, 1.0), (1.0 + offset[0], 1.0 - offset[1])),
        'top-left': ((0.0, 1.0), (0.0 - offset[0], 1.0 - offset[1])),
    }

    if position not in position_map:
        raise ValueError(
            f"Invalid position '{position}'. "
            f"Must be one of: {list(position_map.keys())}"
        )

    xy, box_alignment = position_map[position]

    # Add to axes
    ab = AnnotationBbox(
        imagebox,
        xy,
        xycoords='axes fraction',
        box_alignment=box_alignment,
        pad=0,
        frameon=False
    )
    ax.add_artist(ab)

    return ab


def save_watermark_png(output_path=None, width=320):
    """
    Save standalone watermark PNG at specified resolution.

    Args:
        output_path: Output file path (defaults to assets/branding/virtuoso_watermark.png)
        width: PNG width in pixels (default: 320 for 2x resolution)

    Returns:
        str: Path to saved PNG file
    """
    if output_path is None:
        svg_path = get_watermark_path()
        output_path = svg_path.replace('.svg', '.png')

    # Render at target width (no scale factor needed for standalone PNG)
    png_data = cairosvg.svg2png(
        url=get_watermark_path(),
        output_width=width,
    )

    img = Image.open(BytesIO(png_data))
    img.save(output_path, 'PNG')

    return output_path
