import os
import json
import uuid
import tempfile
import zipfile
import time
import subprocess
from pathlib import Path
from shutil import rmtree, copytree

from loguru import logger
from dotenv import load_dotenv
from flask import Flask, request, send_from_directory

from kubernetes import client, config
from kubernetes.client.rest import ApiException

###########################################

load_dotenv()

CHASSIS_DEV = False
WINDOWS = True if os.name == 'nt' else False

HOME_DIR = str(Path.home())
MODZY_UPLOADER_REPOSITORY = 'ghcr.io/modzy/chassis-modzy-uploader'

if CHASSIS_DEV:
    MOUNT_PATH_DIR = "/"+ str(os.path.join(HOME_DIR,".chassis_data"))[3:].replace("\\", "/") if WINDOWS else os.path.join(HOME_DIR,".chassis_data")
else:
    MOUNT_PATH_DIR =  os.getenv('MOUNT_PATH_DIR')

WORKSPACE_DIR = os.getenv('WORKSPACE_DIR')
DATA_DIR = f'{MOUNT_PATH_DIR}/{WORKSPACE_DIR}'

ENVIRONMENT = os.getenv('K_ENVIRONMENT')

K_DATA_VOLUME_NAME = os.getenv('K_DATA_VOLUME_NAME')
K_EMPTY_DIR_NAME = os.getenv('K_EMPTY_DIR_NAME')
K_INIT_EMPTY_DIR_PATH = os.getenv('K_INIT_EMPTY_DIR_PATH')
K_KANIKO_EMPTY_DIR_PATH = os.getenv('K_KANIKO_EMPTY_DIR_PATH')
K_SERVICE_ACCOUNT_NAME = "local-job-builder" if CHASSIS_DEV else os.getenv('K_SERVICE_ACCOUNT_NAME')
K_JOB_NAME = os.getenv('K_JOB_NAME')

