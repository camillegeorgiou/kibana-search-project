import csv

input_csv = 'path/bbc_news.csv'
output_csv = 'path/new-bbc_news.csv'

# Read in the old bbc_news CSV file
with open(input_csv, 'r') as infile:
    reader = csv.DictReader(infile)
    data = [row for row in reader]

# Write the file in the desired format
with open(output_csv, 'w', newline='') as outfile:
    fieldnames = ['pubDate', 'title', 'guid', 'link', 'description']
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)

    writer.writeheader()

    # Write data in new format
    for row in data:
        writer.writerow({
            'pubDate': row['pubDate'],
            'title': row['title'],
            'guid': row['guid'],
            'link': row['link'],
            'description': row['description']
        })

print(f'Success. Output saved to {output_csv}')

