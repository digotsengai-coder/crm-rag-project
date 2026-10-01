import numpy as np
import pandas as pd

file_name = 'data/clean_final_data.csv'
df = pd.read_csv(file_name)
unique_list = df['ProductName'].unique().tolist()
print(unique_list)

"""
'USB-C Cable', 'Backpack', 'Mechanical Keyboard', 'Office Chair', 'Phone Case', 'Desk Lamp', 'HDMI Cable', 
'Power Bank', 'Wireless Mouse', 'Laptop Stand', 'Notebook', 'Webcam', 'Fitness Band', 'Tablet', 'Headphones', 
'Gaming Controller', 'Microphone', 'Smart Watch', 'Bluetooth Speaker', 'Monitor'
"""
# test