###########################################
def create_dev_environment():
    '''
    Creates chassis environment for development purposes

    Args:
        None (None)
    
    Returns:
        None
    '''
    # get the kubeconfig file for local cluster
    kubefile = os.getenv("CHASSIS_KUBECONFIG")
    config.load_kube_config(kubefile)

    # check to see if the development cluster has the development volume and claim installed
    base_api = client.CoreV1Api()
    try:
        # check to see if the volume exists
        # volume and claim based off of https://github.com/docker/for-win/issues/5325#issuecomment-632309842 Gsyltc comment
        api_response = base_api.list_persistent_volume(pretty='pretty', watch=False)
        print(api_response)
        filtered_pv = [pv for pv in api_response.items if pv.metadata.name == "local-volume-chassis"]
        if len(filtered_pv) == 0:
            # if the volume doesn't exist, create it. note these paths are specific for Docker Desktop On Windows
            # TODO: document a Linux or Mac version

            if WINDOWS:
                local_path = f'/run/desktop/mnt/host/c{MOUNT_PATH_DIR}'
            else:
                local_path = MOUNT_PATH_DIR

            local_node_selector_terms = client.V1NodeSelectorTerm(
                match_expressions=[client.V1NodeSelectorRequirement(
                    key="kubernetes.io/hostname",
                    operator="In",
                    values=["docker-desktop"])]
            )

            local_volume_spec = client.V1PersistentVolumeSpec(capacity={"storage": "10Gi"},
                                                              volume_mode="Filesystem",
                                                              access_modes=["ReadWriteOnce"],
                                                              persistent_volume_reclaim_policy="Delete",
                                                              storage_class_name="local-storage",
                                                              local=client.V1LocalVolumeSource(path=local_path),
                                                              node_affinity=client.V1VolumeNodeAffinity(
                                                                  required=client.V1NodeSelector(
                                                                      node_selector_terms=[local_node_selector_terms])
                                                              )
                                                              )
            local_volume_meta = client.V1ObjectMeta(name="local-volume-chassis")

            local_pvolume = client.V1PersistentVolume(api_version="v1",
                                                      kind="PersistentVolume",
                                                      metadata=local_volume_meta,
                                                      spec=local_volume_spec)

            api_response = base_api.create_persistent_volume(body=local_pvolume)
            print(api_response)

    except Exception as err:
        print(err)

    try:
        # check to see if the volume claim exists
        api_response = base_api.list_persistent_volume_claim_for_all_namespaces(pretty='pretty', watch=False)
        print(api_response)
        filtered_pvc = [pvc for pvc in api_response.items if pvc.metadata.name == "dir-claim-chassis"]
        if len(filtered_pvc) == 0:
            # if the volume doesn't exist, create it.

            local_volume_claim_spec = client.V1PersistentVolumeClaimSpec(storage_class_name="local-storage",
                                                                         access_modes=["ReadWriteOnce"],
                                                                         resources=client.V1ResourceRequirements(
                                                                             requests={"storage": "1Gi"}
                                                                         )
                                                                         )

            local_pvolume_claim = client.V1PersistentVolumeClaim(api_version="v1",
                                                                 kind="PersistentVolumeClaim",
                                                                 metadata=client.V1ObjectMeta(name="dir-claim-chassis"),
                                                                 spec=local_volume_claim_spec)

            api_response = base_api.create_namespaced_persistent_volume_claim(body=local_pvolume_claim,
                                                                              namespace="default")
            print(api_response)
    except Exception as err:
        print(err)

    # The dev volume and claim are now accessible in the local Kubernetes cluster.

    # Check to see if the service account exists. If not create it.
    try:
        api_response = base_api.list_namespaced_service_account(ENVIRONMENT)
        filtered_sa = [sa for sa in api_response.items if sa.metadata.name == "local-job-builder"]
        if len(filtered_sa) == 0:
            api_response = base_api.create_namespaced_service_account(ENVIRONMENT,
                                                                      client.V1ServiceAccount(
                                                                          api_version="v1",
                                                                          metadata=client.V1ObjectMeta(
                                                                              name="local-job-builder")
                                                                      )
                                                                      )
            print(api_response)
    except Exception as err:
        print(err)

    # check to see of role exists and if not create it
    role_api = client.RbacAuthorizationV1Api()
    try:
        api_response = role_api.list_namespaced_role(ENVIRONMENT)
        filtered_role = [role for role in api_response.items if role.metadata.name == "local-job-builder-role"]
        if len(filtered_role) == 0:
            local_role_meta = client.V1ObjectMeta(name="local-job-builder-role")
            local_role_rules = [client.V1PolicyRule(api_groups=[""],
                                                    resources=["pods"],
                                                    verbs=["get", "create", "list"]),
                                client.V1PolicyRule(api_groups=["batch", "extensions"],
                                                    resources=["jobs", "pods"],
                                                    verbs=["get", "create", "patch"])
                                ]
            role_api.create_namespaced_role(ENVIRONMENT,
                                            client.V1Role(api_version="rbac.authorization.k8s.io/v1",
                                                          kind="Role",
                                                          metadata=local_role_meta,
                                                          rules=local_role_rules))
    except Exception as err:
        # something happened with role creation
        print(err)

    # check to see if the service account is bound to the role. If not, bind them
    try:
        api_response = role_api.list_namespaced_role_binding(ENVIRONMENT)
        filtered_role_binding = [role_binding for role_binding in api_response.items if
                                 role_binding.metadata.name == "local-job-builder-role-binding"]
        if len(filtered_role_binding) == 0:
            local_role_binding_meta = client.V1ObjectMeta(name="local-job-builder-role-binding", namespace=ENVIRONMENT)
            local_role_binding_subjects = [client.V1Subject(kind="ServiceAccount",
                                                            name="local-job-builder")
                                           ]
            local_role_binding_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io",
                                                      kind="Role",
                                                      name="local-job-builder-role")
            role_api.create_namespaced_role_binding(ENVIRONMENT,
                                                    client.V1RoleBinding(api_version="rbac.authorization.k8s.io/v1",
                                                                         kind="RoleBinding",
                                                                         metadata=local_role_binding_meta,
                                                                         subjects=local_role_binding_subjects,
                                                                         role_ref=local_role_binding_ref))
    except Exception as err:
        # something happened with role binding creation
        print(err)

    # testing has only been done against Windows 10 running the kubernetes cluster in docker desktop
    return


