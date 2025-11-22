from base import create_app
app = create_app()

if __name__ == '__main__':

    app.run(port=7252, debug=True, host='0.0.0.0')