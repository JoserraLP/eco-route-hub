from route_consumption_estimator import create_app

if __name__ == "__main__":
    app = create_app()

    app.run(debug=True, port=5001, host='0.0.0.0')
    # python main.py

    # http://127.0.0.1:5000/routes?source=43.5231781,-5.6276553&destination=43.3828673,-5.8237067&vehicle_id=skoda
