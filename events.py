import os
import urllib
import threading
import json
import ftrack_api as fa
from dotenv import load_dotenv

#Load the environment variables
load_dotenv()

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
			url = component.get("component_locations")[0].get("url")["value"]
			print("downloading to`{0}".format(downloadPath))
			if replace or not os.path.exists(downloadPath):
				urllib.request.urlretrieve(url,downloadPath)
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
						sendToGoogleSheet(json.dumps(data))
					elif task["name"] in ["03_Render","07_Render","10_Comp","07_Comp","10.01_Comp"]:

						data = {"shot": shot["name"],"task":task["name"].split("_")[-1].lower(),"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID2"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"render"}
						sendToGoogleSheet(json.dumps(data))

					#data = {"shot": shot["name"],"task":task["name"].split("_")[-1].lower(),"status":status["name"],"spreadsheet_id":os.getenv("SPREADSHEET_ID3"),"sheet_name":"Shots","assignees":assignees,"date": status_changes[-1]["date"].format("YYYY-MM-DD"),"spreadsheet_type":"geral","description":task["description"],"task_type":task["type"]["name"]}
					#sendToGoogleSheet(json.dumps(data))



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
	
	# Subscribe to events with the update topic.
	print("Starting Ftrack events listener...")
	session = fa.Session(auto_connect_event_hub=True)
	t = threading.Thread(target=getCompletedScenes,args=(session,))
	t.start()

	session.event_hub.subscribe('topic=ftrack.update', my_callback)
	# Wait for events to be received and handled.
	session.event_hub.wait()

