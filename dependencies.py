import pkg_resources

packages = ["streamlit", "pandas", "opencv-python-headless", "numpy", "ultralytics", "plotly"]

for p in packages:
    try:
        print(f"{p}=={pkg_resources.get_distribution(p).version}")
    except:
        print(f"{p} not installed")


import torch
print(torch.__version__)