def create_job_object(
        image_name,
        module_name,
        model_name,
        path_to_tar_file,
        random_name,
        modzy_data,
        publish,
        registry_auth,
        gpu=False,
        arm64=False,
        modzy_model_id=None
):
    '''
    This utility method sets up all the required objects needed to create a model image and is run within the `run_kaniko` method.

    Args:
        image_name (str): container image name
        module_name (str): reference module to locate location within service input is saved
        model_name (str): name of model to package
        path_to_tar_file (str): filepath destination to save docker image tar file
        random_name (str): random id generated during build process that is used to ensure that all jobs are uniquely named and traceable
        modzy_data (str): modzy_metadata_path returned from `extract_modzy_metadata` method
        publish (bool): determines if image will be published to Docker registry
        registry_auth (dict): Docker registry authorization credentials  
        gpu (bool): If `True`, will build container image that runs on GPU 
        arm64 (bool): If `True`, will build container image that runs on ARM64 architecture
        modzy_model_id (str): existing modzy model id if user requested new version

    Returns:
        Job: Chassis job object
          
    '''
    # 

    job_name = f'{K_JOB_NAME}-{random_name}'

    # credential setup for Docker Hub.
    # json for holding registry credentials that will access docker hub.
    # reference: https://github.com/GoogleContainerTools/kaniko#pushing-to-docker-hub
    registry_credentials = f'{{"auths":{{"https://index.docker.io/v1/":{{"auth":"{registry_auth}"}}}}}}'

    # mount path leads to /data
    # this is a mount point. NOT the volume itself.
    # name aligns with a volume defined below.
    data_volume_mount = client.V1VolumeMount(
        mount_path=MOUNT_PATH_DIR,
        name="local-volume-code"
    ) if CHASSIS_DEV else client.V1VolumeMount(
        mount_path=MOUNT_PATH_DIR,
        name=K_DATA_VOLUME_NAME
    )

    # This volume will be used by init container to populate registry credentials.
    # mount leads to /tmp/credentials
    # this is a mount point. NOT the volume itself.
    # name aligns with a volume defined below.
    init_empty_dir_volume_mount = client.V1VolumeMount(
        mount_path=K_INIT_EMPTY_DIR_PATH,
        name=K_EMPTY_DIR_NAME
    )

    # This volume will be used by kaniko container to get registry credentials.
    # mount path leads to /kaniko/.docker per kaniko reference documentation
    # this is a mount point. NOT the volume itself.
    # name aligns with a volume defined below.
    kaniko_empty_dir_volume_mount = client.V1VolumeMount(
        mount_path=K_KANIKO_EMPTY_DIR_PATH,
        name=K_EMPTY_DIR_NAME
    )

    # This container is used to populate registry credentials.
    # it only runs the single command in shell to echo our credentials into their proper file
    # per the reference documentation for Docker Hub
    # TODO: add credentials for Cloud Providers
    init_container = client.V1Container(
        name='credentials',
        image='busybox',
        volume_mounts=[init_empty_dir_volume_mount],
        command=[
            '/bin/sh',
            '-c',
            f'echo \'{registry_credentials}\' > {K_INIT_EMPTY_DIR_PATH}/config.json'
        ]
    )

    # This is the kaniko container used to build the final image.

    if gpu and not arm64:
        dockerfile = "Dockerfile.gpu"
    elif arm64 and not gpu:
        dockerfile = "Dockerfile.arm"
    elif arm64 and gpu:
        dockerfile = "Dockerfile.arm.gpu"
    else:
        dockerfile = "Dockerfile"

    kaniko_args = [
        f'--dockerfile={DATA_DIR}/flavours/{module_name}/{dockerfile}',
        '' if publish else '--no-push',
        f'--tarPath={path_to_tar_file}',
        f'--destination={image_name}{"" if ":" in image_name else ":latest"}',
        f'--context={DATA_DIR}',
        f'--build-arg=MODEL_DIR=model-{random_name}',
        f'--build-arg=MODZY_METADATA_PATH={modzy_data.get("modzy_metadata_path")}',
        f'--build-arg=MODEL_NAME={model_name}',
        f'--build-arg=MODEL_CLASS={module_name}',
        # Modzy is the default interface.
        '--build-arg=INTERFACE=modzy'   
    ]
        
    init_container_kaniko = client.V1Container(
        name='kaniko',
        image='gcr.io/kaniko-project/executor:latest',
        volume_mounts=[
            data_volume_mount,
            kaniko_empty_dir_volume_mount
        ],
        args=kaniko_args
    )

    modzy_uploader_args = [
            f'--api_key={modzy_data.get("api_key")}',
            f'--deploy={True if modzy_data.get("deploy") else ""}',
            f'--sample_input_path={modzy_data.get("modzy_sample_input_path")}',
            f'--metadata_path={DATA_DIR}/{modzy_data.get("modzy_metadata_path")}',
            f'--image_tag={image_name}{"" if ":" in image_name else ":latest"}',
        ]

    if modzy_model_id:
        modzy_uploader_args.append(f'--model_id={modzy_model_id}')

    modzy_uploader_container = client.V1Container(
        name='modzy-uploader',
        image=MODZY_UPLOADER_REPOSITORY,
        volume_mounts=[data_volume_mount],
        env=[
            client.V1EnvVar(name='JOB_NAME', value=job_name),
            client.V1EnvVar(name='ENVIRONMENT', value=ENVIRONMENT)
        ],
        args=modzy_uploader_args
    )

    # volume claim
    data_pv_claim = client.V1PersistentVolumeClaimVolumeSource(
        claim_name="dir-claim-chassis"
    ) if CHASSIS_DEV else client.V1PersistentVolumeClaimVolumeSource(
        claim_name=K_DATA_VOLUME_NAME
    )

    # volume holding data

    data_volume = client.V1Volume(
        name="local-volume-code",
        persistent_volume_claim=data_pv_claim
    ) if CHASSIS_DEV else client.V1Volume(
        name=K_DATA_VOLUME_NAME,
        persistent_volume_claim=data_pv_claim
    )

    # volume holding credentials
    empty_dir_volume = client.V1Volume(
        name=K_EMPTY_DIR_NAME,
        empty_dir=client.V1EmptyDirVolumeSource()
    )

    # Pod spec for the image build process
    pod_spec = client.V1PodSpec(
        service_account_name=K_SERVICE_ACCOUNT_NAME,
        restart_policy='Never',
        init_containers=[init_container, init_container_kaniko],
        containers=[modzy_uploader_container],
        volumes=[
            data_volume,
            empty_dir_volume
        ]
    )

    # setup and initiate model image build
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(name=job_name),
        spec=pod_spec
    )

    spec = client.V1JobSpec(
        backoff_limit=0,
        template=template
    )
    job = client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=client.V1ObjectMeta(
            name=job_name,
        ),
        spec=spec
    )

    return job

