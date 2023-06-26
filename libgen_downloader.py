import requests
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from bs4 import BeautifulSoup
import pandas as pd
import os
import openai
from fuzzywuzzy import fuzz
from tqdm import tqdm
from urllib.parse import unquote
import re
import langid

openai.api_key = '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'
fuzziness_threshold = 70  # Adjust this value as needed

def process_authors(authors_list):
    """
    Function to process author names to handle different formats
    """
    processed_authors = []

    for author in authors_list:
        if ',' in author:
            # Handle the format "Surname, Name"
            split_name = author.split(',')
            author = f"{split_name[1].strip()} {split_name[0].strip()}"
        elif '.' in author and ' ' not in author:
            # Handle the format "N. Surname" - only if there are no spaces (to avoid affecting names like "J. K. Rowling")
            split_name = author.split('.')
            author = split_name[-1].strip()
        # If author's name doesn't need processing, it stays the same
        processed_authors.append(author)

    return processed_authors

def get_user_topic():
    topic = input("Please enter your topic of interest: ")
    lang, _ = langid.classify(topic)

    language_dict = {
        'en': {"name": "english", "prompt": "Generate a list of English book titles related to {} along with their authors, formatted as 'Book Title by Author Name':"},
        'es': {"name": "spanish", "prompt": "Genera una lista de títulos de libros en español relacionados con {} junto con sus autores, en formato 'Título del libro por Nombre del autor':"},
        'fr': {"name": "french", "prompt": "Générer une liste de titres de livres en français liés à {} avec leurs auteurs, formatés comme 'Titre du livre par Nom de l'auteur':"},
        'de': {"name": "german", "prompt": "Erzeugen Sie eine Liste von Buchtiteln auf Deutsch, die sich auf {} beziehen, zusammen mit ihren Autoren, formatiert als 'Buchtitel von Autorname':"},
        'it': {"name": "italian", "prompt": "Genera un elenco di titoli di libri in italiano relativi a {} insieme ai loro autori, formattati come 'Titolo del libro di Nome dell'autore':"},
        # add more languages as needed...
    }

    language_data = language_dict.get(lang, language_dict['en'])  # Default to English template if language is not in dictionary
    formatted_prompt = language_data["prompt"].format(topic)

    directory = sanitize_filename(topic)[:50]
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

    return formatted_prompt, language_data["name"], directory


def call_openai_api(prompt):
    """
    Function to call OpenAI API and return raw response
    """
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        temperature=0.5,
        max_tokens=200
    )

    return response

def process_openai_response(response, language):
    """
    Function to process the response from OpenAI API
    """
    output = response.choices[0].text.strip()

    # Assuming the output is in the format: 'Book Title, Author\nBook Title, Author\n...'
    books_and_authors = output.split('\n')

    # Dictionary for different language splitting terms
    split_dict = {"english": "by", "spanish": "por", "french": "par", "german": "von", "italian": "da", "portuguese": "por"}

    # Choose the splitting term based on the detected language
    split_term = split_dict.get(language, "by")

    # Remove leading digits and strip whitespaces
    books_and_authors = [re.sub(r'^\d+\.\s*', '', ba).split(f' {split_term} ') for ba in books_and_authors]

    # Filter out any pairs with missing book title or author name
    books_and_authors = [ba for ba in books_and_authors if len(ba) == 2 and ba[0] and ba[1]]

    # Make sure author names are clean
    for pair in books_and_authors:
        pair[1] = pair[1].strip()  # Remove leading/trailing spaces

    return books_and_authors
def create_libgen_url(book_title):
    print("Creating Libgen URL...")
    base_url = "http://libgen.rs/search.php?req="
    options = "&open=0&res=100&view=simple&phrase=1&column=title"
    
    encoded_title = book_title.replace(' ', '+')
    full_url = base_url + encoded_title + options
    print(f"Created URL: {full_url}")
    
    return full_url

