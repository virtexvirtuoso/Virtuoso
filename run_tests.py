import unittest
import asyncio
import sys
import os

class AsyncioTestCase(unittest.TestCase):
    """Base class for async test cases."""
    def run(self, result=None):
        """Run the test case in an event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return super().run(result)
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def _callTestMethod(self, method):
        """Call the test method, handling coroutines properly."""
        if asyncio.iscoroutinefunction(method):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(method())
        return method()

class AsyncioTestRunner(unittest.TextTestRunner):
    """Custom test runner that handles async tests."""
    def run(self, test):
        """Run tests with async support."""
        # Patch test cases to handle async
        for test_case in test:
            if isinstance(test_case, unittest.TestCase):
                test_case.__class__.__bases__ = (AsyncioTestCase,) + test_case.__class__.__bases__

        return super().run(test)

def run_tests():
    """Discover and run all tests."""
    # Add the project root directory to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Discover tests recursively
    loader = unittest.TestLoader()
    suites = []
    start_dir = os.path.join(project_root, 'tests')
    
    # Ensure data_processing tests are included
    data_processing_dir = os.path.join(start_dir, 'data_processing')
    if os.path.exists(data_processing_dir):
        suite = loader.discover(data_processing_dir, pattern='test_*.py')
        suites.append(suite)
    
    # Walk through all other subdirectories
    for root, dirs, files in os.walk(start_dir):
        if root != data_processing_dir and any(f.startswith('test_') and f.endswith('.py') for f in files):
            suite = loader.discover(root, pattern='test_*.py')
            suites.append(suite)
    
    # Combine all test suites
    combined_suite = unittest.TestSuite(suites)
    
    # Create and run test suite with async support
    runner = AsyncioTestRunner(verbosity=2)
    result = runner.run(combined_suite)
    
    # Return 0 if tests passed, 1 if any failed
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    # Set up asyncio event loop for async tests
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run tests and exit with appropriate status code
    sys.exit(run_tests()) 