#!/usr/bin/env python3
"""Fix the connector monitoring section indentation"""

def fix_connector_monitoring():
    with open('src/core/exchanges/bybit.py', 'r') as f:
        lines = f.readlines()
    
    # Find and fix the problematic connector monitoring section
    for i in range(1170, min(1190, len(lines))):
        if '# Monitor connection pool usage' in lines[i]:
            # This comment should be at base indent level (8 spaces)
            lines[i] = '        # Monitor connection pool usage\n'
            
            # Fix the if statement
            if i+1 < len(lines) and 'if hasattr(self, \'session\')' in lines[i+1]:
                lines[i+1] = '        if hasattr(self, \'session\') and self.session and hasattr(self.session, \'connector\'):\n'
            
            # Fix the connector assignment - should be indented under the if
            if i+2 < len(lines) and 'connector = self.session.connector' in lines[i+2]:
                lines[i+2] = '            connector = self.session.connector\n'
            
            # Fix the nested if - should be at same level as connector assignment
            if i+3 < len(lines) and 'if hasattr(connector' in lines[i+3]:
                lines[i+3] = '            if hasattr(connector, \'_acquired\'):\n'
            
            # Fix the lines inside the nested if
            if i+4 < len(lines) and 'in_use =' in lines[i+4]:
                lines[i+4] = '                in_use = len(connector._acquired) if hasattr(connector, \'_acquired\') else 0\n'
            
            if i+5 < len(lines) and 'available =' in lines[i+5]:
                lines[i+5] = '                available = len(connector._available) if hasattr(connector, \'_available\') else 0\n'
            
            if i+6 < len(lines) and 'if in_use > 20' in lines[i+6]:
                lines[i+6] = '                if in_use > 20:  # Warning threshold\n'
            
            if i+7 < len(lines) and 'self.logger.warning' in lines[i+7] and 'High connection usage' in lines[i+7]:
                lines[i+7] = '                    self.logger.warning(f"⚠️ High connection usage: {in_use} in use, {available} available")\n'
            
            print(f"Fixed connector monitoring block at lines {i+1}-{i+8}")
            break
    
    with open('src/core/exchanges/bybit.py', 'w') as f:
        f.writelines(lines)
    
    print("✅ Fixed connector monitoring indentation")

if __name__ == "__main__":
    fix_connector_monitoring()