def get_download_link(url, book_title, topic):
    print(f"Retrieving download link for {book_title}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(f"Error occurred when retrieving download link: {str(e)}")
        return "Error occurred"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for the 'a' tag with the string 'GET'
    download_link_tag = soup.find('a', string='GET')

    if download_link_tag:
        download_link = download_link_tag['href']
        download_status = download_file(download_link, book_title, directory)
        return download_status
    else:
        return "No download link found"
    
def sanitize_filename(filename):
    """
    Function to sanitize a string to be used as a filename by removing or replacing invalid characters
    """
    # Replace reserved characters with underscore
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_file(download_link, book_title, topic):
    print(f"Downloading file for {book_title}...")
    # Sanitize the topic and limit it to 50 characters
    directory = sanitize_filename(topic)[:50]
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

    try:
        response = requests.get(download_link, stream=True, timeout=10)
        response.raise_for_status()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(f"Error occurred when downloading file: {str(e)}")
        return "Error occurred"

    # Parse the download_link to get the filename
    raw_filename = download_link.split('/')[-1]
    filename = unquote(raw_filename)  # Replace %hh by corresponding characters

    file_path = os.path.join(directory, filename)

    # Total size in bytes.
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 #1 Kbyte

    t=tqdm(total=total_size, unit='iB', unit_scale=True)

    try:
        with open(file_path, 'wb') as file:
            for data in response.iter_content(block_size):
                t.update(len(data))
                file.write(data)
        t.close()
    except Exception as e:
        print(f"Error occurred when writing file: {str(e)}")
        return "Error occurred"

    if total_size != 0 and t.n != total_size:
        print("Error, something went wrong with the download process.")
    else:
        print(f"File '{filename}' downloaded successfully in directory: {os.path.abspath(directory)}.")
    return file_path


def scrape_libgen(book_title, author_name, fuzziness_threshold, directory, max_retries=3):
    print(f"Scraping Libgen for book titled '{book_title}' by author '{author_name}'...")
    url = create_libgen_url(book_title)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(f"Error occurred when making request: {str(e)}")
        return "Error occurred"

    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'width': '100%', 'cellspacing': '1', 'cellpadding': '1', 'rules': 'rows', 'class': 'c', 'align': 'center'})

    print("Processing search results...")
    rows = []
    for index, row in enumerate(table.find_all('tr')):
        if index == 0:  # Skip the first row
            continue
        columns = row.find_all('td')
        try:
            if columns:
                id = columns[0].get_text(strip=True)
                authors = [a.get_text(strip=True) for a in columns[1].find_all('a')]
                title = columns[2].find('a').get_text(strip=True)
                publisher = columns[3].get_text(strip=True)
                year = columns[4].get_text(strip=True)
                pages = columns[5].get_text(strip=True)
                language = columns[6].get_text(strip=True)
                size = columns[7].get_text(strip=True)
                format = columns[8].get_text(strip=True)
                link_element = columns[9].find('a')
                link = link_element['href'] if link_element is not None else 'No link'
                rows.append([id, authors, title, publisher, year, pages, language, size, format, link])
        except IndexError:
            print("A row was skipped due to insufficient columns.")
            continue

    df = pd.DataFrame(rows, columns=["ID", "Authors", "Title", "Publisher", "Year", "Pages", "Language", "Size", "Format", "Link"])

    retries = 0
    while retries < max_retries:
        print("Filtering matching results...")
        matching_rows = df[
            df['Title'].apply(lambda title: fuzz.token_sort_ratio(title, book_title) >= fuzziness_threshold) &
            df['Authors'].apply(lambda authors: any(fuzz.token_sort_ratio(process_author, author_name) >= fuzziness_threshold for process_author in process_authors(authors)))
        ]

        if matching_rows.empty:
            print(f"No matches found for book titled '{book_title}' by author '{author_name}'. Trying with a shorter title...")
            # Shorten the title, ensuring we don't split a word in half
            book_title = ' '.join(book_title.split()[:-1])
            if len(book_title.split()) < 3:
                print(f"No matches found for book titled '{book_title}' by author '{author_name}'. Moving on to the next book.")
                return
            retries += 1
        else:
            break

    # Adding the download link only for the matching rows
    print("Getting download links for matching results...")
    matching_rows['Download link'] = matching_rows['Link'].apply(lambda link: get_download_link(link, book_title, directory))

    print("Finished scraping and downloading files.")
    return matching_rows

# Retrieve the topic and language information
formatted_prompt, language, directory = get_user_topic()

# Retrieve the list of books and authors related to the topic
openai_response = call_openai_api(formatted_prompt)
book_author_pairs = process_openai_response(openai_response, language)

# Loop through the book-author pairs, scrape Libgen, and download the files
for book, author in book_author_pairs:
    scrape_libgen(book, author, fuzziness_threshold, directory)