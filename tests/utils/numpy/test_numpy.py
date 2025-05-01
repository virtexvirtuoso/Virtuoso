import numpy as np
import json
a = np.array([1, 2, 3])
print("a:", a, "type:", type(a))
try:
    print(json.dumps({"a": a}))
    print("Serialized successfully")
except TypeError as e:
    print("Error:", e)
print("After conversion:", json.dumps({"a": a.tolist()}))
