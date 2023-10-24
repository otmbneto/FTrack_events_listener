import os
import urllib
import threading
import json
import time
import datetime
import traceback
import tempfile
import copy
import ftrack_api as fa
from dotenv import load_dotenv
#Load the environment variables
load_dotenv()

from utils.sendToGoogleSheet.app import ShotsSheet
googleSheet = ShotsSheet()

sheet_geral_data = googleSheet.getSheetData(os.getenv("SPREADSHEET_ID3"))

def downloadVersion(versionId,shot_name,replace = True):

	print("downloading version with id {0}".format(versionId))
	downloadRootPath = os.getenv("PLAYBLAST_PATH")
	fileTypes = [".mov",".mp4",".avi"]
	version = getEntityById("AssetVersion",versionId) 
	# Get details for these versions to build a list of media to download
	for component in version.get("components"):
		# If this component is of the right fileType, then download it
		if component.get("file_type") in fileTypes:
			fileType = component.get("file_type")
			# Check if we have a version name that seems to match the component name
			fileName = shot_name + fileType
			# Calculate the full download path and URL to pull from
			downloadPath = os.path.join(downloadRootPath, fileName)
			
			component_locations = component.get("component_locations")

			if len(component_locations) > 0:
				try:
					url = component_locations[0].get("url")["value"]
				except:
					continue
				print("downloading to`{0}".format(downloadPath))
				if replace or not os.path.exists(downloadPath):
					tries = 3
					while(tries > 0):
						try:
							urllib.request.urlretrieve(url,downloadPath)
							break
						except Exception as e:
							tries -= 1
							print(e)
							continue

				break


def getEntityById(entity_type,entity_id):

	return session.query("{0} where id is {1}".format(entity_type,entity_id)).first()


def sendToGoogle(shot,step,status):

	app_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"utils/sendStatusToGoogleSheets/app.py")
	if os.path.exists(app_path):
		cmd = "py \"{0}\" \"{1}\" \"{2}\" \"{3}\"".format(app_path,shot,step,status)
		os.system(cmd)

	return 

def sendToGoogleSheet(data):

	fData = data.replace("\"","\\\"") 
	app_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"utils/sendToGoogleSheet/app.py")
	if os.path.exists(app_path):
		cmd = "py \"{0}\" \"{1}\"".format(app_path,fData)
		print(cmd)
		os.system(cmd)	

	return

def getCompletedScenes(session):

	tasks = session.query('Task where name is "04_3D_Polish" and status.name is "Completed" and project.name is "aba_e_sua_banda"').all() + session.query('Task where name is "03_3D_Blocking" and status.name is "Completed" and project.name is "aba_e_sua_banda"').all()
	print(len(tasks))

	for task in tasks:

		print(task["name"])
		shot = task["parent"]
		versions = session.query('AssetVersion where task_id is "{0}"'.format(task["id"])).all()
		print("found {0} assetVersions for this task!".format(len(versions)))
		if len(versions) > 0:
			version = versions[-1]
			downloadVersion(version["id"],shot["name"],replace = False)

	return

def getCompRenderInfo(session):

	tasks = session.query('Task where name in ("03_Render","07_Render","10_Comp","07_Comp","10.01_Comp") and status.name is "Completed" and project.name is "aba_e_sua_banda"').all()

	for task in tasks:

		status = task["status"]
		shot = task["parent"]
		assignees = ",".join(getAssignee(task))
		status_changes = sorted(task["status_changes"], key=lambda d: d['date'])
		data = {"shot": shot["name"],"task":task["name"].split("_")[-1].lower(),"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID2"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"render"}
		googleSheet.setShotStatus(data)


def getGeneralTaskInfo(session):

	ignore_list = readTxtFile("ftrack-general-tasks.txt")
	tasks = session.query('Task where project.name is "aba_e_sua_banda"').all()
	for task in tasks:
		try:
			if task["parent"]["name"].startswith("ABA_SH") and not task["parent"]["name"] + "_" + task["name"] in ignore_list:
				
				status = task["status"]
				shot = task["parent"]
				print(shot["name"] + "_" + task["name"])
				assignees = ",".join(getAssignee(task))
				status_changes = sorted(task["status_changes"], key=lambda d: d['date'])
				data = {"shot": shot["name"],"task":task["name"],"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID3"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"geral","description":task["description"],"task_type":task["type"]["name"]}
				
				fstart = shot["custom_attributes"]["fstart"] if shot["custom_attributes"]["fstart"] is not None else 0
				fend = shot["custom_attributes"]["fend"] if shot["custom_attributes"]["fend"] is not None else 1

				data["fps"] = fend - fstart + 1
				data["start"] = task["start_date"].format("YYYY-MM-DD") if task["start_date"] is not None else ""
				data["end"] = task["end_date"].format("YYYY-MM-DD") if task["end_date"] is not None else ""
				googleSheet.setShotStatus(data)
				saveTxtFile("ftrack-general-tasks.txt",shot["name"] + "_" + task["name"])
		except Exception as e:
			print(traceback.format_exc())
			continue

	print("End of generalTaskThread")


