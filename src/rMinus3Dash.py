#!/usr/bin/env python

import time
import itertools
import numpy as np
import json
import itertools
import rospy
from std_msgs.msg import String
import dynamixel
import os
import rospkg
#--------------------------------------------------------------OFFSETS------------------------------------------------------------------------------
# darwin = {1: 90, 2: -90, 3: 67.5, 4: -67.5, 7: 45, 8: -10, 9: 'i', 10: 'i', 13: 'i', 14: 'i', 17: 'i', 18: 'i'}

darwin = {1: 90, 2: -90, 3: 67.5, 4: -67.5, 7: 45, 8: -10, 9: 'i', 10: 'i', 13: 'i', 14: 'i', 17: 'i', 18: 'i'}
darwin1 = {13: -12, 14: 10}
#abmath = {11: 5, 12: -5, 13: -10, 14: 10, 15: -5, 16: 5}
abmath = {11: 7, 12: -5}
hand = {5: 60, 6: -60}
#---------------------------------------------------------------------------------------------------------------------------------------------------
rp = rospkg.RosPack()
package_path = rp.get_path("dash")
path = os.path.join(package_path, "include", "super.json")

class Dynamixel(object) :
	def __init__(self,lock,default_id=0) :
		global dxl
		ports = dynamixel.get_available_ports()
		if not ports :
			raise IOError("No ports found ")

		print "Connecting to ",ports[0]

		dxl = dynamixel.Dxl(ports[default_id])
		self.ids = dxl.scan(25)
		print self.ids
		# dxl.enable_torque(self.ids)
		if len(self.ids)<lock-1 :
			raise RuntimeError("all the motors were not detected")

		dxl.set_moving_speed(dict(zip(self.ids,itertools.repeat(1000))))


	def posWrite(self,pose) :
		pos = {ids:angle for ids,angle in pose.items()}
		dxl.set_goal_position(pos)


	def listWrite(self,list) :
		pos = dict(zip(self.ids,list))
		dxl.set_goal_position(pos)


	def angleWrite(self,ids,pose) :
		dxl.set_goal_position({ids:pose})
		
	def returnPos(self,ids) :

		return dxl.get_present_position((ids,))	
class JSON(object) :
	def __init__(self,file) :
		try :
			with open(file,"r") as f :
				self.data = json.load(f)
		except :
			raise RuntimeError("File not found")
		
	def parse(self,motion) :
		p_frame = str()
		p_pose = str()
		write = []
		js = self.data["Root"]["PageRoot"]["Page"]
		for j in js :
			try :
				 if motion == j["name"] :
					for step in j["steps"]["step"] :
						write.append(Motion(step["frame"],step["pose"],p_frame,p_pose))
						p_frame = step["frame"]
						p_pose = step["pose"]
			except :
				raise RuntimeError("Motion not found")
		return write
			
	def setparse(self,motion,offset=[]) :
		js = self.data["Root"]["FlowRoot"]["Flow"]
		motionset = []
		for j in js :
			try : 
				if motion == j["name"] :
					for unit in j["units"]["unit"] :
						motionset.append(Motionset(json.parse(motion=unit["main"]),speed=float(unit["mainSpeed"])/2.0,offset=offset))
			except :
				raise RuntimeError("Motionset not found")

                return motionset
	
	
class Motion(object) :
	def __init__(self,frame,pose,p_frame,p_pose) :
		self.frame = int(frame)
		self.begin = {}
		self.end = {}
	
		if not(p_pose) :
			self.frame_diff = 1
			p_pose = pose
		else :
			self.frame_diff = self.frame-int(p_frame) 

			
		for ids,pos in enumerate(map(float,p_pose.split())) :
			self.end[ids+1] = pos	

		for ids,pos in enumerate(map(float,pose.split())) :
			self.begin[ids+1] = pos


	def setoffset(self,offset={},darwin=True) :
		if not(darwin) :
			pass

		else :
			for key in offset.keys() :
				if offset[key] == 'i' :
					self.end[key] = -self.end[key]
					self.begin[key] = -self.begin[key]
				else :
					self.end[key] += offset[key]
					self.begin[key] += offset[key]		


	def motion(self,speed=1.0) :
	
		write = []
		ids = []
		for key in self.end.keys() :
			linp = np.linspace(self.end[key],self.begin[key],self.frame_diff)
			write.append(linp)
			ids.append(key)	

		for pose in zip(*write) :
			print pose
			dxl.set_goal_position(dict(zip(ids,pose)))
			time.sleep(0.008/speed)



class Motionset(object) :
	def __init__(self,motion,speed=1,offset=[]) :
		self.motion = motion
		self.offset = offset
		self.speed = speed
		self.init = False

	def run(self,speed=1) :
		speed = self.speed
		
		if self.init :
			self.exe(speed)

		else :
			self.init = True
			for motion in self.motion :
				for offset in self.offset :
					#for m in motion :
					motion.setoffset(offset)
				motion.motion(speed)
			
	def exe(self,speed) :
		for motion in self.motion :
			motion.motion(speed)	
								

