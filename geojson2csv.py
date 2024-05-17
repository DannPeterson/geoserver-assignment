import json
import csv

# Загрузка данных из JSON-файла
with open('centroids.json', 'r') as json_file:
    centroids = json.load(json_file)

# Запись данных в CSV-файл
with open('centroids.csv', 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    # Запись заголовков
    csv_writer.writerow(['x', 'y'])
    # Запись координат
    for centroid in centroids:
        csv_writer.writerow([centroid['x'], centroid['y']])

print("Центроиды сохранены в centroids.csv")
