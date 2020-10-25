# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from gtp import gtp
from Tkinter import *
from time import sleep
from toolbox import *
from toolbox import _

class KataGoAnalysis():
	def run_analysis(self,current_move):
		one_move=go_to_move(self.move_zero,current_move)
		player_color=guess_color_to_play(self.move_zero,current_move)
		
		katago=self.katago
		log()
		log("==============")
		log("move",str(current_move))
		
		#additional_comments=""
		if player_color in ('w',"W"):
			log("katago play white")
			answer=katago.play_white()
		else:
			log("katago play black")
			answer=katago.play_black()
		
		if current_move>1:
			es=katago.get_katago_final_score()
			node_set(one_move,"ES",es)
			
		best_answer=answer
		node_set(one_move,"CBM",answer) #Computer Best Move

		position_evaluation=katago.get_all_katago_moves()
		
		if (answer in ["PASS","RESIGN"]):
			katago.undo()
		else:
			#let's make sure there is at least one variation available
			if len(position_evaluation['variations'])==0:
				position_evaluation['variations'].append({'sequence':answer})
			
			nb_undos=1 #let's remember to undo that move from katago

			#let's make sure that there is more than one move for the first line of play
			#only one move could be a bookmove, or a very very forcing move
			first_sequence=position_evaluation['variations'][0]['sequence']
			new_sequence=first_sequence
			while len(new_sequence.split())<=1 and nb_undos<=5:
				log("first, let's ask katago for the next move")
				if player_color in ('w',"W") and nb_undos%2==0:
					answer=katago.play_white()
				elif player_color in ('w',"W") and nb_undos%2==1:
					answer=katago.play_black()
				elif player_color not in ('w',"W") and nb_undos%2==0:
					answer=katago.play_black()
				else:
					answer=katago.play_white()
				nb_undos+=1 #one have to remember to undo that move later
				
				new_position_evaluation=katago.get_all_katago_moves() #let's get stats for this new move
				
				#let's make sure there is at least one variation available
				if len(new_position_evaluation['variations'])==0:
					new_position_evaluation['variations'].append({'sequence':answer})
				
				if (answer not in ["PASS","RESIGN"]):
					#let's check the lenght of the new sequence
					new_sequence=new_position_evaluation["variations"][0]["sequence"]
					#adding this new sequence to the old sequence
					position_evaluation['variations'][0]['sequence']+=" "+new_sequence

				else:
					#katago does not want to play further on this line of play
					#so let's stop there
					break

			for u in range(nb_undos):
				#log("undo...")
				katago.undo()
			
		best_move=True
		log("Number of alternative sequences:",len(position_evaluation['variations']))
		for variation in position_evaluation['variations'][:self.maxvariations]:
			#exemple: {'value network win rate': '50.22%', 'policy network value': '17.37%', 'sequence': 'Q16 D4 D17 Q4', 'playouts': '13', 'first move': 'Q16'}
			previous_move=one_move.parent
			current_color=player_color	
			first_variation_move=True
			for one_deep_move in variation['sequence'].split(' '):
				if one_deep_move in ["PASS","RESIGN"]:
					log("Leaving the variation when encountering",one_deep_move)
					break

				i,j=gtp2ij(one_deep_move)
				new_child=previous_move.new_child()
				node_set(new_child,current_color,(i,j))
				
				if first_variation_move==True:
					first_variation_move=False
					#variation_comment=""
		
					if 'value network win rate' in variation:
						if player_color=='b':
							black_value=variation['value network win rate']
							white_value=opposite_rate(black_value)
						else:
							white_value=variation['value network win rate']
							black_value=opposite_rate(white_value)	
						node_set(new_child,"VNWR",black_value+'/'+white_value)
						if best_move:
							node_set(one_move,"VNWR",black_value+'/'+white_value)

					if 'policy network value' in variation:
						node_set(new_child,"PNV",variation['policy network value'])

					if 'playouts' in variation:
						node_set(new_child,"PLYO",variation['playouts'])
					
					#new_child.add_comment_text(variation_comment)
					
					if best_move:
						best_move=False
					
				previous_move=new_child
				if current_color in ('w','W'):
					current_color='b'
				else:
					current_color='w'
		log("==== no more sequences =====")
		
		try:
			max_reading_depth=position_evaluation['max reading depth']
			node_set(one_move,"MRD",str(max_reading_depth))
			average_reading_depth=position_evaluation['average reading depth']
			node_set(one_move,"ARD",str(average_reading_depth))
		except:
			pass
		
		log("==== creating heat map =====")
		raw_heat_map=katago.get_heatmap()
		heat_map=""
		for i in range(self.size):
			for j in range(self.size):
				if raw_heat_map[i][j]>=0.01:#ignore values lower than 1% to avoid generating heavy RSGF file
					heat_map+=ij2sgf([i, j])+str(round(raw_heat_map[i][j],2))+","
		
		if heat_map:
			node_set(one_move,"HTM",heat_map[:-1]) #HTM: heat map
		
		
		#one_move.add_comment_text(additional_comments)
		return best_answer
	
	def initialize_bot(self):
		katago=katago_starting_procedure(self.g,self.profile)
		self.katago=katago
		self.time_per_move=0
		return katago

