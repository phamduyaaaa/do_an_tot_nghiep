import csv

csv_file = 'dataset.csv'  # thay bằng đường dẫn file của bạn

with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f)
    line_count = sum(1 for _ in reader)

print(f"Số dòng trong {csv_file}: {line_count}")

