#!/usr/bin/env python3
"""
Test fast endpoint to verify setup
"""

test_route = '''
@router.get("/test-fast")
async def test_fast_endpoint():
    """Ultra-fast test endpoint"""
    import time
    start = time.time()
    
    # Simple response with no external calls
    return {
        "status": "success",
        "message": "Fast endpoint working",
        "response_time": round(time.time() - start, 3),
        "timestamp": datetime.utcnow().isoformat()
    }
'''

print("Add this test endpoint to dashboard.py:")
print(test_route)
print("\nThen test with:")
print("curl http://${VPS_HOST}:8003/api/dashboard/test-fast")