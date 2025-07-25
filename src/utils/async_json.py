"""Async JSON file operations utilities."""

import json
import aiofiles
from typing import Any, Dict, List, Union, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import custom JSON encoder if available
try:
    from .json_encoder import CustomJSONEncoder
    DEFAULT_ENCODER = CustomJSONEncoder
except ImportError:
    DEFAULT_ENCODER = None


async def load_json(filepath: Union[str, Path]) -> Union[Dict, List, Any]:
    """
    Asynchronously load JSON data from a file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Loaded JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)


async def save_json(
    filepath: Union[str, Path], 
    data: Union[Dict, List, Any],
    indent: Optional[int] = 2,
    ensure_ascii: bool = False,
    cls: Optional[type] = None
) -> None:
    """
    Asynchronously save data to a JSON file.
    
    Args:
        filepath: Path where to save the JSON file
        data: Data to save
        indent: JSON indentation level
        ensure_ascii: Whether to escape non-ASCII characters
        cls: Custom JSON encoder class
        
    Raises:
        TypeError: If data is not JSON serializable
    """
    filepath = Path(filepath)
    
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Use custom encoder if available and not specified
    if cls is None and DEFAULT_ENCODER is not None:
        cls = DEFAULT_ENCODER
    
    # Serialize to JSON string first
    json_str = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, cls=cls)
    
    # Write asynchronously
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(json_str)


async def append_json_line(
    filepath: Union[str, Path],
    data: Union[Dict, List, Any],
    cls: Optional[type] = None
) -> None:
    """
    Asynchronously append a JSON object as a new line (JSONL format).
    
    Args:
        filepath: Path to the JSONL file
        data: Data to append
        cls: Custom JSON encoder class
    """
    filepath = Path(filepath)
    
    # Use custom encoder if available and not specified
    if cls is None and DEFAULT_ENCODER is not None:
        cls = DEFAULT_ENCODER
    
    # Serialize to JSON string (no indentation for JSONL)
    json_str = json.dumps(data, cls=cls) + '\n'
    
    # Append asynchronously
    async with aiofiles.open(filepath, 'a', encoding='utf-8') as f:
        await f.write(json_str)


async def load_json_lines(filepath: Union[str, Path]) -> List[Union[Dict, List, Any]]:
    """
    Asynchronously load all JSON objects from a JSONL file.
    
    Args:
        filepath: Path to the JSONL file
        
    Returns:
        List of loaded JSON objects
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If any line contains invalid JSON
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"JSONL file not found: {filepath}")
    
    results = []
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        async for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON line: {e}")
                    continue
    
    return results


async def update_json(
    filepath: Union[str, Path],
    updates: Dict[str, Any],
    create_if_missing: bool = True
) -> Dict[str, Any]:
    """
    Asynchronously update a JSON file with new data.
    
    Args:
        filepath: Path to the JSON file
        updates: Dictionary of updates to apply
        create_if_missing: Create file if it doesn't exist
        
    Returns:
        Updated data
    """
    filepath = Path(filepath)
    
    # Load existing data or start with empty dict
    if filepath.exists():
        data = await load_json(filepath)
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict in {filepath}, got {type(data)}")
    elif create_if_missing:
        data = {}
    else:
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    
    # Update data
    data.update(updates)
    
    # Save back
    await save_json(filepath, data)
    
    return data


# Convenience functions that match the synchronous API
async def dump(
    obj: Any,
    fp: Union[str, Path],
    **kwargs
) -> None:
    """Async version of json.dump()."""
    await save_json(fp, obj, **kwargs)


async def load(fp: Union[str, Path]) -> Any:
    """Async version of json.load()."""
    return await load_json(fp)