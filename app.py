from flask import Flask, render_template, request, jsonify
import feedparser
import requests
from bs4 import BeautifulSoup
import nltk

app = Flask(__name__)

# Ensure necessary NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

RSS_FEEDS = {
    'CNN Money': 'https://money.cnn.com/services/rss/',
    'New York Times': 'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
    'Fox News': 'https://moxie.foxnews.com/google-publisher/latest.xml',
    'SEC': 'https://www.sec.gov/news/pressreleases.rss',
    'Federal Reserve': 'https://www.federalreserve.gov/feeds/press_all.xml'
}

# Fetch RSS feed
def fetch_rss_feed(url):
    return feedparser.parse(url)

# Scrape article content if no description is found
def scrape_article_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    paragraphs = soup.find_all('p')
    return ' '.join([p.text for p in paragraphs])

# Summarize text with a fallback in case of errors
def summarize_text(text):
    return text  # Return the complete text as the summary

# Categorize article based on title and content
def categorize_article(title, content):
    categories = {
        'politics': ['government', 'election', 'president', 'congress', 'senate'],
        'war': ['conflict', 'military', 'troops', 'battle', 'war'],
        'finance': ['economy', 'stock', 'market', 'investment', 'bank'],
    }
    
    text = (title + ' ' + content).lower()
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return 'other'

@app.route('/')
def index():
    return render_template('index.html', sources=RSS_FEEDS.keys())

@app.route('/fetch_news')
def fetch_news():
    source = request.args.get('source', 'all')
    category = request.args.get('category', 'all')
    
    all_articles = []
    
    feeds_to_fetch = RSS_FEEDS.items() if source == 'all' else [(source, RSS_FEEDS[source])]

    for src, url in feeds_to_fetch:
        try:
            feed = fetch_rss_feed(url)
            for entry in feed.entries[:5]:  # Limit to the first 5 entries for each feed
                link = entry.get('link', '')
                if not link:
                    continue

                content = entry.get('summary', '') or entry.get('description', '')
                if not content:
                    content = scrape_article_content(link)

                summary = summarize_text(content)  # Get full text as summary
                article_category = categorize_article(entry.title, content)

                # Get the published timestamp
                published = entry.get('published', '')  # This may vary depending on the feed structure

                # Append the article with timestamp
                article = {
                    'title': entry.get('title', 'No Title'),
                    'source': src,
                    'summary': summary,
                    'category': article_category,
                    'link': link,
                    'timestamp': published  # Add the timestamp for new article checking
                }

                if category == 'all' or category == article_category:
                    all_articles.append(article)

        except Exception as e:
            print(f"Error fetching feed from {src}: {str(e)}")
    
    return jsonify(all_articles)

@app.route('/test_feed/<source>')
def test_feed(source):
    if source in RSS_FEEDS:
        url = RSS_FEEDS[source]
        feed = fetch_rss_feed(url)
        return jsonify({
            'source': source,
            'url': url,
            'status': 'success' if feed.entries else 'no entries',
            'entry_count': len(feed.entries)
        })
    else:
        return jsonify({'error': 'Source not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
