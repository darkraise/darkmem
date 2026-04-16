"""One-off emitter for shared-base batch-184 — robotics and autonomous systems (ROS, DDS, SLAM, Nav2, MoveIt, PX4, sensor fusion).

Writes 50 rows to data/v2/shared/batch_184.tmp.jsonl with ids shared-09151..09200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_184.tmp.jsonl"
ID_OFFSET = 9150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Migrated the warehouse fleet stack from ROS 1 noetic to ROS 2 humble; end-of-life on noetic and the DDS-based middleware drove the port after the Python 2 transitional pain finally stopped hurting.", "decision", "technical", False,
     [("ROS 1", "framework"), ("noetic", "platform"), ("ROS 2", "framework"), ("humble", "platform"), ("DDS", "protocol"), ("Python 2", "language")],
     [("ROS 2", "ROS 1", "REPLACES"), ("ROS 2", "DDS", "USES")],
     "which middleware motivated moving the warehouse fleet from ROS 1 noetic to ROS 2 humble",
     "ros1 noetic ros2 humble dds migration warehouse fleet port"),
    # --- 2 --- architecture
    ("The robot bring-up uses CycloneDDS as the rmw implementation for multicast stability on our switch fabric; Fast DDS discovery kept flapping under the VLAN trunk we run between cells.", "architecture", "technical", False,
     [("CycloneDDS", "library"), ("rmw", "api"), ("Fast DDS", "library"), ("VLAN", "protocol")],
     [("CycloneDDS", "Fast DDS", "REPLACES"), ("CycloneDDS", "rmw", "IMPLEMENTS")],
     "which DDS vendor did the fleet pin as the rmw implementation and why not the default",
     "cyclonedds fast dds rmw multicast vlan trunk discovery switch"),
    # --- 3 --- milestone
    ("Shipped the first end-to-end Nav2 stack running under ROS 2 jazzy on the new mobile base; the smac_planner hybrid A* picked up the Ackermann constraints cleanly on the first demo run.", "milestone", "technical", False,
     [("Nav2", "framework"), ("ROS 2", "framework"), ("jazzy", "platform"), ("smac_planner", "library"), ("hybrid A*", "algorithm"), ("Ackermann", "concept")],
     [("Nav2", "ROS 2", "DEPLOYED_ON"), ("smac_planner", "hybrid A*", "IMPLEMENTS")],
     "which Nav2 planner handled the Ackermann constraints on the first jazzy-based mobile base demo",
     "nav2 jazzy smac planner hybrid astar ackermann mobile base demo"),
    # --- 4 --- reference
    ("Cartographer's paper formalised the branch-and-bound loop-closure search on submaps; we lean on the same algorithm sketch when tuning the scan-matching window for our wheeled platform.", "reference", "technical", False,
     [("Cartographer", "publication"), ("branch-and-bound", "algorithm"), ("loop-closure", "concept"), ("scan-matching", "method")],
     [("Cartographer", "branch-and-bound", "USES"), ("loop-closure", "scan-matching", "DEPENDS_ON")],
     "which search algorithm does Cartographer formalise for loop-closure over submaps",
     "cartographer paper branch bound loop closure submap scan match"),
    # --- 5 --- fact
    ("rclpy callbacks run on a MultiThreadedExecutor with a ReentrantCallbackGroup so the navigation action client doesn't deadlock against the pose-subscriber callback during a goal cancel.", "fact", "technical", False,
     [("rclpy", "library"), ("MultiThreadedExecutor", "api"), ("ReentrantCallbackGroup", "api")],
     [("rclpy", "MultiThreadedExecutor", "USES"), ("ReentrantCallbackGroup", "MultiThreadedExecutor", "CONFIGURES")],
     "which rclpy executor and callback-group combo avoids the navigation goal-cancel deadlock",
     "rclpy multithreaded executor reentrant callback group navigation cancel"),
    # --- 6 --- problem
    ("tf2 lookup threw extrapolation-into-the-future errors on the arm controller because the IMU driver was publishing timestamps from the sensor clock without syncing to the ROS clock.", "problem", "technical", False,
     [("tf2", "library"), ("IMU", "infrastructure"), ("ROS clock", "concept")],
     [("IMU", "tf2", "CAUSES"), ("IMU", "ROS clock", "DEPENDS_ON")],
     "which clock mismatch produced tf2 extrapolation errors on the arm controller",
     "tf2 extrapolation future imu timestamp ros clock sync arm"),
    # --- 7 --- architecture
    ("URDF describes the wheeled chassis for rviz and MoveIt while SDF handles the same robot inside Gazebo; a shared xacro layer fans out to both so inertial tweaks stay in one place.", "architecture", "technical", False,
     [("URDF", "file"), ("rviz", "tool"), ("MoveIt", "framework"), ("SDF", "file"), ("Gazebo", "platform"), ("xacro", "tool")],
     [("URDF", "MoveIt", "APPLIES_TO"), ("SDF", "Gazebo", "APPLIES_TO"), ("xacro", "URDF", "PRODUCES")],
     "how does the bring-up share one xacro source between URDF for MoveIt and SDF for Gazebo",
     "urdf sdf xacro moveit gazebo shared chassis inertial tweak"),
    # --- 8 --- decision
    ("Picked MoveIt 2 over a from-scratch OMPL integration for the 6-DoF arm; the Servo component and the pilz industrial planner covered cartesian jog and trapezoidal profiles out of the box.", "decision", "technical", False,
     [("MoveIt 2", "framework"), ("OMPL", "library"), ("Servo", "library"), ("pilz", "library")],
     [("MoveIt 2", "OMPL", "USES"), ("MoveIt 2", "Servo", "HAS_PART"), ("MoveIt 2", "pilz", "HAS_PART")],
     "which motion-planning stack beat a custom OMPL build for the 6-DoF arm and what did it bundle",
     "moveit2 ompl servo pilz industrial 6dof arm cartesian jog trapezoidal"),
    # --- 9 --- reference
    ("LIO-SAM fuses a tightly-coupled IMU pre-integration factor with LiDAR odometry in a factor graph; our indoor stack borrows the same graph topology for the Velodyne VLP-16 build.", "reference", "technical", False,
     [("LIO-SAM", "publication"), ("IMU pre-integration", "method"), ("LiDAR odometry", "method"), ("factor graph", "concept"), ("Velodyne VLP-16", "infrastructure")],
     [("LIO-SAM", "factor graph", "USES"), ("LIO-SAM", "IMU pre-integration", "USES"), ("LIO-SAM", "Velodyne VLP-16", "APPLIES_TO")],
     "which factor-graph structure does LIO-SAM use to fuse IMU pre-integration with LiDAR odometry",
     "liosam imu preintegration lidar odometry factor graph velodyne vlp16"),
    # --- 10 --- architecture
    ("The drone autopilot pairs PX4 on the flight controller with a companion computer running ROS 2 over the micro-XRCE-DDS bridge; MAVLink survives only for QGroundControl telemetry.", "architecture", "technical", False,
     [("PX4", "framework"), ("ROS 2", "framework"), ("micro-XRCE-DDS", "protocol"), ("MAVLink", "protocol"), ("QGroundControl", "tool")],
     [("PX4", "ROS 2", "COMMUNICATES_WITH"), ("PX4", "micro-XRCE-DDS", "USES"), ("MAVLink", "QGroundControl", "APPLIES_TO")],
     "how does the PX4 autopilot talk to a ROS 2 companion while keeping MAVLink only for QGroundControl",
     "px4 ros2 micro xrce dds bridge mavlink qgroundcontrol companion"),
    # --- 11 --- noise
    ("The lab cat knocked the cable tray off the shelf during lunch and we had to re-zip eighty jumper wires one by one.", "fact", "noise", True, [], [], None, None),
    # --- 12 --- decision
    ("Chose Cartographer over GMapping for the warehouse SLAM run; the 2D submap approach handles the long aisles without the particle filter degeneracy we kept seeing under GMapping.", "decision", "technical", False,
     [("Cartographer", "library"), ("GMapping", "library"), ("submap", "concept"), ("particle filter", "algorithm")],
     [("Cartographer", "GMapping", "REPLACES"), ("GMapping", "particle filter", "USES")],
     "which SLAM package replaced GMapping for warehouse aisles and what failure mode drove the switch",
     "cartographer gmapping warehouse aisle particle filter degeneracy submap"),
    # --- 13 --- fact
    ("robot_localization runs a UKF fusing wheel-odometry, the Xsens IMU, and GPS on the outdoor rover; the EKF variant undershot heading under rapid yaw during the field trial.", "fact", "technical", False,
     [("robot_localization", "library"), ("UKF", "algorithm"), ("EKF", "algorithm"), ("Xsens IMU", "infrastructure"), ("GPS", "infrastructure")],
     [("robot_localization", "UKF", "USES"), ("UKF", "EKF", "REPLACES")],
     "which filter did robot_localization adopt for the outdoor rover after EKF heading issues",
     "robot localization ukf ekf xsens imu gps yaw outdoor rover"),
    # --- 14 --- architecture
    ("The perception pipeline fuses the ZED 2i stereo depth stream with Velodyne point clouds through a ros2 sensor_msgs/PointCloud2 merge node; the camera handles close range, LiDAR covers long range.", "architecture", "technical", False,
     [("ZED 2i", "infrastructure"), ("Velodyne", "infrastructure"), ("sensor_msgs/PointCloud2", "api"), ("ros2", "framework")],
     [("ZED 2i", "Velodyne", "COMMUNICATES_WITH"), ("sensor_msgs/PointCloud2", "ros2", "IMPLEMENTS")],
     "how does the perception stack combine ZED 2i stereo with Velodyne LiDAR across ranges",
     "zed 2i velodyne pointcloud2 sensor fusion stereo lidar perception"),
    # --- 15 --- decision
    ("Migrated from Gazebo classic to Ignition Fortress after the OGRE depth-buffer allocation kept failing above eight spawned lidars; Fortress's new rendering plugin handled the scene without the crash.", "decision", "technical", False,
     [("Gazebo classic", "platform"), ("Ignition Fortress", "platform"), ("OGRE", "library")],
     [("Ignition Fortress", "Gazebo classic", "REPLACES"), ("Gazebo classic", "OGRE", "USES")],
     "which simulator replaced Gazebo classic after OGRE depth-buffer failures at eight-plus lidars",
     "ignition fortress gazebo ogre depth buffer lidar rendering plugin"),
    # --- 16 --- decision
    ("Selected ORB-SLAM3 over a visual-only LOAM port for the indoor drone; multi-map atlas and IMU-initialised scale recovery made it the obvious pick for re-entry into mapped corridors.", "decision", "technical", False,
     [("ORB-SLAM3", "library"), ("LOAM", "algorithm"), ("atlas", "concept")],
     [("ORB-SLAM3", "LOAM", "PREFERS"), ("ORB-SLAM3", "atlas", "HAS_PART")],
     "which visual-inertial SLAM package beat a LOAM port for the indoor drone and what feature sealed it",
     "orbslam3 loam indoor drone atlas multi map imu scale recovery"),
    # --- 17 --- milestone
    ("Landed the migration to Nav2's behavior-tree composer over BT.CPP this sprint; Recovery behaviors ship as XML now and the old hand-rolled planner state machine is finally out of the repo.", "milestone", "technical", False,
     [("Nav2", "framework"), ("BT.CPP", "library"), ("behavior-tree", "pattern"), ("XML", "technology")],
     [("Nav2", "BT.CPP", "USES"), ("behavior-tree", "XML", "CONFIGURES")],
     "which Nav2 migration shipped this sprint and what replaced the hand-rolled planner state machine",
     "nav2 behavior tree btcpp xml recovery migration sprint state machine"),
    # --- 18 --- milestone
    ("First indoor autonomous lap closed on the test track with the Intel RealSense D455 alone as the depth source; the LiDAR harness was left on the bench to confirm vision-only fallback works.", "milestone", "technical", False,
     [("Intel RealSense D455", "infrastructure"), ("LiDAR", "infrastructure")],
     [("Intel RealSense D455", "LiDAR", "REPLACES")],
     "which depth sensor completed the first autonomous lap without LiDAR as a fallback check",
     "realsense d455 depth sensor lidar vision only indoor autonomous lap"),
    # --- 19 --- fact
    ("ros2_control's hardware_interface reads joint states at 500 Hz from the EtherCAT bus; the real-time kernel patch on the industrial PC keeps the update loop jitter under 200 microseconds.", "fact", "technical", False,
     [("ros2_control", "library"), ("hardware_interface", "api"), ("EtherCAT", "protocol"), ("real-time kernel", "platform")],
     [("ros2_control", "EtherCAT", "COMMUNICATES_WITH"), ("hardware_interface", "ros2_control", "HAS_PART")],
     "at what rate does ros2_control poll joint states over EtherCAT and what keeps jitter low",
     "ros2 control hardware interface ethercat 500hz real time kernel jitter"),
    # --- 20 --- decision
    ("Switched from ArduPilot to PX4 for the survey quadcopter; the uORB message bus and the library-style architecture slotted into our ROS 2 offboard control cleaner than ArduPilot's monolithic loop.", "decision", "technical", False,
     [("ArduPilot", "framework"), ("PX4", "framework"), ("uORB", "protocol")],
     [("PX4", "ArduPilot", "REPLACES"), ("PX4", "uORB", "USES")],
     "which autopilot replaced ArduPilot on the survey quad and what architectural property won",
     "ardupilot px4 uorb quadcopter survey offboard monolithic library"),
    # --- 21 --- reference
    ("The RRT* paper proved asymptotic optimality by rewiring the search tree as new samples arrive; Nav2's smac_planner_lattice borrows the rewire step in its state-lattice variant.", "reference", "technical", False,
     [("RRT*", "algorithm"), ("smac_planner_lattice", "library"), ("Nav2", "framework"), ("state-lattice", "concept")],
     [("smac_planner_lattice", "RRT*", "BUILDS_ON"), ("smac_planner_lattice", "Nav2", "HAS_PART")],
     "which asymptotic-optimality proof does the Nav2 state-lattice planner borrow from",
     "rrt star asymptotic optimal rewire nav2 state lattice smac planner"),
    # --- 22 --- fact
    ("The DRV8833 motor driver on the educational rover runs behind a 470 microfarad bulk capacitor on the VM rail with firmware-side current limiting; this combination keeps the PWM stage stable under stall.", "fact", "technical", False,
     [("DRV8833", "infrastructure"), ("PWM", "concept"), ("firmware", "concept")],
     [("DRV8833", "PWM", "USES"), ("firmware", "DRV8833", "CONFIGURES")],
     "which hardware and firmware combination keeps the DRV8833 PWM stage stable under stall",
     "drv8833 motor driver capacitor vm rail firmware current limit pwm"),
    # --- 23 --- milestone
    ("The agricultural bot finally closed its first full crop-row autonomy run; an EKF slam backend and a parallel particle filter tracking ambiguous row-crossings both published cleanly to the fused map topic.", "milestone", "technical", False,
     [("EKF", "algorithm"), ("particle filter", "algorithm"), ("fused map", "concept")],
     [("EKF", "fused map", "PRODUCES"), ("particle filter", "fused map", "PRODUCES")],
     "which first autonomy run did the agricultural bot close and which two filters fed the fused map",
     "agricultural bot first autonomy ekf particle filter fused map row"),
    # --- 24 --- fact
    ("rclcpp composition loads the lidar driver and the laser_filters node into a single process; the zero-copy intra-process comms saved 4 ms per scan compared with the multi-process bring-up.", "fact", "technical", False,
     [("rclcpp", "library"), ("laser_filters", "library"), ("intra-process", "concept"), ("lidar driver", "service")],
     [("rclcpp", "intra-process", "USES"), ("rclcpp", "laser_filters", "HAS_PART")],
     "which rclcpp feature delivered the 4 ms per-scan saving by co-locating the lidar driver",
     "rclcpp composition intra process zero copy lidar laser filters scan"),
    # --- 25 --- decision
    ("Went with Isaac Sim for the perception training dataset generation; the PhysX-backed synthetic LiDAR and the domain randomisation bundled with Omniverse beat the Gazebo-based pipeline we had.", "decision", "technical", False,
     [("Isaac Sim", "platform"), ("PhysX", "library"), ("Omniverse", "platform"), ("Gazebo", "platform"), ("domain randomisation", "method")],
     [("Isaac Sim", "Gazebo", "REPLACES"), ("Isaac Sim", "Omniverse", "DEPLOYED_ON"), ("Isaac Sim", "PhysX", "USES")],
     "which simulator replaced Gazebo for synthetic perception data and what bundled feature tipped it",
     "isaac sim gazebo physx omniverse domain randomisation synthetic lidar"),
    # --- 26 --- architecture
    ("The humanoid torso runs a whole-body MPC at 200 Hz feeding joint torque commands to rclcpp; the trajectory tracking layer sits above and only sees end-effector poses, keeping the controller stack layered.", "architecture", "technical", False,
     [("whole-body MPC", "algorithm"), ("rclcpp", "library"), ("trajectory tracking", "concept"), ("end-effector", "concept")],
     [("whole-body MPC", "rclcpp", "COMMUNICATES_WITH"), ("trajectory tracking", "whole-body MPC", "BUILDS_ON")],
     "how is the humanoid controller stack layered between MPC torque commands and trajectory tracking",
     "whole body mpc 200hz rclcpp trajectory tracking torque end effector"),
    # --- 27 --- milestone
    ("First closed-loop integration of Nav2 with MoveIt 2 landed this week; the mobile manipulator now picks a tote off a conveyor while the base repositions to extend reach during the grasp.", "milestone", "technical", False,
     [("Nav2", "framework"), ("MoveIt 2", "framework"), ("mobile manipulator", "concept")],
     [("Nav2", "MoveIt 2", "COMMUNICATES_WITH"), ("MoveIt 2", "mobile manipulator", "APPLIES_TO")],
     "which two stacks integrated to let the mobile manipulator pick while repositioning",
     "nav2 moveit2 mobile manipulator tote conveyor grasp reposition"),
    # --- 28 --- preference
    ("Prefer Fast DDS over CycloneDDS on the air-gapped inspection robot; the SHM transport and the XML participant tuning cut end-to-end image latency by a third on the 10 Gb backplane.", "preference", "technical", False,
     [("Fast DDS", "library"), ("CycloneDDS", "library"), ("SHM transport", "protocol")],
     [("Fast DDS", "CycloneDDS", "PREFERS"), ("Fast DDS", "SHM transport", "USES")],
     "which DDS won on the air-gapped inspection robot and what feature delivered the latency cut",
     "fast dds cyclonedds shm transport inspection air gap image latency"),
    # --- 29 --- decision
    ("Swapped the global planner from Dijkstra to A* with a Euclidean heuristic on the 60-meter storefront 2D costmap; plan time dropped from 1.4 s to 90 ms and the switch stuck for every store over 40 meters.", "decision", "technical", False,
     [("Dijkstra", "algorithm"), ("A*", "algorithm"), ("2D costmap", "concept"), ("Euclidean heuristic", "method")],
     [("A*", "Dijkstra", "REPLACES"), ("A*", "Euclidean heuristic", "USES")],
     "which planner replaced Dijkstra on the 60-meter storefront and which heuristic cut plan time",
     "dijkstra astar 2d costmap storefront euclidean heuristic plan swap"),
    # --- 30 --- architecture
    ("Our SLAM-on-edge architecture runs LIO-SAM on the Jetson Orin NX, Cartographer as the 2D fallback on the industrial PC, and the raw LiDAR feed is mirrored to a bag recorder for offline replay.", "architecture", "technical", False,
     [("LIO-SAM", "library"), ("Jetson Orin NX", "infrastructure"), ("Cartographer", "library"), ("industrial PC", "infrastructure"), ("bag recorder", "tool")],
     [("LIO-SAM", "Jetson Orin NX", "DEPLOYED_ON"), ("Cartographer", "industrial PC", "DEPLOYED_ON")],
     "how is the edge SLAM stack partitioned between the Jetson, the industrial PC, and the bag replay",
     "liosam jetson orin cartographer industrial pc bag recorder slam edge"),
    # --- 31 --- reference
    ("Thrun's Probabilistic Robotics chapter on particle filters sets out the Monte Carlo localisation algorithm; amcl in Nav2 is the canonical ROS translation of the same formulation.", "reference", "technical", False,
     [("Probabilistic Robotics", "publication"), ("Monte Carlo localisation", "algorithm"), ("amcl", "library"), ("Nav2", "framework")],
     [("amcl", "Monte Carlo localisation", "IMPLEMENTS"), ("amcl", "Nav2", "HAS_PART")],
     "which canonical publication describes the particle-filter algorithm that amcl implements",
     "probabilistic robotics particle filter monte carlo localisation amcl nav2"),
    # --- 32 --- decision
    ("Adopted Cyclone DDS Security for the multi-robot fleet; the signed discovery and the access-control permissions file shut down the rogue-node-publishes-cmd_vel exploit path entirely.", "decision", "technical", False,
     [("Cyclone DDS Security", "library"), ("signed discovery", "concept"), ("access-control", "concept"), ("cmd_vel", "api")],
     [("Cyclone DDS Security", "cmd_vel", "APPLIES_TO"), ("signed discovery", "Cyclone DDS Security", "HAS_PART")],
     "which security layer shut down the rogue cmd_vel publisher path across the fleet",
     "cyclone dds security signed discovery access control cmd_vel fleet"),
    # --- 33 --- fact
    ("The ZED 2i runs its neural depth mode on the Orin's DLA while the SDK publishes odometry at 60 Hz; the left-lens rectified image also feeds the ORB-SLAM3 keyframe thread.", "fact", "technical", False,
     [("ZED 2i", "infrastructure"), ("Orin", "infrastructure"), ("DLA", "infrastructure"), ("ORB-SLAM3", "library")],
     [("ZED 2i", "Orin", "DEPLOYED_ON"), ("ZED 2i", "ORB-SLAM3", "COMMUNICATES_WITH"), ("DLA", "Orin", "HAS_PART")],
     "how is the ZED 2i wired between the Orin DLA, its own odometry topic, and ORB-SLAM3",
     "zed 2i orin dla neural depth odometry orbslam3 keyframe rectified"),
    # --- 34 --- preference
    ("I prefer bringing the Velodyne VLP-16 driver, the Xsens IMU driver, and the RealSense D455 node up as sibling ROS 2 lifecycle nodes under one orchestrator; unmanaged nodes always bite on restart.", "preference", "technical", False,
     [("Velodyne VLP-16", "infrastructure"), ("Xsens IMU", "infrastructure"), ("RealSense D455", "infrastructure"), ("lifecycle nodes", "pattern"), ("orchestrator", "service")],
     [("orchestrator", "lifecycle nodes", "CONFIGURES"), ("Velodyne VLP-16", "lifecycle nodes", "IMPLEMENTS")],
     "why do you prefer lifecycle nodes plus an orchestrator over unmanaged bring-up for the sensor trio",
     "velodyne vlp16 xsens realsense d455 lifecycle node orchestrator prefer"),
    # --- 35 --- problem
    ("MAVLink heartbeat timeouts tripped the failsafe on the PX4 quad during long-range flights; raising the SERIAL_UART6_BAUD to 921600 and pinning the companion link to the RFD900x radio cleared it.", "problem", "technical", False,
     [("MAVLink", "protocol"), ("PX4", "framework"), ("SERIAL_UART6_BAUD", "config"), ("RFD900x", "infrastructure")],
     [("MAVLink", "PX4", "CAUSES"), ("SERIAL_UART6_BAUD", "MAVLink", "FIXES"), ("RFD900x", "MAVLink", "SUPPORTS")],
     "which radio and baud-rate change fixed MAVLink heartbeat timeouts on the PX4 quad",
     "mavlink heartbeat timeout px4 failsafe serial baud rfd900x radio"),
    # --- 36 --- decision
    ("Dropped Fast DDS for the tele-op link because the default multicast discovery hits restrictive corporate networks; switched the tele-op to Zenoh via the rmw_zenoh bridge and the pub/sub reconvened.", "decision", "technical", False,
     [("Fast DDS", "library"), ("Zenoh", "protocol"), ("rmw_zenoh", "library"), ("tele-op", "concept")],
     [("Zenoh", "Fast DDS", "REPLACES"), ("rmw_zenoh", "Zenoh", "IMPLEMENTS"), ("Zenoh", "tele-op", "APPLIES_TO")],
     "which transport replaced Fast DDS for tele-op on restrictive corporate networks",
     "fast dds zenoh rmw zenoh tele op multicast discovery corporate"),
    # --- 37 --- reference
    ("The original A* paper introduces the admissible-heuristic guarantee that makes shortest-path search tractable; our global planner leans on consistent octile distance so the optimality proof still holds.", "reference", "technical", False,
     [("A*", "algorithm"), ("admissible-heuristic", "concept"), ("octile distance", "method")],
     [("A*", "admissible-heuristic", "USES"), ("octile distance", "admissible-heuristic", "IS_A")],
     "which heuristic property from the original A* paper does the planner preserve with octile distance",
     "astar admissible heuristic optimality octile distance global planner"),
    # --- 38 --- preference
    ("I default to rclpy for prototyping and rclcpp for anything that has to hit real-time guarantees; Python's GIL keeps biting me on tight control loops even with the MultiThreadedExecutor workaround.", "preference", "technical", False,
     [("rclpy", "library"), ("rclcpp", "library"), ("GIL", "concept"), ("MultiThreadedExecutor", "api")],
     [("rclcpp", "rclpy", "PREFERS"), ("GIL", "rclpy", "CAUSES")],
     "which ROS 2 client library do you default to for real-time loops versus prototyping, and why",
     "rclpy rclcpp gil real time prototype python executor preference"),
    # --- 39 --- architecture
    ("The outdoor stack uses a GNSS-aided EKF for the global pose and a LiDAR-inertial UKF for the local estimate; a fusion node reconciles them through a simple covariance-weighted blend each tick.", "architecture", "technical", False,
     [("GNSS", "infrastructure"), ("EKF", "algorithm"), ("UKF", "algorithm"), ("fusion node", "service"), ("covariance-weighted blend", "method")],
     [("fusion node", "EKF", "COMMUNICATES_WITH"), ("fusion node", "UKF", "COMMUNICATES_WITH"), ("fusion node", "covariance-weighted blend", "USES")],
     "how are the global GNSS-aided EKF and the local LiDAR-inertial UKF reconciled per tick",
     "gnss ekf lidar inertial ukf fusion covariance blend outdoor pose"),
    # --- 40 --- milestone
    ("Completed the transition off ROS 1 melodic last Friday; the last bridged node finally died after the final perception package hit ROS 2 iron and the ros1_bridge container got decommissioned.", "milestone", "technical", False,
     [("ROS 1", "framework"), ("melodic", "platform"), ("ROS 2", "framework"), ("iron", "platform"), ("ros1_bridge", "service")],
     [("ROS 2", "ROS 1", "REPLACES"), ("ros1_bridge", "ROS 1", "COMMUNICATES_WITH"), ("iron", "ROS 2", "IS_A")],
     "which ROS version transition did we close and what bridge container finally went away",
     "ros1 melodic ros2 iron bridge transition perception decommission"),
    # --- 41 --- decision
    ("Picked Cartographer over Hector SLAM for the rescue-bot 2D map; Hector's lack of loop closure kept producing doubled walls in the long corridor the test arena insists on including.", "decision", "technical", False,
     [("Cartographer", "library"), ("Hector SLAM", "library"), ("loop closure", "concept")],
     [("Cartographer", "Hector SLAM", "REPLACES"), ("Hector SLAM", "loop closure", "CONTRADICTS")],
     "which 2D SLAM replaced Hector for the rescue-bot arena and which missing feature drove it",
     "cartographer hector slam loop closure rescue bot corridor wall"),
    # --- 42 --- fact
    ("MoveIt 2 Servo streams TwistStamped commands at 250 Hz into the joint controller; the collision check runs on a separate thread and kills the servo if any monitored pair falls below the margin.", "fact", "technical", False,
     [("MoveIt 2", "framework"), ("Servo", "library"), ("TwistStamped", "api"), ("collision check", "method")],
     [("Servo", "TwistStamped", "PRODUCES"), ("collision check", "Servo", "APPLIES_TO"), ("MoveIt 2", "Servo", "HAS_PART")],
     "what command rate does MoveIt 2 Servo stream and what kills the servo on a collision margin breach",
     "moveit2 servo twist stamped 250hz joint collision check thread margin"),
    # --- 43 --- problem
    ("The URDF for the four-wheel platform was rejected by MoveIt's srdf generator because a continuous joint had no limit tags; adding soft_upper/soft_lower dummy bounds got the setup assistant unstuck.", "problem", "technical", False,
     [("URDF", "file"), ("MoveIt", "framework"), ("srdf generator", "tool"), ("soft_upper", "config")],
     [("URDF", "MoveIt", "APPLIES_TO"), ("soft_upper", "URDF", "CONFIGURES"), ("srdf generator", "MoveIt", "HAS_PART")],
     "which URDF tweak unstuck the MoveIt setup assistant on a continuous-joint platform",
     "urdf moveit srdf generator continuous joint soft upper lower limit"),
    # --- 44 --- reference
    ("LOAM's paper decomposes LiDAR odometry into a fast scan-to-scan thread and a slower scan-to-map refinement; the two-thread structure directly informed the A-LOAM and LeGO-LOAM follow-ups.", "reference", "technical", False,
     [("LOAM", "publication"), ("A-LOAM", "library"), ("LeGO-LOAM", "library"), ("scan-to-map", "method")],
     [("A-LOAM", "LOAM", "BUILDS_ON"), ("LeGO-LOAM", "LOAM", "BUILDS_ON"), ("LOAM", "scan-to-map", "USES")],
     "which two-thread decomposition from the LOAM paper do A-LOAM and LeGO-LOAM both extend",
     "loam paper scan map thread aloam lego refinement lidar odometry"),
    # --- 45 --- preference
    ("I keep URDF hand-written and use xacro macros only for repeated joint groups; the auto-generated URDF out of Fusion 360 ships inertial noise that breaks Gazebo contact resolution.", "preference", "technical", False,
     [("URDF", "file"), ("xacro", "tool"), ("Fusion 360", "tool"), ("Gazebo", "platform")],
     [("xacro", "URDF", "EXTENDS"), ("Fusion 360", "URDF", "PRODUCES"), ("Fusion 360", "Gazebo", "CONTRADICTS")],
     "why do you hand-write URDF and only reach for xacro macros instead of the Fusion 360 export",
     "urdf xacro fusion 360 auto generate inertial noise gazebo contact"),
    # --- 46 --- architecture
    ("The factory cell uses ROS 2 iron with CycloneDDS peer-to-peer on one VLAN and a separate MQTT bridge to the SCADA layer; the two networks never cross because the robot cell is safety-isolated.", "architecture", "technical", False,
     [("ROS 2", "framework"), ("iron", "platform"), ("CycloneDDS", "library"), ("MQTT", "protocol"), ("SCADA", "platform"), ("VLAN", "protocol")],
     [("ROS 2", "CycloneDDS", "USES"), ("MQTT", "SCADA", "COMMUNICATES_WITH"), ("VLAN", "ROS 2", "CONFIGURES")],
     "how are the ROS 2 cell network and the SCADA MQTT bridge kept isolated in the factory cell",
     "ros2 iron cyclonedds vlan mqtt scada factory cell isolation safety"),
    # --- 47 --- noise
    ("Someone replaced the espresso-machine water filter without telling anybody and the first three pulls were chalky enough to clog the group head.", "fact", "noise", True, [], [], None, None),
    # --- 48 --- milestone
    ("The indoor drone closed its first full GPS-denied autonomy loop on Tuesday; the VIO-only stack based on ORB-SLAM3 and a PX4 offboard mode held position within 30 cm over a ten-minute hold.", "milestone", "technical", False,
     [("ORB-SLAM3", "library"), ("PX4", "framework"), ("VIO", "method"), ("offboard mode", "concept")],
     [("PX4", "offboard mode", "HAS_PART"), ("ORB-SLAM3", "VIO", "IMPLEMENTS"), ("PX4", "ORB-SLAM3", "COMMUNICATES_WITH")],
     "which VIO stack held the drone in GPS-denied hover via PX4 offboard on the first successful loop",
     "orbslam3 px4 offboard vio gps denied indoor drone hover 30cm"),
    # --- 49 --- decision
    ("Adopted Nav2's collision_monitor as the safety overlay instead of a bespoke bump-stop node; the slowdown and emergency-stop polygons on a single lifecycle node simplified the safety review considerably.", "decision", "technical", False,
     [("Nav2", "framework"), ("collision_monitor", "library"), ("bump-stop", "pattern"), ("lifecycle node", "pattern")],
     [("collision_monitor", "bump-stop", "REPLACES"), ("collision_monitor", "Nav2", "HAS_PART"), ("collision_monitor", "lifecycle node", "IMPLEMENTS")],
     "which Nav2 component replaced the bespoke bump-stop and simplified the safety review",
     "nav2 collision monitor bump stop safety overlay lifecycle slowdown stop"),
    # --- 50 --- architecture
    ("Sensor fusion on the autonomous tractor feeds a dual-antenna GNSS, a tactical-grade IMU, and a front-facing Velodyne VLP-32C into a factor-graph backend running gtsam; the optimiser re-linearises at 10 Hz.", "architecture", "technical", False,
     [("GNSS", "infrastructure"), ("IMU", "infrastructure"), ("Velodyne VLP-32C", "infrastructure"), ("factor-graph", "concept"), ("gtsam", "library")],
     [("gtsam", "factor-graph", "IMPLEMENTS"), ("GNSS", "gtsam", "COMMUNICATES_WITH"), ("IMU", "gtsam", "COMMUNICATES_WITH"), ("Velodyne VLP-32C", "gtsam", "COMMUNICATES_WITH")],
     "which backend optimiser fuses the tractor's GNSS, IMU, and VLP-32C and at what relinearisation rate",
     "gnss imu velodyne vlp32c factor graph gtsam tractor sensor fusion"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