def get_diff(old,new):

	diff = []
	print("Differences!!!")
	for l in range(len(old)):

		old[l] += [''] * (10 - len(old[l]))
		if len(new) <= l:
			print("new matrix is smaller")
			break
		new[l] += [''] * (len(old[l]) - len(new[l]))
		if old[l] == new[l]:
			continue
		print("------------------------------")
		print(old[l])
		print(new[l])
		print("\n")
		diff.append(new[l])

	return diff


def update_ftrack(data,session):


	for line in data:

		somethingChanged = False
		print(line)
		task = session.query('Task where name is "{0}" and parent.name is "{1}" and project.name is "aba_e_sua_banda"'.format(line[4],line[1])).all()
		if len(task) == 0:
			print("ERROR: Task not found!")
			continue

		task = task[0]
		shot = getEntityById("Shot",task["parent"]["id"])
		fend = shot["custom_attributes"]["fend"]
		if fend == '' or fend is None or int(fend) != int(line[2]):
			fend = int(fend) if fend is not None else str(fend)
			print("Changing Shot frame count! from {0} to {1}".format(fend,line[2]))
			shot["custom_attributes"]["fend"] = int(line[2])
			somethingChanged = True

		status = session.query('Status where name is "{0}"'.format(line[5]))
		if len(status) == 0:
			print("ERROR: Status not found!")
		elif status[0]["id"] != task["status_id"]:
			print("Changing task status! from {0} to {1}".format(task["status_id"],status[0]["id"]))
			task["status_id"] = status[0]["id"]
			somethingChanged = True

		if task["description"] != line[7]:
			print("Changing task description")
			task["description"] = line[7]
			somethingChanged = True

		if ",".join(getAssignee(task)) != line[3]:
			print("Changing task assignees")
			for user in getUsers(line[3].split(",")):
				if not user["first_name"] + " " + user["last_name"] in ",".join(getAssignee(task)):
					assignUser(task,user,commit=False)
					somethingChanged = True

		start_date = task["start_date"].format("YYYY-MM-DD") if task["start_date"] is not None else ""
		if start_date != line[8]:
			print("Changing start date")
			# Convert the date string to a datetime object
			start_date = datetime.datetime.strptime(line[8], "%Y-%m-%d") if line[8] != "" else None
			task['start_date'] = start_date
			somethingChanged = True

		due_date = task["end_date"].format("YYYY-MM-DD") if task["end_date"] is not None else ""
		if due_date != line[9]:
			print("Changing due date")
			# Convert the date string to a datetime object
			due_date = datetime.datetime.strptime(line[9], "%Y-%m-%d") if line[9] != "" else None
			task['end_date'] = due_date
			somethingChanged = True

		if somethingChanged:
			session.commit()


	return somethingChanged

def checkGoogleForChanges(session):

	old_sheet = googleSheet.getSheetData(os.getenv("SPREADSHEET_ID3"),sheet_name = "Shots",pull = True)
	while not exit_flag.is_set():
		time.sleep(300)
		try:
			new_sheet = googleSheet.getSheetData(os.getenv("SPREADSHEET_ID3"),sheet_name = "Shots",pull = True)
			diff = get_diff(old_sheet,new_sheet)
			print("Checking for updates! found {0}.".format(len(diff)))
			if len(diff) > 0:
				result = update_ftrack(diff,session)
				#if result:
				old_sheet = copy.deepcopy(new_sheet)
		except Exception as e:
			print(traceback.format_exc())
			continue

	print("finishing checkGoogleForChanges thread!")
	raise KeyboardInterrupt

	return


def warnProduction(message,users):

	for user in users:

		# Create a new message and send it
		new_message = session.create('Note', {'content': message,'user': user})
	
	session.commit()


