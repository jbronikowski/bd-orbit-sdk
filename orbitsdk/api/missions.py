import urllib
from munch import Munch, munchify, unmunchify
from ..config import *
class Missions(object):
    def __init__(self, session, robotId, robotName):
        super(Missions, self).__init__()
        self._session = session
        self.robotId = robotId
        self.robotName = robotName
        self.missionId = None
    
    def getSiteMaps(self, name = None):
        """
        **Return a robot**

        - robotIndex (string): Robot ID
        """

        metadata = {
            'tags': ['robots', 'maps'],
            'operation': 'getSiteMaps'
        }

        resource = f'/api/v0/site_maps/'
        response = self._session.get(metadata, resource)['siteMaps']
        if name:
            for siteMap in response:
                if siteMap['metadata']['displayName'] == name:
                    return munchify(siteMap)
        return munchify(response)
    
    def getRobotMissionStatus(self):
        """
        **Return a robot**

        - robotIndex (string): Robot ID
        """

        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'getRobot'
        }

        resource = f'/robot/nickname/{self.robotName}/api/v0/mission/status'

        return munchify(self._session.get(metadata, resource))
    
    
    def sendRobot(self, waypointId):
        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'sendRobot'
        }
        
        payload = dict(
                            nickname = self.robotName,
                            waypointId = waypointId
            )
        resource = f'/api/v0/graph/send-robot'
        missionDetails =  self._session.post(metadata, resource, payload)
        if 'error' in missionDetails:
            return missionDetails['error']
        self.walk = missionDetails['walk']
        self.waypointId = waypointId
        return missionDetails
    
    def sendRobotToDock(self, siteDockUUid = DEFAULT_DOCK_ID):
        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'sendRobotToDock'
        }
        
        payload = dict(
                        nickname = self.robotName,
                        siteDockUuid = siteDockUUid
        )
        resource = f'/api/v0/graph/send-robot'
        
        missionDetails =  self._session.post(metadata, resource, payload)

        self.missionId = missionDetails['walk']['id']
        self.waypointId = siteDockUUid
        self.walk = missionDetails['walk']
        return missionDetails
    
    def dispatchRobot(self, walk: str = None, robotName: str = None):
        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'dispatchRobot'
        }
        
        if not robotName and self.robotName:
            robotName = self.robotName
        
        if not walk and self.walk:
            walk = self.walk
        payload = {
                    "eventMetadata": {
                        "name": "Driver Triggered by SDK"
                    },
                    "agent": {
                        "nickname": robotName
                    },
                    "task": {
                        "dispatchTarget": {
                            "walk": walk
                        },
                        "forceAcquireEstop": True,
                        "requireDocked": False,
                        "skipInitialization": True
                    },
                    "schedule": {
                        "timeMs": "1",
                        "repeatMs": "0"
                    }
                }
        resource = f'/api/v0/calendar/mission/dispatch/{robotName}'
        
        return self._session.post(metadata, resource, payload)
    
    def getCalendarStatus(self):

        resource = '/api/v0/calendar/status'
        metadata = {
            'tags': ['robots', 'configure'],
            'operation': 'getCalendarStatus'
        }
        resource = '/api/v0/calendar/status'

        return self._session.get(metadata, resource)
    
# {
#     "eventMetadata": {
#         "name": "Driver Triggered Mission ( 1745414655646)"
#     },
#     "agent": {
#         "nickname": "BarQ"
#     },
#     "task": {
#         "dispatchTarget": {
#             "walk": {
#                 "playbackMode": {
#                     "once": {
#                         "skipDockingAfterCompletion": false
#                     }
#                 },
#                 "missionName": "Send BarQ to Dock 520",
#                 "docks": [
#                     {
#                         "dockId": 520,
#                         "dockedWaypointId": "dismal-lamb-nS6TXPmU1p0MNhgi4hFq0w==",
#                         "targetPrepPose": {
#                             "navigateTo": {
#                                 "destinationWaypointId": "gowned-fish-QqixOJxH7X1m.Ph+KdTN9w==",
#                                 "travelParams": {
#                                     "boxRegion": {
#                                         "box": {
#                                             "size": {
#                                                 "x": 0.5,
#                                                 "y": 0.25
#                                             }
#                                         }
#                                     },
#                                     "maxYaw": 0.1,
#                                     "featureQualityTolerance": "TOLERANCE_IGNORE_POOR_FEATURE_QUALITY",
#                                     "blockedPathWaitTime": {
#                                         "seconds": "5"
#                                     },
#                                     "entityBehaviorConfig": {
#                                         "entitySlowdownConfig": {
#                                             "slowdownZone": {
#                                                 "box": {
#                                                     "size": {
#                                                         "x": 3.5,
#                                                         "y": 3
#                                                     }
#                                                 },
#                                                 "frameName": "body",
#                                                 "frameNameTformBox": {
#                                                     "position": {
#                                                         "x": -0.5,
#                                                         "y": -1.5
#                                                     },
#                                                     "rotation": {
#                                                         "w": 1
#                                                     }
#                                                 }
#                                             },
#                                             "slowdownMaxLinearSpeed": 0.35,
#                                             "slowdownMaxAngularSpeed": 0.5
#                                         },
#                                         "entityObstacleConfig": {
#                                             "enableEntityObstacles": true,
#                                             "entityObstacleRadius": 0.75
#                                         }
#                                     },
#                                     "entityWaitConfig": {
#                                         "enabled": {
#                                             "value": true
#                                         },
#                                         "startWaitingAfterEntitiesAheadTime": {
#                                             "nanos": 100000000
#                                         },
#                                         "entityNearPathDistance": {},
#                                         "entityLookaheadDistance": {},
#                                         "closeSafetyZoneSize": {
#                                             "value": 1.5
#                                         }
#                                     },
#                                     "plannerMode": "PLANNER_MODE_DEFAULT"
#                                 }
#                             }
#                         }
#                     }
#                 ],
#                 "id": "4e14148a-7c36-4b4c-8b41-feffd693bbb0"
#             }
#         },
#         "forceAcquireEstop": false,
#         "requireDocked": false,
#         "skipInitialization": true
#     },
#     "schedule": {
#         "timeMs": "1",
#         "repeatMs": "0"
#     }
# }