def create_job(api_instance, job):
    '''
    This method kicks off the kaniko build job within `run_kaniko` method to create the new model image.

    Args:
        api_instance (kubernetes.client): Kubernetes client where kaniko build will execute
        job (job): valid job object generated by `create_job_object` method 

    Returns:
        None
    '''
    api_response = api_instance.create_namespaced_job(
        body=job,
        namespace=ENVIRONMENT)
    logger.info(f'Pod created. Status={str(api_response.status)}')

def run_kaniko(
        image_name,
        module_name,
        model_name,
        path_to_tar_file,
        random_name,
        modzy_data,
        publish,
        registry_auth,
        gpu=False,
        arm64=False,
        modzy_model_id=None
):
    '''
    This utility method creates and launches a job object that uses Kaniko to create the desired image during the `/build` process.
    
    It passes its arguments through to the `create_job_object` method and uses the output job to create chassis job. See `chassis_job_object` method for parameter details. 
    '''
    if CHASSIS_DEV:
        # if you are doing local dev you need to point at the local kubernetes cluster with your config file
        kubefile = os.getenv("CHASSIS_KUBECONFIG")
        config.load_kube_config(kubefile)
    else:
        # if the service is running inside a cluster during production then the config can be inherited
        config.load_incluster_config()

    batch_v1 = client.BatchV1Api()

    try:
        job = create_job_object(
            image_name,
            module_name,
            model_name,
            path_to_tar_file,
            random_name,
            modzy_data,
            publish,
            registry_auth,
            gpu,
            arm64,
            modzy_model_id
        )
        create_job(batch_v1, job)
    except Exception as err:
        return str(err)

    return False

