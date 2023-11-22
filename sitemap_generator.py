import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import concurrent.futures
from flask import Flask, request, render_template, send_file
from io import BytesIO

app = Flask(__name__)

def get_all_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(url, href)
        links.append(full_url)

    return links

def get_last_modified(url):
    response = requests.head(url)
    last_modified = response.headers.get('last-modified')
    
    return last_modified

def process_url(base_url, url):
    # Process a single URL and return a tuple of (url, last_modified)
    last_modified = get_last_modified(url)
    return url, last_modified

def generate_sitemap(base_url):
    visited = set()
    queue = [base_url]
    sitemap_links = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
        while queue:
            current_url = queue.pop(0)

            if current_url in visited:
                continue

            print(f"Scanning: {current_url}")
            links = get_all_links(current_url)
            visited.add(current_url)

            # Use concurrent processing for the links
            future_to_url = {executor.submit(process_url, base_url, link): link for link in links}
            for future in concurrent.futures.as_completed(future_to_url):
                link = future_to_url[future]
                try:
                    result = future.result()
                    # Check if the link starts with the base URL and is not already in the sitemap
                    if result[0].startswith(base_url) and result[0] not in sitemap_links:
                        sitemap_links.add(result)
                        queue.append(result[0])
                except Exception as e:
                    print(f"Error processing URL {link}: {e}")

    return sitemap_links

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        website_url = request.form['website_url']
        sitemap_links = generate_sitemap(website_url)

        # Debugging: Print the scanned URLs and last modified dates
        print("Scanned URLs and Last Modified Dates:")
        for link, last_modified in sitemap_links:
            print(f"{link} - Last Modified: {last_modified}")

        # Create an XML sitemap
        xml_sitemap = '\n'.join([f'<url><loc>{link}</loc><lastmod>{last_modified}</lastmod></url>' for link, last_modified in sitemap_links])
        xml_content = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{xml_sitemap}</urlset>'

        # Debugging: Print the generated XML content
        print("Generated XML Content:")
        print(xml_content)

        # Save the XML content to a BytesIO object
        xml_file = BytesIO()
        xml_file.write(xml_content.encode())
        xml_file.seek(0)

        # Offer the XML file for download
        return send_file(xml_file, attachment_filename='sitemap.xml', as_attachment=True)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)