def katago_starting_procedure(sgf_g,profile,silentfail=False):


	katago=bot_starting_procedure("KataGo","KataGo",KataGo_gtp,sgf_g,profile,silentfail)
	if not katago:
		return False

	try:
		time_per_move=profile["timepermove"]
		if time_per_move:
			time_per_move=int(time_per_move)
			if time_per_move>0:
				log("Setting time per move")
				katago.set_time(main_time=0,byo_yomi_time=time_per_move,byo_yomi_stones=1)
				#self.time_per_move=time_per_move #why is that needed???
	except:
		log("Wrong value for KataGo thinking time:",time_per_move)
	
	return katago

class RunAnalysis(KataGoAnalysis,RunAnalysisBase):
	def __init__(self,parent,filename,move_range,intervals,variation,komi,profile,existing_variations="remove_everything"):
		RunAnalysisBase.__init__(self,parent,filename,move_range,intervals,variation,komi,profile,existing_variations)

class LiveAnalysis(KataGoAnalysis,LiveAnalysisBase):
	def __init__(self,g,filename,profile):
		LiveAnalysisBase.__init__(self,g,filename,profile)

class Position(dict):
	def __init__(self):
		self['variations']=[]

class Variation(dict):
	pass

class KataGo_gtp(gtp):

	def get_heatmap(self):
		while not self.stderr_queue.empty():
			self.stderr_queue.get()
		self.write("heatmap average")
		one_line=self.readline() #empty line
		buff=[]
		while len(buff)<self.size+2:
			buff.append(self.stderr_queue.get())
		buff.reverse()
		number_coordinate=1
		letters="ABCDEFGHJKLMNOPQRST"[:self.size]
		pn=[["NA" for i in range(self.size)] for j in range(self.size)] #pn: policy network
		pn_values=[]
		for i in range(self.size+2):
			one_line=buff[i].strip()
			if "winrate" in one_line:
				continue
			if "pass" in one_line:
				continue
			one_line=one_line.strip()
			one_line=[int(s) for s in one_line.split()]
			new_values=[[letter_coordinate+str(number_coordinate),int(value)/1000.] for letter_coordinate,value in zip(letters,one_line)]
			for nv in new_values:
				pn_values.append(nv)
			number_coordinate+=1

		for coordinates,value in pn_values:
			i,j=gtp2ij(coordinates)
			pn[i][j]=value
		return pn

	def quick_evaluation(self,color):
		if color==2:
			self.play_white()
		else:
			self.play_black()
		position_evaluation=self.get_all_katago_moves()
		self.undo()
		
		if color==1:
			black_win_rate=position_evaluation["variations"][0]["value network win rate"]
			white_win_rate=opposite_rate(black_win_rate)
		else:
			white_win_rate=position_evaluation["variations"][0]["value network win rate"]
			black_win_rate=opposite_rate(white_win_rate)
		txt=variation_data_formating["VNWR"]%(black_win_rate+'/'+white_win_rate)
		txt+="\n\n"+variation_data_formating["ES"]%self.get_katago_final_score()
		return txt
		
	def __init__(self,command):
		self.c=1
		self.command_line=command[0]+" "+" ".join(command[1:])
		
		katago_working_directory=command[0][:-len(ntpath.basename(command[0]))]
		command=[c.encode(sys.getfilesystemencoding()) for c in command]
		katago_working_directory=katago_working_directory.encode(sys.getfilesystemencoding())
		if katago_working_directory:
			log("KataGo working directory:",katago_working_directory)
			self.process=subprocess.Popen(command,cwd=katago_working_directory, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		else:
			self.process=subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		self.size=0
		
		self.stderr_starting_queue=Queue.Queue(maxsize=100)
		self.stderr_queue=Queue.Queue()
		self.stdout_queue=Queue.Queue()
		
		threading.Thread(target=self.consume_stderr).start()
		
		log("Checking KataGo stderr to check for OpenCL SGEMM tuner running")
		delay=60
		while 1:
			try:
				err_line=self.stderr_starting_queue.get(True,delay)
				
				delay=10
				if "Started OpenCL SGEMM tuner." in err_line:
					log("OpenCL SGEMM tuner is running")
					show_info(_("KataGo is currently running the OpenCL SGEMM tuner. It may take several minutes until KataGo is ready."))
					break
				elif "Loaded existing SGEMM tuning.\n" in err_line:
					log("OpenCL SGEMM tuner has already been runned")
					break
				elif "Could not open weights file" in err_line:
					show_info(err_line.strip())
					break
				elif "A network weights file is required to use the program." in err_line:
					show_info(err_line.strip())
					break
				elif "Weights file is the wrong version." in err_line:
					show_info(err_line.strip())
					break
				elif "BLAS Core:" in err_line:
					log("Could not find out, abandoning")
					break
			except:
				log("Could not find out, abandoning")
				break
		
		self.free_handicap_stones=[]
		self.history=[]

	def consume_stderr(self):
		while 1:
			try:
				err_line=self.process.stderr.readline()
				if err_line:
					self.stderr_queue.put(err_line)
					try:
						self.stderr_starting_queue.put(err_line,block=False)
					except:
						#no need to keep all those log in memory, so there is a limit at 100 lines
						pass
				else:
					log("leaving consume_stderr thread")
					return
			except Exception, e:
				log("leaving consume_stderr thread due to exception:")
				log(e)
				return


	def get_katago_final_score(self):
		self.write("final_score")
		answer=self.readline().strip()
		try:
			return answer.split(" ")[1]
		except:
			raise GRPException("GRPException in Get_katago_final_score()")

	def get_all_katago_moves(self):
		buff=[]
		
		sleep(.1)
		while not self.stderr_queue.empty():
			while not self.stderr_queue.empty():
				buff.append(self.stderr_queue.get())
			sleep(.1)
		
		buff.reverse()
		
		position_evaluation=Position()
		
		for err_line in buff:
			#log(err_line)
			try: #for comptability with KataGo dynamic komi
				if "average depth," in err_line and "max depth" in err_line:
					position_evaluation["average reading depth"]=float(err_line.split()[0])
					position_evaluation["max reading depth"]=int(err_line.split()[3])
				if " ->" in err_line:
					if err_line[0]==" ":
						#log(err_line)
						variation=Variation()
						
						one_answer=err_line.strip().split(" ")[0]
						variation["first move"]=one_answer
						
						nodes=err_line.strip().split("(")[0].split("->")[1].replace(" ","")
						variation["playouts"]=nodes
						
						value_network=err_line.split("(V:")[1].split('%')[0].strip()+"%"
						variation["value network win rate"]=value_network #for KataGo, the value network is used as win rate
						
						policy_network=err_line.split("(N:")[1].split('%)')[0].strip()+"%"
						variation["policy network value"]=policy_network
						
						sequence=err_line.split("PV: ")[1].strip()
						variation["sequence"]=sequence.upper()
						
						#answers=[[one_answer,sequence,value_network,policy_network,nodes]]+answers
						position_evaluation['variations']=[variation]+position_evaluation['variations']
			except:
				pass

		return position_evaluation


class KataGoSettings(BotProfiles):
	def __init__(self,parent,bot="KataGo"):
		Frame.__init__(self,parent)
		self.parent=parent
		self.bot=bot
		self.profiles=get_bot_profiles(bot,False)
		profiles_frame=self
		
		self.listbox = Listbox(profiles_frame)
		self.listbox.grid(column=10,row=10,rowspan=10)
		self.update_listbox()
		
		row=10
		Label(profiles_frame,text=_("Profile")).grid(row=row,column=11,sticky=W)
		self.profile = StringVar()
		Entry(profiles_frame, textvariable=self.profile, width=30).grid(row=row,column=12)

		row+=1
		Label(profiles_frame,text=_("Command")).grid(row=row,column=11,sticky=W)
		self.command = StringVar() 
		Entry(profiles_frame, textvariable=self.command, width=30).grid(row=row,column=12)
		
		row+=1
		Label(profiles_frame,text=_("Parameters")).grid(row=row,column=11,sticky=W)
		self.parameters = StringVar()
		Entry(profiles_frame, textvariable=self.parameters, width=30).grid(row=row,column=12)
		'''
		row+=1
		Label(profiles_frame,text=_("Time per move (s)")).grid(row=row,column=11,sticky=W)
		self.timepermove = StringVar()
		Entry(profiles_frame, textvariable=self.timepermove, width=30).grid(row=row,column=12)
		'''

		row+=10
		buttons_frame=Frame(profiles_frame)
		buttons_frame.grid(row=row,column=10,sticky=W,columnspan=3)
		Button(buttons_frame, text=_("Add profile"),command=self.add_profile).grid(row=row,column=1,sticky=W)
		Button(buttons_frame, text=_("Modify profile"),command=self.modify_profile).grid(row=row,column=2,sticky=W)
		Button(buttons_frame, text=_("Delete profile"),command=self.delete_profile).grid(row=row,column=3,sticky=W)
		Button(buttons_frame, text=_("Test"),command=lambda: self.parent.parent.test(self.bot_gtp,self.command,self.parameters)).grid(row=row,column=4,sticky=W)
		
		self.listbox.bind("<Button-1>", lambda e: self.after(100,self.change_selection))

		self.index=-1

		self.bot_gtp=KataGo_gtp

	def clear_selection(self):
		self.index=-1
		self.profile.set("")
		self.command.set("")
		self.parameters.set("")
		self.timepermove.set("")
		
	def change_selection(self):
		try:
			index=int(self.listbox.curselection()[0])
			self.index=index
		except:
			log("No selection")
			self.clear_selection()
			return
		data=self.profiles[index]
		self.profile.set(data["profile"])
		self.command.set(data["command"])
		self.parameters.set(data["parameters"])
		self.timepermove.set(data["timepermove"])

		
	def add_profile(self):
		profiles=self.profiles
		if self.profile.get()=="":
			return
		data={"bot":self.bot}
		data["profile"]=self.profile.get()
		data["command"]=self.command.get()
		data["parameters"]=self.parameters.get()
		data["timepermove"]=self.timepermove.get()
		
		self.empty_profiles()
		profiles.append(data)
		self.create_profiles()
		self.clear_selection()
		
	def modify_profile(self):
		profiles=self.profiles
		if self.profile.get()=="":
			return
		
		if self.index<0:
			log("No selection")
			return
		index=self.index
		
		profiles[index]["profile"]=self.profile.get()
		profiles[index]["command"]=self.command.get()
		profiles[index]["parameters"]=self.parameters.get()
		profiles[index]["timepermove"]=self.timepermove.get()
		
		self.empty_profiles()
		self.create_profiles()
		self.clear_selection()



class KataGoOpenMove(BotOpenMove):
	def __init__(self,sgf_g,profile):
		BotOpenMove.__init__(self,sgf_g,profile)
		self.name='KataGo'
		self.my_starting_procedure=katago_starting_procedure

KataGo={}
KataGo['name']="KataGo"
KataGo['gtp_name']="KataGo"
KataGo['analysis']=KataGoAnalysis
KataGo['openmove']=KataGoOpenMove
KataGo['settings']=KataGoSettings
KataGo['gtp']=KataGo_gtp
KataGo['liveanalysis']=LiveAnalysis
KataGo['runanalysis']=RunAnalysis
KataGo['starting']=katago_starting_procedure

if __name__ == "__main__":
	main(KataGo)
