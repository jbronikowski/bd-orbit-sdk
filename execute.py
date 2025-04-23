from orbitsdk import OrbitAPI
client = OrbitAPI()
barq = client.robots.setRobot('BarQ')


maps = barq.missions.getSiteMaps("Map 1")

waypoint1 = maps.waypointIds[0]

barq.missions.sendRobot(waypoint1)
barq.missions.dispatchRobot()


barq.missions.sendRobotToDock()
barq.missions.dispatchRobot()