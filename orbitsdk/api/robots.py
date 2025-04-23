import urllib
from munch import Munch, munchify, unmunchify
from .missions import Missions

class Robots(object):
    def __init__(self, session):
        super(Robots, self).__init__()
        self._session = session
        self.robotName = None
        self.robotId = None
        


    def getRobots(self):
        """
        **Return Orbit Robots**
        """

        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'getRobots'
        }

        resource = '/api/v0/robots'

        return self._session.get(metadata, resource)
        
    def getRobot(self, robotIndex: int = None, robotName: str = None):
        """
        **Return a robot**

        - robotIndex (string): Robot ID
        """

        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'getRobot'
        }
        #robotIndex = urllib.parse.quote(str(robotIndex), safe='')
        resource = '/api/v0/robots'

        robots =  self._session.get(metadata, resource)
        for robot in robots:
            if robot['robotIndex'] == robotIndex:
                self.robotName = robot['nickname']
                self.robotId = robot['robotIndex']
                return robot
            elif robot['nickname'] == robotName:
                self.robotName = robot['nickname']
                self.robotId = robot['robotIndex']
                return robot
            else:
                break
                # add in error

    def setRobot(self, robotName: str = None, robotIndex: int = None):

        robots = self.getRobots()
        for robot in robots:
            if robot['robotIndex'] == robotIndex or robot['nickname'] == robotName:
                self.robotName = robot['nickname']
                self.robotId = robot['robotIndex']
                break
            else:
                continue
        
        self.missions = Missions(self._session, self.robotId, self.robotName)
        return self


    

    def getRobotSession(self, robotName: str = None):
        """
        **Return a robot session**

        - robotName (string): Robot Name
        """
        if not robotName and self.robotName:
            robotName = self.robotName

        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'getRobotSession'
        }
        #robotIndex = urllib.parse.quote(str(robotIndex), safe='')
        resource = f'/api/v0/robot-session/{robotName}/session'

        robotSession = self._session.get(metadata, resource)
        return munchify(robotSession)
    

    def getRobotBattery(self, robotName: str = None):
        """
        **Return a robot session**

        - robotName (string): Robot Name
        """
         
        if not robotName and self.robotName:
            robotName = self.robotName
        elif robotName:
            pass
        else:
            return None
        
        robotSession = self.getRobotSession(robotName)
        return unmunchify(robotSession.batteryState)



    
    
    def isRobotReady(self):

        robotSession = self.getRobotSession()
        return robotSession.missionRunning