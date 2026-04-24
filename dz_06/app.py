from flask import Flask, render_template, url_for, redirect

app = Flask(__name__)

books = [
    {"id": 0, "title": "Linux from Scratch", "about": "Книга про создание ОС из исходного кода"},
    {"id": 1, "title": "Джордж Оруэлл", "about": "Книга рассказывает о жизни в тоталитарном обществе"},
    {"id": 2, "title": "Метро 2033", "about": "Книга о выживании остатков человечества в московском метро после ядерной войны"},
]


@app.route('/')
def index():
    return render_template('index.html', books=books)


@app.route('/books/<int:id>')
def details(id):
    return render_template('items.html', book=books[id], id=books[id])


@app.route('/about')
def about():
    return redirect('https://t.me/pathoflinux')


if __name__ == '__main__':
    app.run(debug=True)
