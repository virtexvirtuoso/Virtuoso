#!/usr/bin/env python3
"""Script to finalize SignalGenerator updates."""

def finalize_signal_generator():
    # Read the file
    with open('src/signal_generation/signal_generator.py', 'r') as f:
        content = f.read()
    
    # Fix the missing results assignment
    content = content.replace(
        '''                except Exception as e:
                    self.logger.error(f"Error generating interpretation for {component_name}: {str(e)}")
                    # Fallback to simple interpretation
                    interpretation = f"Score: {component_score:.1f} - {'Bullish' if component_score > 50 else 'Bearish'} bias"
            # Generate signals based on configured thresholds''',
        '''                except Exception as e:
                    self.logger.error(f"Error generating interpretation for {component_name}: {str(e)}")
                    # Fallback to simple interpretation
                    interpretation = f"Score: {component_score:.1f} - {'Bullish' if component_score > 50 else 'Bearish'} bias"
                
                # Create component entry with full interpretation text
                results[component_name] = {
                    'score': component_score,
                    'components': sub_components,
                    'interpretation': interpretation
                }
            
            # Generate signals based on configured thresholds'''
    )
    
    # Remove all old interpretation methods
    lines = content.split('\n')
    new_lines = []
    skip_method = False
    skip_count = 0
    
    for i, line in enumerate(lines):
        # Check if we're starting an interpretation method to remove
        if any(f'def _interpret_{comp}(' in line for comp in ['volume', 'orderbook', 'orderflow', 'price_structure', 'technical', 'sentiment']):
            skip_method = True
            skip_count = 0
            continue
        
        # Skip lines that are part of the interpretation method
        if skip_method:
            # Count indented lines to know when method ends
            if line.strip() == '' or line.startswith('    '):
                skip_count += 1
                continue
            else:
                # We've reached the end of the method
                skip_method = False
                skip_count = 0
        
        new_lines.append(line)
    
    # Write back to file
    with open('src/signal_generation/signal_generator.py', 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("Finalized SignalGenerator updates")

if __name__ == "__main__":
    finalize_signal_generator() 