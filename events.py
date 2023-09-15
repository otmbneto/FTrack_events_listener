import os
import urllib
import ftrack_api as fa
from dotenv import load_dotenv

#Load the environment variables
load_dotenv()

def downloadVersion(versionId,shot_name):

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
			urllib.request.urlretrieve(url,downloadPath)


def getEntityById(entity_type,entity_id):

	return session.query("{0} where id is {1}".format(entity_type,entity_id)).first()


def my_callback(event):
	
	'''Event callback printing all new or updated entities.'''
	for entity in event['data'].get('entities', []):

		if "entity_type" in entity.keys() and entity["entity_type"] == "Task":

			if entity["action"] == "update":

				shots = [s for s in entity["parents"] if s["entity_type"] == "Shot"]
				shot = shots[-1] if len(shots) > 0 else None
				if shot is not None:
					shot = getEntityById("Shot",shot["entityId"])
				task = getEntityById("Task",entity["entityId"])
				
				if "statusid" in entity["changes"]:
					status = getEntityById("Status",entity["changes"]["statusid"]['new'])
					print("New status Change detected: " + str(entity["changes"]["statusid"]))
					if task["name"] in ["03_3D_Blocking","04_3D_Polish"] and status["name"] in ["Hum Review","Alan Review","Pending Review","Hum Approved"]:
						versions = session.query('AssetVersion where task_id is "{0}"'.format(task["id"])).all()
						print("found {0} assetVersions for this task!".format(len(versions)))
						if len(versions) > 0:
							version = versions[-1]
							downloadVersion(version["id"],shot["name"])

if __name__ == '__main__':
	
	# Subscribe to events with the update topic.
	print("Starting Ftrack events listener...")
	session = fa.Session(auto_connect_event_hub=True)
	session.event_hub.subscribe('topic=ftrack.update', my_callback)
	# Wait for events to be received and handled.
	session.event_hub.wait()

