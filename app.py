from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import re
from matplotlib.ticker import AutoLocator, MaxNLocator
from urllib.parse import quote

app = Flask(__name__)


def get_word_statistics(page_name):
    page_name = quote(page_name)

    wikipedia_url = f'https://ru.wikipedia.org/wiki/{page_name}'

    response = requests.get(wikipedia_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        word_statistics = {
            'total_words': 0,
            'section_statistics': {},
            'paragraph_statistics': {},
            'avg_words_per_paragraph': 0,
            'avg_words_per_section': 0,
            'min_words_paragraph': 0,
            'max_words_paragraph': 0,
            'min_words_section': 0,
            'max_words_section': 0
        }

        # Считаем общее количество слов
        article_text = ' '.join([p.text for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        words = re.findall(r'\b\w+\b', article_text)
        word_statistics['total_words'] = len(words)

        # Считаем количество слов в заголовках разделов
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            heading_text = heading.get_text()
            heading_words = re.findall(r'\b\w+\b', heading_text)
            word_statistics['section_statistics'][heading_text] = len(heading_words)

        section_word_lengths = [len(re.findall(r'\b\w+\b', heading_text)) for heading_text in word_statistics['section_statistics'].keys()]
        if section_word_lengths:
            word_statistics['min_words_section'] = min(section_word_lengths)
            word_statistics['max_words_section'] = max(section_word_lengths)
        else:
            word_statistics['min_words_section'] = 0
            word_statistics['max_words_section'] = 0

        # Считаем количество слов в абзацах
        paragraphs = soup.find_all('p')
        for i, paragraph in enumerate(paragraphs):
            paragraph_text = paragraph.get_text()
            paragraph_words = re.findall(r'\b\w+\b', paragraph_text)
            word_statistics['paragraph_statistics'][f'{i + 1}'] = len(paragraph_words)

        # Находим минимальное и максимальное количество слов в абзацах
        min_words_paragraph = min(word_statistics['paragraph_statistics'].values()) if word_statistics['paragraph_statistics'] else 0
        max_words_paragraph = max(word_statistics['paragraph_statistics'].values()) if word_statistics['paragraph_statistics'] else 0

        # Добавляем в общую статистику
        word_statistics['min_words_paragraph'] = min_words_paragraph
        word_statistics['max_words_paragraph'] = max_words_paragraph
        return word_statistics
    else:
        return None


def plot_bar_chart(data, xlabel, ylabel, title, round_values=True):
    plt.figure(figsize=(9, 6))
    plt.bar(data.keys(), data.values(), width=0.9)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=45, ha='right')

    if data:
        plt.yticks(range(0, max(data.values()) + 1))

    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.gca().yaxis.set_minor_locator(AutoLocator())

    if round_values:
        data = {key: round(value) for key, value in data.items()}

    plt.tight_layout()

    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)
    encoded_image = base64.b64encode(image_stream.read()).decode('utf-8')

    plt.tight_layout()
    plt.close()

    return f"data:image/png;base64,{encoded_image}", data


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/results', methods=['POST'])
def results():
    if 'page_name' in request.form:
        page_name = request.form['page_name']
        word_statistics = get_word_statistics(page_name)

        if word_statistics is not None:
            section_chart, section_data = plot_bar_chart(word_statistics['section_statistics'], 'Разделы', 'Кол-во слов', 'Количество слов в разделах', round_values=True)
            paragraph_chart = plot_bar_chart(word_statistics['paragraph_statistics'], 'Абзацы', 'Кол-во слов','Количество слов в абзацах', round_values=True)[0]

            return render_template('results.html',
                                   page_name=page_name,
                                   word_statistics=word_statistics,
                                   section_chart=section_chart,
                                   paragraph_chart=paragraph_chart,
                                   section_data=section_data)
        else:
            error_message = "Error fetching data from Wikipedia"
            return render_template('results.html', page_name=page_name, error_message=error_message)
    else:
        return "Error: Page name not provided"


@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
