import sqlite3
import os
from flask import Flask, render_template, request



def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# вспомогательная функция для создания бд
def create_db():
    db = connect_db()
    with app.open_resource('sq_db.sql', mode-'r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

def get_db():
    #соединение с бд, если оно еще не установлено
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

app.route("/")
def index():
    db = get_db()
    return render_template('index.html', menu = [])