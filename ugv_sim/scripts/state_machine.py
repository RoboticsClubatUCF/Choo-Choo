#!/usr/bin/env python3

# ROS system imports
import rospy
import actionlib
import smach, smach_ros

# ROS messages
import std_msgs.msg as std
import nav_msgs.msg as nav
import sensor_msgs.msg as sens
import geometry_msgs.msg as geom
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

class Boot(smach.State):

    def __init__(self):
        smach.State.__init__(self, outcomes=['error', 'boot_success'])

        # TODO: define message callbacks for topics to watch and throw flags
        # what needs to be verified before we can begin?

        self._velodyne_flag = False
        self._odom_flag = False
        self._cam_flag = False
        self._imu_flag= False
        self._gps_flag = False

        # Odom subscriber
        rospy.Subscriber('/bowser2/odom', sens.Imu, callback = self.odom_callback)

        # Lidar subscriber
        rospy.Subscriber('/velodyne', sens.PointCloud2, callback = self.velodyne_callback)

        # Depth camera
        rospy.Subscriber('/bowser2/bowser2_dc/depth/camera_info', sens.CameraInfo, callback = self.cam_callback)

        # Imu Subscriber
        rospy.Subscriber('/bowser2/imu', sens.Imu, callback = self.imu_callback)

        # GPS Subscriber
        rospy.Subscriber('/bowser2/gps', sens.Imu, callback = self.gps_callback)


        # received ACK from all software modules (define list in XML/YAML format?)

    def execute(self, userdata):

        while not rospy.is_shutdown():

            if self._velodyne_flag and self._odom_flag and self._cam_flag and self._imu_flag and self._gps_flag:
                return 'boot_success'

            # what constitutes an error?

    def cam_callback(self, data):
        
        self._cam_flag = True

    def velodyne_callback(self, data):

        self._velodyne_flag = True

    def odom_callback(self, data):

        self._odom_flag = True

    def imu_callback(self, data):

        self.imu_flag = True

    def gps_callback(self, data):

        self.gps_flag = True

class Standby(smach.State):

    def __init__(self):
        smach.State.__init__(self, outcomes=['got_pose', 'rc_preempt', 'error', 'end'],
                                   output_keys=['pose_target', 'end_status', 'end_reason'] )

        self._pose_target = geom.PoseStamped()

        cmd_sub = rospy.Subscriber('/cmd_pose', geom.PoseStamped, callback = self.cmd_callback)


    def execute(self, userdata):

        while not rospy.is_shutdown():
            # check for errors
            # if err:
            #   userdata.end_reason = 'Fatal Error'
            #   userdata.end_status = 'err'
            #   return 'end'
            pass

    # Called when movement data is received
    def cmd_callback(self, data):
        return None

class Waypoint(smach.State):

    ''' pose_target contains the pose target that initiated the switch to waypoint 
        NOT guaranteed to remain the pose_target during operation '''

    def __init__(self):
        smach.State.__init__(self, outcomes=['nav_finish', 'rc_preempt', 'error'],
                                   input_keys=['pose_target'],
                                   output_keys=['status'])

        # create the client that will connect to move_base
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        
        # listen for pose updates that will change our pose_target
        pose_sub = rospy.Subscriber('/pose_updates', geom.PoseStamped, callback=self.pose_callback)
        self.pose_update = False

        # the pose target that WAYPOINT will use for navigation
        self._pose_target = None

    def execute(self, userdata):

        ''' manages the lifecycle of calls to the autonomy stack '''

        # get input pose target (pose that caused us to transition to Waypoint)
        self._pose_target = userdata.pose_target
        self._pose_update = True

        # make sure we have connection to client server before continuing
        self.client.wait_for_server()

        while not rospy.is_shutdown():

            # will need to use an actionlib connection to move_base, like below:
            # https://hotblackrobotics.github.io/en/blog/2018/01/29/action-client-py/
            # this approach may require multithreading to not block the main loop

            # for a non-blocking method: https://answers.ros.org/question/347823/action-client-wait_for_result-in-python/
            # 1. send goal with send_goal()
            # 2. query action server for state with getState()
            # 3. if we're in the appropriate state, getResult()
            # api docs: http://docs.ros.org/melodic/api/actionlib/html/classactionlib_1_1simple__action__client_1_1SimpleActionClient.html

            # if we received a pose update, create a new goal
            if self._pose_update:
                
                # goal = MoveBaseGoal()

                # goal.target_pose.header.frame_id = "map"
                # goal.target_pose.header.stamp = rospy.Time.now()
                # goal.target_pose.pose.position.x = 0.5
                # goal.target_pose.pose.orientation.w = 1.0

                # client.send_goal(goal)
                # wait = client.wait_for_result()
                # if not wait:
                #     rospy.logerr("Action server not available!")
                #     rospy.signal_shutdown("Action server not available!")
                # else:
                #     return client.get_result()

                # reset the flag
                self._pose_update = False

    def pose_callback(self, data):
        # update internal pose target
        self._pose_target = data.pose
        # set flag to true
        self._pose_update = True
    
