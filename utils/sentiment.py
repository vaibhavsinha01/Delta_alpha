import requests
from datetime import datetime, timedelta
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd

#the function of this script is to tell which stocks to trade in

# stocks = ['Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.', 'Amazon.com, Inc.', 'Facebook, Inc. (Meta Platforms, Inc.)', 'Tesla, Inc.', 'Berkshire Hathaway Inc.', 'Johnson & Johnson', 'JPMorgan Chase & Co.', 'Visa Inc.', 'Procter & Gamble Co.', 'UnitedHealth Group Incorporated', 'Mastercard Incorporated', 'The Home Depot, Inc.', 'NVIDIA Corporation', 'PayPal Holdings, Inc.', 'Intel Corporation', 'Adobe Inc.', 'Netflix, Inc.', 'The Walt Disney Company', 'Cisco Systems, Inc.', 'PepsiCo, Inc.', 'Pfizer Inc.', 'Nike, Inc.', 'Coca-Cola Company', 'Exxon Mobil Corporation']
# stocks = ['Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.', 'Amazon.com']
stocks = ['Bitcoin','Ethereum','Solana','Shiba Inu','NVIDIA','MSFT','Facebook','Tesla','Dogecoin','Alphabet Inc','Amazon.com']
# stocks = ['Bitcoin', 'Ethereum', 'Binance Coin', 'Cardano', 'Solana', 'Ripple (XRP)', 'Polkadot', 'Dogecoin', 'Shiba Inu', 'Litecoin', 'Chainlink', 'Uniswap', 'Stellar', 'Polygon (MATIC)', 'Avalanche', 'Terra (LUNA)', 'VeChain', 'Tron', 'Cosmos (ATOM)', 'Tezos', 'Monero', 'Algorand', 'Aave', 'Elrond', 'IOTA', 'Filecoin']
positive_news = []
negative_news = []
normal_news = []

def get_news(api_key, company_name, num_articles=100):
    # Get the date for one day ago
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d') # checks the data for the last 10 days 

    # News API endpoint
    endpoint = "https://newsapi.org/v2/everything"

    # Set the parameters
    params = {
        'apiKey': api_key,
        'q': company_name,
        'sortBy': 'publishedAt',
        'language': 'en',
        'pageSize': num_articles,
        'from': start_date,
        'to': datetime.now().strftime('%Y-%m-%d')
    }

    try:
        # Make the request to the API
        response = requests.get(endpoint, params=params)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Extract and print the news articles
            articles = data['articles']
            all_texts = ""
            for article in articles:
                if company_name.lower() in article['title'].lower():
                    title = article['title']
                    description = article['description']
                    url = article['url']
                    
                    print(f"Title: {title}")
                    print(f"Description: {description}")
                    print(f"URL: {url}")
                    print("\n" + "="*50 + "\n")

                    # Concatenate title and description to form the text for sentiment analysis
                    all_texts += f"{title} {description} "

            return all_texts.strip()
        else:
            # Print an error message if the request was not successful
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Replace 'YOUR_API_KEY' with your actual News API key
api_key = '1f30615161cf4037b369adb5e4e0efb6'

# Call the function to get news about the specified company
def main():
    nltk.download('vader_lexicon')
    analyzer = SentimentIntensityAnalyzer()
    
    for company_name in stocks:
        text = get_news(api_key, company_name, num_articles=100)
        if text:
            sentiment = analyzer.polarity_scores(text)
            print(f"Text: {text}")
            print(f"The compound Sentiment for {company_name} is: {sentiment['compound']} the positive Sentiment is: {sentiment['pos']} the negative sentiment is {sentiment['neg']} and neutral sentiment is {sentiment['neu']}")
            if sentiment['pos'] > sentiment['neg']*1.5:
                positive_news.append(text)
                print(f'Buy {company_name}')
            elif sentiment['neg'] < sentiment['pos']*1.5:
                negative_news.append(text)
                print(f'Sell {company_name}')
            else:
                normal_news.append(text)
                print(f'Hold {company_name}')
        else:
            print(f"No relevant articles found for {company_name}")
    
    data = pd.DataFrame(positive_news)
    data.to_csv("positive_news.csv")
    data2 = pd.DataFrame(negative_news)
    data2.to_csv('negative_news.csv')
    data3 = pd.DataFrame(normal_news)
    data3.to_csv("normal.csv")

main()


# so now only trade buy for the stocks which are here