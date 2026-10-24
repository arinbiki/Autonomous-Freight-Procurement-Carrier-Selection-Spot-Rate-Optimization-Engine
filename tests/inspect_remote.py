import paramiko
import os
from dotenv import load_dotenv

load_dotenv()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(os.getenv('SSH_HOST'), username=os.getenv('SSH_USER'), password=os.getenv('SSH_PASS'))

cmd = "docker exec api-mn65ylv0vqu0q23xti3v4qur cat /app/api/controllers/console/apikey.py"
stdin, stdout, stderr = client.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
client.close()