class Manual(smach.State):

    def __init__(self):
        smach.State.__init__(self, outcomes=['rc_un_preempt', 'resume_waypoint', 'error'])

        # subscribe to RC commands
        # TODO: make/find an RC channels message
        rospy.Subscriber('/rc', std.String, callback=self.rc_callback)

        # publish motor commands for the base_controller to actuate
        self.motor_pub = rospy.Publisher('/cmd_vel', geom.Twist, queue_size=10)
    
    def execute(self, userdata):

        while not rospy.is_shutdown():
            pass

    def rc_callback(self, data):

        # convert raw RC to twist (if that's the approach we're taking)

        # publish on cmd_vel with self.motor_pub
        pass

class Warn(smach.State):

    def __init__(self):
        smach.State.__init__(self, outcomes=['reset', 'standby', 'end'],
                                   output_keys=['end_status', 'end_reason'])

    def execute(self, userdata):

        pass

class End(smach.State):

    def __init__(self):
        smach.State.__init__(self, outcomes=['end_success', 'end_err'],
                                   input_keys=['end_status', 'end_reason'])

    def execute(self, userdata):

        # kill the ROS node
        # http://wiki.ros.org/rospy/Overview/Initialization%20and%20Shutdown
        rospy.signal_shutdown(userdata.end_reason)

        if userdata.end_status == 'success':
            return 'end_success'
        elif userdata.end_status == 'err':
            return 'end_err'

def main():

    # initialize ROS node
    rospy.init_node('rover_sm', anonymous=True)

    # create state machine with outcomes
    sm = smach.StateMachine(outcomes=['success', 'err'])

    # declare userdata
    sm.userdata.pose_target = geom.PoseStamped()

    # define states within sm
    with sm:
        smach.StateMachine.add('BOOT',
            Boot(),
            transitions={'error':'WARN', 'boot_success':'STANDBY'},
            remapping={})
        smach.StateMachine.add('STANDBY',
            Standby(),
            transitions={'got_pose':'WAYPOINT', 'rc_preempt':'MANUAL', 'error':'WARN', 'end':'END'},
            remapping={'pose_target':'pose_target', 'end_status':'end_status', 'end_reason':'end_reason'})
        smach.StateMachine.add('WAYPOINT',
            Waypoint(),
            transitions={'nav_finish':'STANDBY', 'rc_preempt':'MANUAL', 'error':'WARN'},
            remapping={'pose_target':'pose_target', 'status':'waypoint_status'})
        smach.StateMachine.add('MANUAL',
            Manual(),
            transitions={'rc_un_preempt':'STANDBY', 'resume_waypoint':'WAYPOINT', 'error':'WARN'},
            remapping={})
        smach.StateMachine.add('WARN',
            Warn(),
            transitions={'reset':'BOOT', 'standby':'STANDBY', 'end':'END'},
            remapping={})
        smach.StateMachine.add('END',
            End(),
            transitions={'end_success':'success', 'end_err':'err'},
            remapping={'end_status':'end_status', 'end_reason':'end_reason'})


    # create an introspection server for debugging transitions
    introspect = smach_ros.IntrospectionServer('rover_sm_info', sm, '/SM_ROOT')
    introspect.start()

    outcome = sm.execute()

    rospy.spin()
    introspect.stop()

if __name__ == '__main__':
    main()