class Custom(object) :
	def __init__(self,motionset) :
		self.motionset = motionset

	def run(self,spd=None) :
		#prev_motionset = str()
		speed = spd
		for motionset in self.motionset :
			if not(spd) :
				speed = motionset.speed
  
			motionset.run(speed)

		
#--------------------------------------------------------------MOTIONS--------------------------------------------------------------------------------
json = JSON(path)
balance = Motionset(json.parse(motion="152 Balance"),offset=[darwin,hand])
w1 = Motionset(json.parse(motion="32 F_S_L"),speed=2.1,offset=[darwin])
w2 = Motionset(json.parse(motion="33 "),speed=2.1,offset=[darwin])
w3 = Motionset(json.parse(motion="38 F_M_R"),speed=3.5,offset=[darwin])
w4 = Motionset(json.parse(motion="39 "),speed=3.1,offset=[darwin])
w5 = Motionset(json.parse(motion="36 F_M_L"),speed=3.5,offset=[darwin])
w6 = Motionset(json.parse(motion="37 "),speed=3.1,offset=[darwin])

walk = Custom(json.setparse("22 F_S_L",offset=[darwin]))

w1b = Motionset(json.parse(motion="32 F_S_L"),speed=2.1,offset=[darwin])
w2b = Motionset(json.parse(motion="33 "),speed=2.1,offset=[darwin])
w3b = Motionset(json.parse(motion="13 B_R_M"),speed=1.0,offset=[darwin])
w4b = Motionset(json.parse(motion="14 B_L_S"),speed=1.0,offset=[darwin])
w5b = Motionset(json.parse(motion="15 B_R_M"),speed=1.0,offset=[darwin])
w6b = Motionset(json.parse(motion="16 B_L_M"),speed=1.0,offset=[darwin])

back_left = Motionset(json.parse(motion="17 B_R_E"),speed=1,offset=[darwin])
back_right = Motionset(json.parse(motion="18 B_L_E"),speed=1,offset=[darwin])


bl1 = Motionset(json.parse("52 B_E_L"), offset=[darwin])
bl2 = Motionset(json.parse("53 "), offset=[darwin])

br1 = Motionset(json.parse("54 B_E_R"), offset=[darwin])
br2 = Motionset(json.parse("55 "), offset=[darwin])

back_walk = Custom(motionset=[w6b,w5b])
walk_init = Custom(motionset=[w1,w2])
walk_motion = Custom(motionset=[w3,w4,w5,w6])				
fast_left = Motionset(json.parse(motion="9 ff_r_l"),speed=0.5,offset=[darwin,abmath,darwin1])
fast_right = Motionset(json.parse(motion="10 ff_l_r"),speed=0.5,offset=[darwin,abmath,darwin1])
fast_walk = Custom(motionset=[fast_left,fast_right])
r_turn = Motionset(json.parse(motion="27 RT"),speed=1.2,offset=[darwin])
l_turn = Motionset(json.parse(motion="28 LT"),speed=1.2,offset=[darwin])

left_side_step = Custom(json.setparse("21 Fst_L",offset=[darwin, hand]))
right_side_step = Custom(json.setparse("20 Fst_R",offset=[darwin, hand]))

l_step = Custom(json.setparse("24 F_E_L",offset=[darwin, hand]))
r_step = Custom(json.setparse("25 F_E_R",offset=[darwin, hand]))

kick = Custom(json.setparse("26 F_PShoot_R",offset = [darwin, hand]))
rskick = Motionset(json.parse("39 Pass_R"),speed=1.5, offset=[darwin])
#-----------------------------------------------------------------------------------------------------------------------------------------------------

tilt = 20
tilt_inst = 2.0

def listener(data) :
	global tilt_ang
        rospy.loginfo(rospy.get_caller_id() + 'I heard %s', data.data)
        print data.data
	if data.data == "forward":
		walk_motion.run()
		
	elif data.data == "right" :
		r_turn.run()
	elif data.data == "left" :
		l_turn.run()


	elif data.data == "tilt_d" :
		ddxl.angleWrite(tilt,tilt_inst)

	if ddxl.returnPos(20)[20] < 1.0 :
		ddxl.angleWrite(20,40)
		time.sleep(0.001)
		back_walk.run()
		
		
if __name__ == "__main__":
	ddxl = Dynamixel(lock=20)
	ddxl.angleWrite(19,0)
	ddxl.angleWrite(20,40)
	balance.run()
	raw_input("Proceed da?")
        rospy.init_node('Dash', anonymous=True)
        rospy.Subscriber('get_area',String,listener,queue_size=1)
        rospy.spin()
	
