import numpy as np
print('NumPy version:', np.__version__)
# Check if types exist
type_names = ['np.integer', 'np.floating', 'np.generic']
for name in type_names:
    try:
        t = eval(name)
        print(f'{name} exists: {t}')
    except Exception as e:
        print(f'{name} error: {e}')