def unzip_model(model, module_name, random_name):
    '''
    This utility function unzips a tar archive of a container image. It is used in two places:

    * During `/build` process
    * During `/test` process

    Args:
        model (str): data returned from `request.files` component of REST call
        module_name (str): reference module to locate location within service input is saved
        random_name (str): random id generated during build process that is used to ensure that all jobs are uniquely named and traceable

    Returns:
        filepath: location of unzipped model container
    '''
    tmp_dir = tempfile.mkdtemp()
    path_to_zip_file = f'{tmp_dir}/{model.filename}'

    zip_content_dst = f'{DATA_DIR}/flavours/{module_name}/model-{random_name}'

    # if running on windows, zip dst has to be modified for local kubernetes processing
    # if WINDOWS:
    # zip_content_dst =

    model.save(path_to_zip_file)

    with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
        zip_ref.extractall(zip_content_dst)

    rmtree(tmp_dir)

    return zip_content_dst

def extract_modzy_metadata(modzy_metadata_data, module_name, random_name):
    '''
    This utility method returns model metadata is used in two separate places during the `/build` process
    
    Args:
        modzy_metadata_data (str): data returned from `request.files` component of REST call
        module_name (str): reference module to locate location within service input is saved
        random_name (str): random id generated during build process that is used to ensure that all jobs are uniquely named and traceable

    Returns:
        str: filepath to model metadata       
    '''
    if modzy_metadata_data:
        metadata_path = f'flavours/{module_name}/model-{random_name}.yaml'
        modzy_metadata_data.save(f'{DATA_DIR}/{metadata_path}')
    else:
        # Use the default one if user has not sent its own metadata file.
        # This way, mlflow/Dockerfile will not throw an error because it
        # will copy a file that does exist.
        metadata_path = f'flavours/{module_name}/interfaces/modzy/asset_bundle/0.1.0/model.yaml'

    return metadata_path

def extract_modzy_sample_input(modzy_sample_input_data, module_name, random_name):
    '''
    This utility method returns a sample input data path and is used in two separate places: 
    
    * During the `/build` process if Modzy-specific information is included. Only executes if model is to be deployed to Modzy
    * During the `/test` process, where chassis will create a new conda environment and run a sample inference through the `ChassisModel` object with the data returned from this method.
    
    Args:
        modzy_sample_input_data (str): data returned from `request.files` component of REST call
        module_name (str): reference module to locate location within service input is saved
        random_name (str): random id generated during build process that is used to ensure that all jobs are uniquely named and traceable

    Returns:
        str: filepath to sample input data        
    '''
    if not modzy_sample_input_data:
        return

    sample_input_path = f'{DATA_DIR}/flavours/{module_name}/{random_name}-{modzy_sample_input_data.filename}'
    modzy_sample_input_data.save(sample_input_path)

    return sample_input_path

