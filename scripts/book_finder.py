#!/usr/bin/env python3
"""
Quantitative Finance Book Finder and Copier
Searches the computer for specified finance books and copies them to a desktop folder.
"""

import os
import shutil
import re
from pathlib import Path
import logging
from typing import List, Dict, Set
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('book_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BookFinder:
    def __init__(self, desktop_path: str = None):
        """Initialize the book finder with target books and search parameters."""
        
        # Get desktop path
        if desktop_path is None:
            self.desktop_path = Path.home() / "Desktop"
        else:
            self.desktop_path = Path(desktop_path)
            
        # Create target folder for found books
        self.target_folder = self.desktop_path / "Quantitative_Finance_Books"
        self.target_folder.mkdir(exist_ok=True)
        
        # Define book titles and authors for search
        self.books_data = [
            {
                "title": "Market Microstructure Theory",
                "author": "Maureen O'Hara",
                "keywords": ["market", "microstructure", "theory", "ohara"]
            },
            {
                "title": "Algorithmic and High-Frequency Trading",
                "author": "Álvaro Cartea, Sebastian Jaimungal, José Penalva",
                "keywords": ["algorithmic", "high-frequency", "trading", "cartea", "jaimungal"]
            },
            {
                "title": "Trading and Exchanges",
                "author": "Larry Harris",
                "keywords": ["trading", "exchanges", "harris"]
            },
            {
                "title": "The Science of Algorithmic Trading and Portfolio Management",
                "author": "Robert Kissell",
                "keywords": ["science", "algorithmic", "trading", "portfolio", "management", "kissell"]
            },
            {
                "title": "Statistical Arbitrage",
                "author": "Andrew Pole",
                "keywords": ["statistical", "arbitrage", "pole"]
            },
            {
                "title": "Quantitative Trading",
                "author": "Ernest P. Chan",
                "keywords": ["quantitative", "trading", "chan"]
            },
            {
                "title": "Advances in Financial Machine Learning",
                "author": "Marcos López de Prado",
                "keywords": ["advances", "financial", "machine", "learning", "lopez", "prado"]
            },
            {
                "title": "Active Portfolio Management",
                "author": "Richard Grinold & Ronald Kahn",
                "keywords": ["active", "portfolio", "management", "grinold", "kahn"]
            },
            {
                "title": "Inside the Black Box",
                "author": "Rishi K. Narang",
                "keywords": ["inside", "black", "box", "narang", "quantitative", "high-frequency"]
            },
            {
                "title": "Machine Learning for Algorithmic Trading",
                "author": "Stefan Jansen",
                "keywords": ["machine", "learning", "algorithmic", "trading", "jansen"]
            },
            {
                "title": "High-Frequency Trading: A Practical Guide",
                "author": "Irene Aldridge",
                "keywords": ["high-frequency", "trading", "practical", "guide", "aldridge"]
            },
            {
                "title": "Empirical Market Microstructure",
                "author": "Joel Hasbrouck",
                "keywords": ["empirical", "market", "microstructure", "hasbrouck"]
            },
            {
                "title": "Market Liquidity",
                "author": "Thierry Foucault, Marco Pagano, Ailsa Röell",
                "keywords": ["market", "liquidity", "foucault", "pagano", "roell"]
            },
            {
                "title": "Algorithmic Trading: Winning Strategies",
                "author": "Ernest P. Chan",
                "keywords": ["algorithmic", "trading", "winning", "strategies", "chan"]
            },
            {
                "title": "Quantitative Portfolio Management",
                "author": "Michael Isichenko",
                "keywords": ["quantitative", "portfolio", "management", "isichenko"]
            },
            {
                "title": "The Elements of Statistical Learning",
                "author": "Trevor Hastie, Robert Tibshirani, Jerome Friedman",
                "keywords": ["elements", "statistical", "learning", "hastie", "tibshirani", "friedman"]
            }
        ]
        
        # File extensions to search for
        self.file_extensions = {'.pdf', '.epub', '.mobi', '.djvu', '.txt', '.doc', '.docx'}
        
        # Directories to search (common locations)
        self.search_directories = [
            Path.home(),
            Path.home() / "Documents",
            Path.home() / "Downloads", 
            Path.home() / "Desktop",
            Path.home() / "Books",
            Path.home() / "Library",
            Path("/Applications"),  # macOS
            Path("/Users/Shared"),  # macOS shared
        ]
        
        # Add additional common paths on macOS
        if os.name == 'posix':  # Unix-like systems including macOS
            self.search_directories.extend([
                Path("/Volumes"),  # External drives on macOS
                Path.home() / "iCloud Drive",
                Path.home() / "Google Drive",
                Path.home() / "Dropbox",
                Path.home() / "OneDrive"
            ])
            
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing special characters and converting to lowercase."""
        return re.sub(r'[^\w\s]', '', text.lower())
    
    def is_book_match(self, filename: str, book_data: Dict) -> bool:
        """Check if a filename matches a book based on keywords."""
        normalized_filename = self.normalize_text(filename)
        
        # Check if multiple keywords from the book are present
        keyword_matches = 0
        for keyword in book_data['keywords']:
            if keyword.lower() in normalized_filename:
                keyword_matches += 1
                
        # Require at least 2 keyword matches for a positive identification
        return keyword_matches >= 2
    
    def search_directory(self, directory: Path) -> List[Path]:
        """Search a directory for book files."""
        found_files = []
        
        try:
            if not directory.exists() or not directory.is_dir():
                return found_files
                
            logger.info(f"Searching directory: {directory}")
            
            # Walk through directory tree
            for root, dirs, files in os.walk(directory):
                # Skip system and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                    'System', 'Library', 'Applications', '__pycache__', 'node_modules'
                }]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check if file has relevant extension
                    if file_path.suffix.lower() in self.file_extensions:
                        # Check against each book
                        for book_data in self.books_data:
                            if self.is_book_match(file, book_data):
                                logger.info(f"✅ Found potential match: {file_path}")
                                found_files.append(file_path)
                                break
                                
        except PermissionError:
            logger.warning(f"⚠️ Permission denied accessing: {directory}")
        except Exception as e:
            logger.error(f"❌ Error searching {directory}: {e}")
            
        return found_files
    
    def copy_file_safely(self, source: Path, destination: Path) -> bool:
        """Copy a file safely with error handling."""
        try:
            # Create unique filename if file already exists
            counter = 1
            original_destination = destination
            while destination.exists():
                stem = original_destination.stem
                suffix = original_destination.suffix
                destination = original_destination.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.copy2(source, destination)
            logger.info(f"✅ Copied: {source.name} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to copy {source}: {e}")
            return False
    
    def search_and_copy_books(self) -> Dict[str, List[str]]:
        """Main method to search for books and copy them."""
        logger.info("🔍 Starting book search...")
        logger.info(f"📁 Target folder: {self.target_folder}")
        
        results = {
            "found_files": [],
            "copied_files": [],
            "failed_copies": []
        }
        
        all_found_files = []
        
        # Search each directory
        for search_dir in self.search_directories:
            found_files = self.search_directory(search_dir)
            all_found_files.extend(found_files)
        
        # Remove duplicates
        unique_files = list(set(all_found_files))
        results["found_files"] = [str(f) for f in unique_files]
        
        logger.info(f"📚 Found {len(unique_files)} potential book files")
        
        # Copy found files
        for file_path in unique_files:
            destination = self.target_folder / file_path.name
            
            if self.copy_file_safely(file_path, destination):
                results["copied_files"].append(str(file_path))
            else:
                results["failed_copies"].append(str(file_path))
        
        # Generate summary report
        self.generate_report(results)
        
        return results
    
    def generate_report(self, results: Dict[str, List[str]]) -> None:
        """Generate a summary report of the search results."""
        report_path = self.target_folder / "search_report.txt"
        
        with open(report_path, 'w') as f:
            f.write("QUANTITATIVE FINANCE BOOK SEARCH REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Search completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Target folder: {self.target_folder}\n\n")
            
            f.write(f"SUMMARY:\n")
            f.write(f"- Files found: {len(results['found_files'])}\n")
            f.write(f"- Files copied: {len(results['copied_files'])}\n")
            f.write(f"- Copy failures: {len(results['failed_copies'])}\n\n")
            
            if results['found_files']:
                f.write("FOUND FILES:\n")
                f.write("-" * 20 + "\n")
                for file_path in results['found_files']:
                    f.write(f"- {file_path}\n")
                f.write("\n")
            
            if results['copied_files']:
                f.write("SUCCESSFULLY COPIED:\n")
                f.write("-" * 20 + "\n")
                for file_path in results['copied_files']:
                    f.write(f"- {file_path}\n")
                f.write("\n")
            
            if results['failed_copies']:
                f.write("FAILED COPIES:\n")
                f.write("-" * 20 + "\n")
                for file_path in results['failed_copies']:
                    f.write(f"- {file_path}\n")
                f.write("\n")
            
            f.write("SEARCHED BOOKS:\n")
            f.write("-" * 20 + "\n")
            for book in self.books_data:
                f.write(f"- {book['title']} by {book['author']}\n")
        
        logger.info(f"📄 Report generated: {report_path}")

def main():
    """Main execution function."""
    print("🔍 Quantitative Finance Book Finder")
    print("=" * 40)
    
    # Create book finder instance
    finder = BookFinder()
    
    # Ask for user confirmation
    print(f"📁 Books will be copied to: {finder.target_folder}")
    print(f"🔍 Will search {len(finder.search_directories)} directories")
    print(f"📚 Looking for {len(finder.books_data)} different books")
    
    response = input("\nProceed with search? (y/n): ").lower().strip()
    if response != 'y':
        print("❌ Search cancelled")
        return
    
    # Run the search
    try:
        results = finder.search_and_copy_books()
        
        print("\n" + "=" * 40)
        print("🎉 SEARCH COMPLETE!")
        print(f"✅ Found: {len(results['found_files'])} files")
        print(f"📋 Copied: {len(results['copied_files'])} files")
        print(f"❌ Failed: {len(results['failed_copies'])} files")
        print(f"📁 Location: {finder.target_folder}")
        
    except KeyboardInterrupt:
        print("\n❌ Search interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main() 