def my_callback(event):
	
	'''Event callback printing all new or updated entities.'''
	for entity in event['data'].get('entities', []):

		if "entity_type" in entity.keys() and entity["entity_type"] == "Task":

			if entity["action"] == "update":

				isShot = False
				shots = [s for s in entity["parents"] if s["entity_type"] == "Shot"]
				shot = shots[-1] if len(shots) > 0 else None
				if shot is not None:
					shot = getEntityById("Shot",shot["entityId"])
					isShot = True
				task = getEntityById("Task",entity["entityId"])

				if entity["changes"] is not None and "statusid" in entity["changes"]:
					status = getEntityById("Status",entity["changes"]["statusid"]['new'])
					assignees = ",".join(getAssignee(task))
					status_changes = sorted(task["status_changes"], key=lambda d: d['date'])
					print("New status Change detected: " + str(entity["changes"]["statusid"]))
					if task["name"] in ["03_3D_Blocking","04_3D_Polish"]:

						if status["name"] in ["Hum Review","Alan Review","Pending Review","Hum Approved"]:
							versions = session.query('AssetVersion where task_id is "{0}"'.format(task["id"])).all()
							print("found {0} assetVersions for this task!".format(len(versions)))
							if len(versions) > 0:
								version = versions[-1]
								downloadVersion(version["id"],shot["name"])

						data = {"shot": shot["name"],"task":task["name"].split("_")[-1].lower(),"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID"),"sheet_name":"Shots","spreadsheet_type": "animation"}
						result = googleSheet.setShotStatus(data)
					elif task["name"] in ["03_Render","07_Render","10_Comp","07_Comp","10.01_Comp"]:

						data = {"shot": shot["name"],"task":task["name"].split("_")[-1].lower(),"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID2"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"render"}
						result = googleSheet.setShotStatus(data)

					data = {"shot": shot["name"],"task":task["name"],"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID3"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"geral","description":task["description"],"task_type":task["type"]["name"]}
					
					fstart = shot["custom_attributes"]["fstart"] if shot["custom_attributes"]["fstart"] is not None else 0
					fend = shot["custom_attributes"]["fend"] if shot["custom_attributes"]["fend"] is not None else 1
					data["fps"] = fend - fstart + 1
					
					data["start"] = task["start_date"].format("YYYY-MM-DD") if task["start_date"] is not None else ""
					data["end"] = task["end_date"].format("YYYY-MM-DD") if task["end_date"] is not None else ""
					
					result = googleSheet.setShotStatus(data)
					if result == -1:
						users = getUsers(["Dir Studio Z"])
						message = "Ola! parece que um erro ocorreu com o script do Ftrack events durante o acesso as planilhas do Google. É provavel que seja hora de atualizar o token."
						warnProduction(message,users)

def assignUser(task,user,commit = True):

	# Create a new Appointment of type assignment.
	session.create('Appointment', {
	    'context': task,
	    'resource': user,
	    'type': 'assignment'
	})

	if commit:
		session.commit()


def readTxtFile(txtName):

	content = ""
	temp_file = os.path.join(tempfile.gettempdir(),"ftrack_temp_files",txtName)
	if os.path.exists(temp_file):
		with open(temp_file,"r") as f:
			content = f.read()
	return content

def saveTxtFile(txtName,data):

	temp = os.path.join(tempfile.gettempdir(),"ftrack_temp_files")

	if not os.path.exists(temp):
		os.makedirs(temp)

	temp_file = os.path.join(temp,txtName)
	edit_mode = "w"
	if os.path.exists(temp_file):
		edit_mode = "a"

	with open(temp_file,edit_mode) as f:
		f.write(data + "\n")

	return


def getUsers(userlist):

	if len(userlist) == 0:
		return []

	# Initialize a list to store the matching users
	matching_users = []

	# Loop through the list of user full names and query users based on each name
	for full_name in userlist:

		first_name = full_name.split(" ")[0]
		last_name = " ".join(full_name.split(" ")[1:])

		user = session.query('User where first_name is "{}" and last_name is "{}"'.format(first_name, last_name)).all()
		if len(user) > 0:
			print(user)
			matching_users.append(user[0])

	return matching_users

def getAssignee(task):

	users = session.query(
		'select first_name, last_name from User '
		'where assignments any (context_id = "{0}")'.format(task['id'])
	)

	assignees = []
	for user in users:
		assignees.append(str(user['first_name']) + " " + str(user['last_name']))
	return assignees


if __name__ == '__main__':

	try:	
		
		# Subscribe to events with the update topic.
		print("Starting Ftrack events listener...")
		session = fa.Session(auto_connect_event_hub=True)

		#t = threading.Thread(target=getCompletedScenes,args=(session,))
		#t.start()

		#t2 = threading.Thread(target=getCompRenderInfo,args=(session,))
		#t2.start() 


		#t3 = threading.Thread(target=getGeneralTaskInfo,args=(session,))
		#t3.start()

		# Create a flag to signal the child thread to exit
		exit_flag = threading.Event()
		t4 = threading.Thread(target=checkGoogleForChanges,args=(session,))
		t4.start()

		session.event_hub.subscribe('topic=ftrack.update', my_callback)
		# Wait for events to be received and handled.
		session.event_hub.wait()

	except KeyboardInterrupt:
	    
	    # Catch Ctrl+C to gracefully exit
	    print("Stopping child thread...")
	    session.close()
	    exit_flag.set()  # Set the flag to signal the child thread to exit
	    t4.join()  # Wait for the child thread to exit

	print("Main thread exiting.")