def get_job_status(job_id):
    '''
    This method is run by the `/job/{job_id}` endpoint.
    Based on a GET request, it retrieves the status of the Kaniko job and the results if the job has completed.

    Args:
        job_id (str): valid Chassis job identifier, generated by `create_job` method

    Returns:
        Dict: Dictionary containing corresponding job data of job `job_id` 
    '''
    if CHASSIS_DEV:
        # if you are doing local dev you need to point at the local kubernetes cluster with your config file
        kubefile = os.getenv("CHASSIS_KUBECONFIG")
        config.load_kube_config(kubefile)
    else:
        # if the service is running inside a cluster during production then the config can be inherited
        config.load_incluster_config()

    batch_v1 = client.BatchV1Api()

    try:
        job = batch_v1.read_namespaced_job(job_id, ENVIRONMENT)

        annotations = job.metadata.annotations or {}
        result = annotations.get('result')
        result = json.loads(result) if result else None
        status = job.status

        job_data = {
            'result': result,
            'status': status.to_dict()
        }

        return job_data
    except ApiException as e:
        logger.error(f'Exception when getting job status: {e}')
        return e.body

def download_tar(job_id):
    '''
    This method is run by the `/job/{job_id}/download-tar` endpoint. 
    It downloads the container image from kaniko, built during the chassis job with the name `job_id`

    Args:
        job_id (str): valid Chassis job identifier, generated by `create_job` method 
    
    Returns:
        Dict: response from `download_tar` endpoint
    '''
    uid = job_id.split(f'{K_JOB_NAME}-')[1]

    return send_from_directory(DATA_DIR, path=f'kaniko_image-{uid}.tar', as_attachment=False)

def build_image():
    '''
    This method is run by the `/build` endpoint. 
    It generates a model image based upon a POST request. The `request.files` structure can be seen in the Python SDK docs.

    Args:
        None (None): This method does not take any parameters

    Returns:
        Dict: information about whether or not the image build resulted in an error
    '''
    
    if not ('image_data' in request.files and 'model' in request.files):
        return 'Both model and image_data are required', 500

    # retrieve image_data and populate variables accordingly
    image_data = json.load(request.files.get('image_data'))
    model_name = image_data.get('model_name')
    image_name = image_data.get('name')
    gpu = image_data.get('gpu')
    arm64 = image_data.get('arm64')
    publish = image_data.get('publish', False)
    publish = True if publish else ''
    registry_auth = image_data.get('registry_auth')

    # retrieve binary representations for all three variables
    model = request.files.get('model')
    modzy_metadata_data = request.files.get('modzy_metadata_data')
    modzy_sample_input_data = request.files.get('modzy_sample_input_data')

    # json string loaded into variable
    modzy_data = json.load(request.files.get('modzy_data') or  {})
    modzy_model_id = modzy_data.get('modzy_model_id')

    # This is a future proofing variable in case we encounter a model that cannot be converted into mlflow.
    # It will remain hardcoded for now.
    module_name = 'mlflow'

    # This name is a random id used to ensure that all jobs are uniquely named and traceable.
    random_name = str(uuid.uuid4())

    # Unzip model archive
    unzip_model(model, module_name, random_name)

    # User can build the image but not deploy it to Modzy. So no input_sample is mandatory.
    # On the other hand, the model.yaml is needed to build the image so proceed with it.

    # save the sample input to the modzy_sample_input_path directory
    if modzy_data:
        modzy_sample_input_path = extract_modzy_sample_input(modzy_sample_input_data, module_name, random_name)
        modzy_data['modzy_sample_input_path'] = modzy_sample_input_path

    # TODO: this probably should only be done if modzy_data is true.
    modzy_metadata_path = extract_modzy_metadata(modzy_metadata_data, module_name, random_name)
    modzy_data['modzy_metadata_path'] = modzy_metadata_path

    # this path is the local location that kaniko will store the image it creates
    path_to_tar_file = f'{DATA_DIR}/kaniko_image-{random_name}.tar'

    logger.debug(f'Request data: {image_name}, {module_name}, {model_name}, {path_to_tar_file}')

    error = run_kaniko(
        image_name,
        module_name,
        model_name,
        path_to_tar_file,
        random_name,
        modzy_data,
        publish,
        registry_auth,
        gpu,
        arm64,
        modzy_model_id
    )

    if error:
        return {'error': error, 'job_id': None}

    return {'error': False, 'job_id': f'{K_JOB_NAME}-{random_name}'}

