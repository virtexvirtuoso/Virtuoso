import numpy as np

def sigmoid_transform(value, sensitivity=0.12, center=50.0):
    """
    Apply sigmoid transformation to amplify signals outside the neutral range.
    
    Args:
        value: The value to transform
        sensitivity: Controls how aggressive the transformation is (lower = more aggressive)
        center: The center point considered neutral
        
    Returns:
        Transformed value in the same range as the input
    """
    # Normalize around center
    normalized = (value - center) / 50.0
    
    # Apply sigmoid with sensitivity parameter
    transformed = 1.0 / (1.0 + np.exp(-normalized / sensitivity))
    
    # Scale back to original range
    result = transformed * 100.0
    
    return result

def main():
    """Test sigmoid transformation with different sensitivity values."""
    print("\n=== Sigmoid Transformation Test ===\n")
    
    # Test values
    test_values = [30.0, 40.0, 45.0, 50.0, 55.0, 60.0, 70.0]
    sensitivities = [0.10, 0.12, 0.15, 0.20]
    
    # Print header
    print(f"{'Raw Value':<10} | {'Sens: 0.10':<10} | {'Sens: 0.12':<10} | {'Sens: 0.15':<10} | {'Sens: 0.20':<10}")
    print("-" * 60)
    
    # Test each value with different sensitivities
    for value in test_values:
        results = [sigmoid_transform(value, sens) for sens in sensitivities]
        print(f"{value:<10.1f} | {results[0]:<10.2f} | {results[1]:<10.2f} | {results[2]:<10.2f} | {results[3]:<10.2f}")
    
    print("\n=== Long/Short Ratio Example ===\n")
    
    # Long/Short ratio example
    long_values = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    print(f"{'Long %':<10} | {'Raw Score':<10} | {'Sigmoid (0.10)':<14} | {'Sigmoid (0.12)':<14} | {'Sigmoid (0.15)':<14}")
    print("-" * 75)
    
    for long_pct in long_values:
        raw_score = long_pct * 100
        transformed_scores = [sigmoid_transform(raw_score, sens) for sens in [0.10, 0.12, 0.15]]
        print(f"{long_pct:<10.2f} | {raw_score:<10.1f} | {transformed_scores[0]:<14.2f} | {transformed_scores[1]:<14.2f} | {transformed_scores[2]:<14.2f}")

if __name__ == "__main__":
    main() 