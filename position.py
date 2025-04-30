from flask import Flask, jsonify
from flask_cors import CORS
import time
import math
from bosdyn.client import create_standard_sdk
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.client.frame_helpers import BODY_FRAME_NAME, ODOM_FRAME_NAME, get_a_tform_b

# Helper function to convert meters to feet
def meters_to_feet(meters):
    return meters * 3.28084

def calculate_linear_distance(x1, y1, x2, y2):
    """Calculate the linear distance in feet between two points."""
    distance_meters = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return meters_to_feet(distance_meters)


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
# Create SDK and robot instance
sdk = create_standard_sdk("GetRobotXYPositions")
robot = sdk.create_robot("xxxxxxxx")

# Authenticate with the robot (replace <USERNAME> and <PASSWORD>)
robot.authenticate("admin", "xxxxxxx")

# Create a RobotState client
state_client = robot.ensure_client(RobotStateClient.default_service_name)
    # Get the initial position as the starting reference
starting_value = None
starting_angle = None
robot_state = state_client.get_robot_state()

# Get the transformation from odometry to body frame
odom_tform_body = get_a_tform_b(robot_state.kinematic_state.transforms_snapshot, 
                                ODOM_FRAME_NAME, 
                                BODY_FRAME_NAME)

# Extract position (x, y) in meters
x_meters = odom_tform_body.position.x
y_meters = odom_tform_body.position.y



vision_tform_body = robot_state.kinematic_state.transforms_snapshot.child_to_parent_edge_map[ODOM_FRAME_NAME].parent_tform_child

# Extract quaternion (qx, qy, qz, qw) from the pose
qx = vision_tform_body.rotation.x
qy = vision_tform_body.rotation.y
qz = vision_tform_body.rotation.z
qw = vision_tform_body.rotation.w

# Convert quaternion to Euler angles (roll, pitch, yaw)
yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))

# Yaw is the angle relative to the map in radians, convert to degrees
yaw_degrees = math.degrees(yaw)

# Normalize the angle to 0° - 360°
if yaw_degrees < 0:
    yaw_degrees += 360


# Set the starting position if not already set
if starting_value is None:
    starting_value = (x_meters, y_meters)

if starting_angle is None:
    starting_angle = 90
@app.route('/get-coordinates', methods=['GET'])
def get_coordinates():
        try:
            # Get the robot state
            robot_state = state_client.get_robot_state()

            # Get the transformation from odometry to body frame
            odom_tform_body = get_a_tform_b(robot_state.kinematic_state.transforms_snapshot, 
                                            ODOM_FRAME_NAME, 
                                            BODY_FRAME_NAME)

            # Extract position (x, y) in meters
            x_meters = odom_tform_body.position.x
            y_meters = odom_tform_body.position.y
            x_feet = meters_to_feet(x_meters - starting_value[0])
            y_feet = meters_to_feet(y_meters - starting_value[1])


            vision_tform_body = robot_state.kinematic_state.transforms_snapshot.child_to_parent_edge_map[ODOM_FRAME_NAME].parent_tform_child

            # Extract quaternion (qx, qy, qz, qw) from the pose
            qx = vision_tform_body.rotation.x
            qy = vision_tform_body.rotation.y
            qz = vision_tform_body.rotation.z
            qw = vision_tform_body.rotation.w

            # Convert quaternion to Euler angles (roll, pitch, yaw)
            yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))

            # Yaw is the angle relative to the map in radians, convert to degrees
            yaw_degrees = math.degrees(yaw)

            # Normalize the angle to 0° - 360°
            if yaw_degrees < 0:
                yaw_degrees += 360
            print({"x":round(x_feet,2), "y":round(y_feet,2), "rotation": starting_angle + yaw_degrees})
            return jsonify({"x":round(x_feet,2), "y":round(y_feet,2), "rotation": starting_angle + yaw_degrees})
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    app.run(debug=True)