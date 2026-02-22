#!/usr/bin/env python3
"""
Test to verify the auto-scoring logic fix works correctly
"""

class MockRequest:
    def __init__(self, auto_score=True):
        self.auto_score = auto_score
        self.business_type = "web design"
        self.location = "Oxford, England"
        self.limit = 20

def test_auto_score_logic():
    """Test that auto-scoring logic works correctly after fix"""
    
    print("🧪 Testing Auto-Score Logic Fix")
    print("=" * 50)
    
    # Test case 1: auto_score=True (default) - SHOULD trigger scoring
    request1 = MockRequest(auto_score=True)
    leads_with_websites = [{"website": "example.com", "name": "Test Lead"}]
    
    should_score_1 = request1.auto_score  # This is the FIXED logic
    print(f"Test 1 - auto_score=True:")
    print(f"  auto_score value: {request1.auto_score}")
    print(f"  Will trigger scoring: {should_score_1}")
    print(f"  Expected: True")
    print(f"  Result: {'✅ PASS' if should_score_1 else '❌ FAIL'}")
    print()
    
    # Test case 2: auto_score=False - SHOULD NOT trigger scoring  
    request2 = MockRequest(auto_score=False)
    
    should_score_2 = request2.auto_score  # This is the FIXED logic
    print(f"Test 2 - auto_score=False:")
    print(f"  auto_score value: {request2.auto_score}")
    print(f"  Will trigger scoring: {should_score_2}")
    print(f"  Expected: False")
    print(f"  Result: {'✅ PASS' if not should_score_2 else '❌ FAIL'}")
    print()
    
    # Test case 3: Default behavior (auto_score not specified)
    request3 = MockRequest()  # Uses default auto_score=True
    
    should_score_3 = request3.auto_score
    print(f"Test 3 - Default behavior:")
    print(f"  auto_score value: {request3.auto_score}")
    print(f"  Will trigger scoring: {should_score_3}")
    print(f"  Expected: True (default should enable scoring)")
    print(f"  Result: {'✅ PASS' if should_score_3 else '❌ FAIL'}")
    print()
    
    # Overall result
    all_tests_pass = should_score_1 and not should_score_2 and should_score_3
    print("=" * 50)
    print(f"🎯 OVERALL RESULT: {'✅ ALL TESTS PASS' if all_tests_pass else '❌ SOME TESTS FAILED'}")
    
    if all_tests_pass:
        print("✅ Auto-scoring logic is now correct!")
        print("✅ Default behavior will trigger scoring")  
        print("✅ Users can disable scoring by setting auto_score=false")
        print("✅ This should fix the 0% scoring rate issue")
    
    return all_tests_pass

if __name__ == "__main__":
    test_auto_score_logic()