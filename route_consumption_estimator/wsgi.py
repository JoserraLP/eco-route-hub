import flask_monitoringdashboard as dashboard

from route_consumption_estimator import create_app

app = create_app()
dashboard.config.init_from(file='../cfg/dashboard.cfg')
dashboard.bind(app)

if __name__ == "__main__":
    app.run()
    # python main.py

    # http://127.0.0.1:5000/routes?source=43.5231781,-5.6276553&destination=43.3828673,-5.8237067&vehicle_id=skoda
