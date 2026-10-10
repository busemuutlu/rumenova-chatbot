from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print(">>> RUMENOVA - Mimari On Gorusme Chatbot Sunucusu Baslatiliyor <<<")
    print(">>> Chatbot Ekrani         : http://127.0.0.1:5000/")
    print(">>> Mimar & Yonetici Paneli: http://127.0.0.1:5000/dashboard")
    print(">>> Wix Widget Scripti     : http://127.0.0.1:5000/static/widget.js")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
