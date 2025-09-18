====================================================================================================
VIRTUOSO CCXT COMPREHENSIVE VALIDATION REPORT
Tuple Unwrapping and Reliability Formatting Fixes
====================================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------
Test execution completed: 2025-09-18 15:40:43
Total duration: 64.5 seconds
Tests executed: 4
Tests passed: 0
Tests failed: 4
Success rate: 0.0%

ENVIRONMENT VALIDATION
--------------------------------------------------
Python virtual environment: ✓
Python version: Python 3.11.12
Project structure validation:
  - src/ directory: ✓
  - scripts/ directory: ✓
  - formatter.py: ✓
  - technical_indicators.py: ✓
System resources:
  - CPU cores: 8
  - Total memory: 16.0 GB
  - Available memory: 0.97 GB

PERFORMANCE BASELINE
--------------------------------------------------
Import test: ✓
Import time: 5.151 seconds

DETAILED TEST RESULTS
--------------------------------------------------
✗ FAIL ReliabilityFormatting
    Description: Reliability Formatting
    Duration: 0.81 seconds
    Error: 

✗ FAIL TupleUnwrapping
    Description: Tuple Unwrapping
    Duration: 6.60 seconds
    Error: 

✗ FAIL EdgeCases
    Description: Edge Cases
    Duration: 6.17 seconds
    Error: 

✗ FAIL Integration
    Description: Integration
    Duration: 45.73 seconds
    Error: Traceback (most recent call last):
  File "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/../scripts/test_integration_comprehensive.py", line 355, in <module>
    success = run_integration_tests()
              ^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/../scripts/test_integration_comprehensive.py", line 351, in run_integration_tests
    return runner.run_all_tests()
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/../scripts/test_integration_comprehensive.py", line 300, in run_all_tests
    with self.application_context(timeout=45):
  File "/usr/local/Cellar/python@3.11/3.11.12/Frameworks/Python.framework/Versions/3.11/lib/python3.11/contextlib.py", line 137, in __enter__
    return next(self.gen)
           ^^^^^^^^^^^^^^
  File "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/../scripts/test_integration_comprehensive.py", line 66, in application_context
    raise Exception(f"Application failed to start within {timeout} seconds")
Exception: Application failed to start within 45 seconds


REQUIREMENTS TRACEABILITY
--------------------------------------------------
REQ-1: Reliability values display as 0-100% (not 10000%)
    Test: test_reliability_formatting_comprehensive.py [✗]

REQ-2: Cache tuple values unwrap correctly without format errors
    Test: test_tuple_unwrapping_comprehensive.py [✗]

REQ-3: No 'unsupported format string' errors in application logs
    Test: test_integration_comprehensive.py [✗]

REQ-4: System handles edge cases and extreme values gracefully
    Test: test_edge_cases_comprehensive.py [✗]

REQ-5: Performance impact is minimal
    Test: All test scripts [✗]

REQ-6: No regression in existing functionality
    Test: test_integration_comprehensive.py [✗]

RISK ASSESSMENT
--------------------------------------------------
⚠ MEDIUM-HIGH RISK: Some tests failed
  - FAILED: ReliabilityFormatting
    Impact: Reliability Formatting
  - FAILED: TupleUnwrapping
    Impact: Tuple Unwrapping
  - FAILED: EdgeCases
    Impact: Edge Cases
  - FAILED: Integration
    Impact: Integration

RECOMMENDATIONS
--------------------------------------------------
⚠ INVESTIGATE: Address failed tests before deployment
  - Review failed test outputs
  - Fix identified issues
  - Re-run validation suite
  - Consider additional testing

====================================================================================================
Report generated: 2025-09-18 15:40:43
Virtuoso CCXT Trading System - Quantitative Validation Report
====================================================================================================