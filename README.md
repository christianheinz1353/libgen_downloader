# libgen_downloader

Libgen Downloader
This script automatically downloads books related to a user-specified topic from Libgen. It generates a list of book titles and authors related to the topic using OpenAI's GPT-4 API, then scrapes Libgen for each book and downloads it if available.

Prerequisites
You will need to have Python 3 installed on your system. You can download Python from the official website: https://www.python.org/

You will also need an API key from OpenAI. You can get an API key by creating an account on the OpenAI website: https://www.openai.com/

Installation
Clone this repository to your local machine.

Navigate to the repository directory in your terminal.

Install the required Python packages by running the following command:

Copy code
pip install -r requirements.txt
Configuration
Before running the script, you need to set up your OpenAI API key and fuzziness threshold:

Copy the config.env.template file and rename the copy to config.env.
In the config.env file, replace 'YOUR-OPENAI-API-KEY' with your actual OpenAI API key. Optionally, you can also set the FUZZINESS_THRESHOLD (default value is 70).
Save the config.env file.
Usage
Run the script by executing the following command in your terminal:

Copy code
python libgen_downloader.py
When prompted, enter your topic of interest. The script will then generate a list of book titles and authors related to the topic, scrape Libgen for each book, and download the books if available. The downloaded files are saved in a directory named after your topic.

Note
The script uses fuzzy matching to compare the generated book titles and authors with the data scraped from Libgen. You can adjust the fuzziness threshold in the config.env file to change how strict the matching is. A higher value will result in stricter matching.
This script is for educational purposes only. Please respect the copyright laws in your country.