def copy_required_files_for_kaniko():
    '''
    Copies required files over to a shared volume with Kaniko so it can access them.

    Args:
        None (None)
    
    Returns:
        None
    '''
    # if using a special debug docker file this is where it goes
    try:
        for dir_to_copy in 'flavours'.split():
            dst = f'{DATA_DIR}/{dir_to_copy}'

            if os.path.exists(dst):
                rmtree(dst)

            copytree(f'./{dir_to_copy}', dst)
    except OSError as e:
        print(f'Directory not copied. Error: {e}')

def test_model():
    '''
    This method is run by the `/test` endpoint. It creates a new conda environment from the provided `conda.yaml` file and then tests the provided model in that conda environment with provided test input file.

    Args:
        None (None): This method does not take any parameters
    
    Returns:
        Dict: model response to `/test` endpoint. Should contain either successful predictions or error message
    '''
    if not ('sample_input' in request.files and 'model' in request.files):
        return 'Both sample input and model are required', 500

    output_dict = {}

    # retrieve binary representations for both variables
    model = request.files.get('model')
    sample_input = request.files.get('sample_input')

    # This is a future proofing variable in case we encounter a model that cannot be converted into mlflow.
    # It will remain hardcoded for now.
    module_name = 'mlflow'

    # This name is a random id used to ensure that all jobs are uniquely named and traceable.
    random_name = str(uuid.uuid4())

    # Unzip model archive
    unzipped_path = unzip_model(model, module_name, random_name)

    # get sample input path
    sample_input_path = extract_modzy_sample_input(sample_input, module_name, random_name)

    # create conda env, return error if fails
    try:
        tmp_env_name = str(time.time())
        rm_env_cmd = "conda env remove --name {}".format(tmp_env_name)
        yaml_path = os.path.join(unzipped_path,"conda.yaml")
        create_env_cmd = "conda env create -f {} -n {}".format(yaml_path,tmp_env_name)
        subprocess.run(create_env_cmd, capture_output=True, shell=True, executable='/bin/bash', check=True)
    except subprocess.CalledProcessError as e:
        print(e)
        subprocess.run(rm_env_cmd, capture_output=True, shell=True, executable='/bin/bash')
        output_dict["env_error"] = e.stderr.decode()
        return output_dict

    # test model in env with sample input file, return error if fails
    try:
        test_model_cmd = """
        source activate {};
        python test_chassis_model.py {} {}
        """.format(tmp_env_name,unzipped_path,sample_input_path)
        test_ret = subprocess.run(test_model_cmd, capture_output=True, shell=True, executable='/bin/bash', check=True)
        output_dict["model_output"] = test_ret.stdout.decode()
    except subprocess.CalledProcessError as e:
        subprocess.run(rm_env_cmd, capture_output=True, shell=True, executable='/bin/bash')
        error_output = e.stderr.decode()
        output_dict["model_error"] = error_output[error_output.find('in process'):]
        return output_dict

    # if we make it here, test was successful, remove env and return output
    subprocess.run(rm_env_cmd, capture_output=True, shell=True, executable='/bin/bash')
    return output_dict

def create_app():
    flask_app = Flask(__name__)

    @flask_app.route('/health')
    def hello2():
        return 'Chassis Server Up and Running!'

    @flask_app.route('/')
    def hello():
        return 'Alive!'

    @flask_app.route('/build', methods=['POST'])
    def build_image_api():
        return build_image()

    @flask_app.route('/job/<job_id>', methods=['GET'])
    def get_job_status_api(job_id):
        return get_job_status(job_id)

    @flask_app.route('/job/<job_id>/download-tar')
    def download_job_tar_api(job_id):
        return download_tar(job_id)

    @flask_app.route('/test', methods=['POST'])
    def test_model_api():
        return test_model()

    return flask_app


###########################################

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    copy_required_files_for_kaniko()

    if CHASSIS_DEV:
        create_dev_environment()

    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=port)
