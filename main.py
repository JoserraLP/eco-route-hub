import flask_monitoringdashboard as dashboard

from route_consumption_estimator import create_app

import argparse

parser = argparse.ArgumentParser(
    description="EcoChassis"
)

# ./config/config_base.yaml
parser.add_argument(
    "config_dir",
    help="Directory where config is stored"
)

args = parser.parse_args()

app = create_app(args.config_dir)
dashboard.config.init_from(file='dashboard/config.cfg')
dashboard.bind(app)


if __name__ == "__main__":

    app.run(debug=True, port=5001, host='0.0.0.0')
    # python main.py

    # http://127.0.0.1:5000/routes?source=43.5231781,-5.6276553&destination=43.3828673,-5.8237067&vehicle_id=skoda
