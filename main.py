from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import os
from typing import Union
import paramiko

import docker

app = FastAPI()
security = HTTPBasic()

def sshConnect(host, command, username = "ubuntu", password = "ubuntu"):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, 22, username, password)
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        stdin.write(f"{password}\n")
        stdin.flush()

        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print("Output:")
            print(output)
        if error:
            print("Error:")
            print(error)

    finally:
        ssh.close()
    lines = output.split('\r\n')
    cleaned_output = '\n'.join(lines[2:]).strip()
    # cleaned_output = output.replace("[sudo] password for user: ", "").strip()
    return cleaned_output

client = docker.DockerClient(base_url='unix:///var/run/docker.sock')

# def localHostCommand(command):
    # username = "ubuntu"
    # password = "ubuntu"
    # result = subprocess.run(
    #     [command],
    #     input=f"{password}\n",
    #     capture_output=True,
    #     text=True
    # )
    # print(result.stdout)
    # lines = result.stdout.split('\r\n')
    # cleaned_output = '\n'.join(lines[2:]).strip()
    # return cleaned_output





class Docker(BaseModel):
    host: str = 'localhost'
    image: str
    port : Union[int, None] = None
    containerPort: Union[int, None] = None
    memoryLimit: Union[int, None] = None
    cpuLimit: Union[float, None] = None
    def findParams(self) -> str:
        params = []
        if self.port is not None and self.containerPort is not None:
            params.append(f"-p {self.port}:{self.containerPort}")
        if self.memoryLimit is not None:
            params.append(f"--memory={self.memoryLimit}m")
        if self.cpuLimit is not None:
            params.append(f"--cpus={self.cpuLimit}")
        params.append(self.image)
        return " ".join(params)
    def findForDocker(self):
        params = {
            "image": self.image,
            "detach": True
        }
        if self.port and self.containerPort:
            params["ports"] = {f"{self.containerPort}/tcp": self.port}
        if self.memoryLimit:
            params["mem_limit"] = f"{self.memoryLimit}m"
        if self.cpuLimit:
            params["cpus"] = self.cpuLimit
        return params

def find_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if (credentials.username is None or credentials.password is None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not found username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": credentials.username, "password": credentials.password}


@app.get("/")
async def root(a: int = 1):
    return {"message": "Hello World", "a": a}

@app.get("/ping/{hostname}")
async def ping(hostname: str, count: int = 4):
    response = os.system(f"ping -n {count} {hostname}")
    if response == 0:
        return {"hostname": hostname, "is": "up"}
    else:
        return {"hostname": hostname, "is": "down"}

@app.post("/docker")
async def run(docker: Docker, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker run -d {docker.findParams()}'
    if docker.host != 'localhost':
        sshConnect(docker.host, commandLine, auth_data["username"], auth_data["password"])
        connectContainer = f'{docker.host}:{docker.port}'
        return {"commandLine": commandLine, "connectContainer": connectContainer }
    else:
        params = docker.findForDocker()
        container = client.containers.run(**params)
        return {"status": "success", "container_id": container.id}



@app.get("/docker/{host}/containers")
async def run(host: str = 'localhost', auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker ps'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        lines = output.split('\n')
        cleaned_output = '\n'.join(lines[1:]).strip()
        return {"commandLine": commandLine, "result": cleaned_output }
    else:
        output = client.containers.list(all=True)
        result = []
        for container in output:
            container_info = {
                "image": container.image.tags[0] if container.image.tags else "none",
                "name": container.name,
                "containerId": container.short_id,
                "status": container.status
            }
            result.append(container_info)
        return {"result": result }


@app.get("/docker/{host}/images")
async def run(host: str, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker images'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        lines = output.split('\n')
        cleaned_output = '\n'.join(lines[1:]).strip()
        return {"commandLine": commandLine, "result": cleaned_output }
    else:
        output = client.images.list()
        return {"result": str(output) }


@app.post("/docker/{host}/containers/{id}/stop")
async def run(host: str, id: str, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker stop {id}'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        return {"commandLine": commandLine, "result": output }
    else:
        container = client.containers.get(container_id=id)
        container.stop()
        return {"container": id, "isStoped": True}


@app.post("/docker/{host}/containers/{id}/start")
async def run(host: str, id: str, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker start {id}'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        return {"commandLine": commandLine, "result": output }
    else:
        container = client.containers.get(container_id=id)
        container.start()
        return {"container": id, "isStarted": True}


@app.delete("/docker/{host}/containers/{id}")
async def run(host: str, id: str, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker rm {id}'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        return {"commandLine": commandLine, "result": f'{output} removed' }
    else:
        container = client.containers.get(container_id=id)
        container.remove()
        return {"container": id, "isRemoved": True}


@app.delete("/docker/{host}/images/{name}")
async def run(host: str, name: str, auth_data: dict = Depends(find_credentials)):
    commandLine = f'sudo docker rmi {name}'
    if host != 'localhost':
        output = sshConnect(host, commandLine, auth_data["username"], auth_data["password"])
        return {"commandLine": commandLine, "result": output }
    else:
        image = client.images.get(name=name)
        image.remove()
        return {"image": name, "isRemoved": True}
