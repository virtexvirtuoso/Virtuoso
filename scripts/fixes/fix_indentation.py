with open("src/indicators/technical_indicators.py", "r") as f:
    lines = f.readlines()

# Check for duplicate except lines
if "except Exception as e:" in lines[373] and "except Exception as e:" in lines[374]:
    # Remove one of the duplicate lines
    lines[373] = "            except Exception as e:\n"
    lines[374] = ""

with open("src/indicators/technical_indicators.py", "w") as f:
    f.writelines(lines)

print("Fixed duplicate except lines") 